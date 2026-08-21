"""Investment portfolio logic.

A holding's units and cost basis are always derived by replaying its
transactions in date order using the weighted-average-cost method (the same
approach a brokerage contract note uses): every buy raises the average price,
every sell realises profit/loss against that average and reduces the basis
proportionally. Nothing here trusts a stored "invested amount" column, because
there isn't one.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import String, delete, func, select, update
from sqlalchemy.orm import Session, selectinload

from app.core.errors import BadRequest
from app.models.enums import AuditAction, InvestmentTxnType
from app.models.investment import (
    InvestmentAccount,
    InvestmentGoal,
    InvestmentHolding,
    InvestmentTransaction,
)
from app.services import audit
from app.services.finance_math import CashFlow, project_goal, xirr
from app.services.ownership import assert_owned, get_owned, owned_query

ZERO = Decimal("0.00")
ZERO_UNITS = Decimal("0")


def _money(value: Decimal | float | int | None) -> Decimal:
    if value is None:
        return ZERO
    return Decimal(str(value)).quantize(Decimal("0.01"))


@dataclass
class Position:
    units: Decimal = ZERO_UNITS
    cost_basis: Decimal = ZERO
    realised_pnl: Decimal = ZERO
    total_dividends: Decimal = ZERO
    total_fees: Decimal = ZERO
    cash_flows: list[CashFlow] = field(default_factory=list)

    @property
    def avg_price(self) -> Decimal:
        if self.units <= ZERO_UNITS:
            return ZERO
        return (self.cost_basis / self.units).quantize(Decimal("0.01"))


def compute_position(transactions: list[InvestmentTransaction]) -> Position:
    """Replay a holding's transactions into a current position.

    Weighted-average cost: a sell realises profit against the average cost of
    every unit bought so far, then shrinks the basis by the cost of the units
    sold - never by the sale proceeds, which would silently invent P/L.
    """
    position = Position()
    for txn in sorted(transactions, key=lambda t: (t.txn_date, t.created_at)):
        if txn.txn_type == InvestmentTxnType.BUY.value:
            position.units += txn.units
            position.cost_basis += txn.amount + txn.fees
            position.cash_flows.append(CashFlow(txn.txn_date, -float(txn.amount + txn.fees)))

        elif txn.txn_type == InvestmentTxnType.BONUS.value:
            # Free units: no cash flow, no cost added, but they dilute the
            # average price of the position exactly like a stock split would.
            position.units += txn.units

        elif txn.txn_type == InvestmentTxnType.SELL.value:
            sell_units = min(txn.units, position.units) if position.units > ZERO_UNITS else ZERO_UNITS
            sold_cost = (position.avg_price * sell_units) if sell_units > ZERO_UNITS else ZERO
            proceeds = txn.amount - txn.fees
            position.realised_pnl += proceeds - sold_cost
            position.units -= txn.units
            position.cost_basis -= sold_cost
            if position.units <= ZERO_UNITS:
                position.units = ZERO_UNITS
                position.cost_basis = ZERO
            position.cash_flows.append(CashFlow(txn.txn_date, float(proceeds)))

        elif txn.txn_type in (InvestmentTxnType.DIVIDEND.value, InvestmentTxnType.INTEREST.value):
            position.total_dividends += txn.amount
            position.cash_flows.append(CashFlow(txn.txn_date, float(txn.amount)))

        elif txn.txn_type == InvestmentTxnType.FEE.value:
            position.total_fees += txn.amount
            position.cash_flows.append(CashFlow(txn.txn_date, -float(txn.amount)))

    position.cost_basis = _money(position.cost_basis)
    position.realised_pnl = _money(position.realised_pnl)
    position.total_dividends = _money(position.total_dividends)
    position.total_fees = _money(position.total_fees)
    return position


def current_value_of(holding: InvestmentHolding, position: Position) -> Decimal:
    """Market value of the live position.

    Falls back to cost basis (zero unrealised P/L) when no live price has ever
    been entered, rather than reporting a misleading zero valuation.
    """
    if holding.manual_value is not None:
        return _money(holding.manual_value)
    if holding.current_price is not None:
        return _money(position.units * holding.current_price)
    return position.cost_basis


def serialise_holding(holding: InvestmentHolding, transactions: list[InvestmentTransaction] | None = None) -> dict:
    txns = transactions if transactions is not None else list(holding.transactions)
    position = compute_position(txns)
    value = current_value_of(holding, position)
    unrealised = value - position.cost_basis
    return_percent = (
        float(unrealised / position.cost_basis * 100) if position.cost_basis > ZERO else 0.0
    )

    flows = list(position.cash_flows)
    if value > ZERO or position.units > ZERO_UNITS:
        flows.append(CashFlow(date.today(), float(value)))
    holding_xirr = xirr(flows)

    return {
        "id": holding.id,
        "name": holding.name,
        "symbol": holding.symbol,
        "asset_type": holding.asset_type,
        "account_id": holding.account_id,
        "account_name": holding.account.name if holding.account else None,
        "currency": holding.currency,
        "current_price": holding.current_price,
        "price_updated_at": holding.price_updated_at,
        "manual_value": holding.manual_value,
        "maturity_date": holding.maturity_date,
        "interest_rate": holding.interest_rate,
        "notes": holding.notes,
        "is_active": holding.is_active,
        "created_at": holding.created_at,
        "units_held": position.units,
        "avg_price": position.avg_price,
        "invested_amount": position.cost_basis,
        "current_value": value,
        "unrealised_pnl": unrealised,
        "realised_pnl": position.realised_pnl,
        "total_dividends": position.total_dividends,
        "return_percent": round(return_percent, 2),
        "xirr_percent": round(holding_xirr * 100, 2) if holding_xirr is not None else None,
    }


def serialise_txn(txn: InvestmentTransaction) -> dict:
    return {
        "id": txn.id,
        "holding_id": txn.holding_id,
        "txn_type": txn.txn_type,
        "txn_date": txn.txn_date,
        "units": txn.units,
        "price_per_unit": txn.price_per_unit,
        "amount": txn.amount,
        "fees": txn.fees,
        "notes": txn.notes,
        "created_at": txn.created_at,
    }


# --- Accounts ------------------------------------------------------------


def list_accounts(db: Session, user_id: uuid.UUID) -> list[dict]:
    accounts = list(
        db.execute(owned_query(InvestmentAccount, user_id).order_by(InvestmentAccount.name)).scalars()
    )
    holdings = list(
        db.execute(
            owned_query(InvestmentHolding, user_id).options(selectinload(InvestmentHolding.transactions))
        ).scalars()
    )
    by_account: dict[uuid.UUID | None, list[InvestmentHolding]] = {}
    for holding in holdings:
        by_account.setdefault(holding.account_id, []).append(holding)

    results = []
    for account in accounts:
        owned = by_account.get(account.id, [])
        value = sum(
            (current_value_of(h, compute_position(list(h.transactions))) for h in owned), ZERO
        )
        results.append(
            {
                "id": account.id,
                "name": account.name,
                "broker": account.broker,
                "account_number": account.account_number,
                "notes": account.notes,
                "is_active": account.is_active,
                "holding_count": len(owned),
                "current_value": value,
            }
        )
    return results


def create_account(db: Session, user_id: uuid.UUID, data: dict) -> InvestmentAccount:
    account = InvestmentAccount(
        user_id=user_id,
        name=data["name"].strip(),
        broker=data.get("broker"),
        account_number=data.get("account_number"),
        notes=data.get("notes"),
    )
    db.add(account)
    db.flush()
    return account


def update_account(db: Session, user_id: uuid.UUID, account_id: uuid.UUID, data: dict) -> InvestmentAccount:
    account = get_owned(db, InvestmentAccount, account_id, user_id)
    for field_name in ("name", "broker", "account_number", "notes", "is_active"):
        if field_name in data and data[field_name] is not None:
            setattr(account, field_name, data[field_name])
    return account


def delete_account(db: Session, user_id: uuid.UUID, account_id: uuid.UUID) -> None:
    account = get_owned(db, InvestmentAccount, account_id, user_id)
    # Detach rather than cascade: a holding's history must survive its broker
    # account being removed.
    db.execute(
        update(InvestmentHolding)
        .where(InvestmentHolding.user_id == user_id, InvestmentHolding.account_id == account_id)
        .values(account_id=None)
    )
    db.execute(delete(InvestmentAccount).where(InvestmentAccount.id == account.id))


# --- Holdings --------------------------------------------------------------


def list_holdings(
    db: Session,
    user_id: uuid.UUID,
    *,
    asset_type: str | None = None,
    account_id: uuid.UUID | None = None,
    include_inactive: bool = False,
) -> list[dict]:
    stmt = owned_query(InvestmentHolding, user_id).options(
        selectinload(InvestmentHolding.transactions), selectinload(InvestmentHolding.account)
    )
    if asset_type:
        stmt = stmt.where(InvestmentHolding.asset_type == asset_type)
    if account_id:
        stmt = stmt.where(InvestmentHolding.account_id == account_id)
    if not include_inactive:
        stmt = stmt.where(InvestmentHolding.is_active.is_(True))

    rows = [serialise_holding(h) for h in db.execute(stmt).scalars()]
    rows.sort(key=lambda r: r["current_value"], reverse=True)
    return rows


def create_holding(db: Session, user_id: uuid.UUID, data: dict) -> InvestmentHolding:
    assert_owned(db, InvestmentAccount, data.get("account_id"), user_id)

    holding = InvestmentHolding(
        user_id=user_id,
        account_id=data.get("account_id"),
        name=data["name"].strip(),
        symbol=data.get("symbol"),
        asset_type=data.get("asset_type") or "stock",
        currency=data.get("currency") or "INR",
        current_price=data.get("current_price"),
        price_updated_at=datetime.now(timezone.utc) if data.get("current_price") else None,
        manual_value=data.get("manual_value"),
        maturity_date=data.get("maturity_date"),
        interest_rate=data.get("interest_rate"),
        notes=data.get("notes"),
    )
    db.add(holding)
    db.flush()

    # Convenience: create the opening buy in the same call, when given.
    units = data.get("initial_units")
    amount = data.get("initial_amount")
    price = data.get("initial_price")
    if units and (amount or price):
        amount = amount if amount is not None else _money(units * price)
        price = price if price is not None else _money(amount / units)
        db.add(
            InvestmentTransaction(
                user_id=user_id,
                holding_id=holding.id,
                txn_type=InvestmentTxnType.BUY.value,
                txn_date=data.get("purchase_date") or date.today(),
                units=units,
                price_per_unit=price,
                amount=amount,
            )
        )
        db.flush()

    audit.record(
        db,
        user_id=user_id,
        action=AuditAction.CREATE.value,
        entity_type="investment_holding",
        entity_id=holding.id,
        summary=f"Added holding {holding.name}",
    )
    return holding


def update_holding(db: Session, user_id: uuid.UUID, holding_id: uuid.UUID, data: dict) -> InvestmentHolding:
    holding = get_owned(db, InvestmentHolding, holding_id, user_id)
    assert_owned(db, InvestmentAccount, data.get("account_id"), user_id)

    for field_name in (
        "name", "symbol", "account_id", "manual_value", "maturity_date",
        "interest_rate", "notes", "is_active",
    ):
        if field_name in data and data[field_name] is not None:
            setattr(holding, field_name, data[field_name])

    if "current_price" in data and data["current_price"] is not None:
        holding.current_price = data["current_price"]
        holding.price_updated_at = datetime.now(timezone.utc)

    return holding


def delete_holding(db: Session, user_id: uuid.UUID, holding_id: uuid.UUID) -> None:
    holding = get_owned(db, InvestmentHolding, holding_id, user_id)
    holding.soft_delete()
    holding.is_active = False


def get_holding_detail(db: Session, user_id: uuid.UUID, holding_id: uuid.UUID) -> dict:
    holding = get_owned(db, InvestmentHolding, holding_id, user_id)
    txns = sorted(holding.transactions, key=lambda t: (t.txn_date, t.created_at), reverse=True)
    payload = serialise_holding(holding, list(holding.transactions))
    payload["transactions"] = [serialise_txn(t) for t in txns]
    return payload


# --- Transactions ----------------------------------------------------------


def add_transaction(db: Session, user_id: uuid.UUID, holding_id: uuid.UUID, data: dict) -> InvestmentTransaction:
    holding = get_owned(db, InvestmentHolding, holding_id, user_id)
    txn_type = data.get("txn_type") or InvestmentTxnType.BUY.value
    units = data.get("units") or Decimal("0")
    amount = data["amount"]

    if txn_type == InvestmentTxnType.SELL.value:
        position = compute_position(list(holding.transactions))
        if units > position.units:
            raise BadRequest(
                f"You only hold {position.units} units of {holding.name}.",
                details={"units_held": float(position.units)},
            )

    price = data.get("price_per_unit")
    if price is None and units:
        price = _money(amount / units)

    txn = InvestmentTransaction(
        user_id=user_id,
        holding_id=holding.id,
        txn_type=txn_type,
        txn_date=data.get("txn_date") or date.today(),
        units=units,
        price_per_unit=price or Decimal("0.00"),
        amount=amount,
        fees=data.get("fees") or Decimal("0.00"),
        notes=data.get("notes"),
    )
    db.add(txn)
    db.flush()

    audit.record(
        db,
        user_id=user_id,
        action=AuditAction.CREATE.value,
        entity_type="investment_transaction",
        entity_id=txn.id,
        summary=f"Recorded {txn_type} on {holding.name}",
    )
    return txn


def delete_transaction(db: Session, user_id: uuid.UUID, txn_id: uuid.UUID) -> None:
    txn = get_owned(db, InvestmentTransaction, txn_id, user_id)
    db.delete(txn)


# --- Portfolio summary -------------------------------------------------


def portfolio_summary(db: Session, user_id: uuid.UUID) -> dict:
    holdings = list(
        db.execute(
            owned_query(InvestmentHolding, user_id)
            .where(InvestmentHolding.is_active.is_(True))
            .options(selectinload(InvestmentHolding.transactions), selectinload(InvestmentHolding.account))
        ).scalars()
    )
    rows = [serialise_holding(h) for h in holdings]

    total_invested = sum((r["invested_amount"] for r in rows), ZERO)
    current_value = sum((r["current_value"] for r in rows), ZERO)
    unrealised = current_value - total_invested
    realised = sum((r["realised_pnl"] for r in rows), ZERO)
    dividends = sum((r["total_dividends"] for r in rows), ZERO)
    total_return = unrealised + realised + dividends
    return_percent = float(total_return / total_invested * 100) if total_invested > ZERO else 0.0

    # Portfolio-level XIRR: every holding's cash flows plus one "sale today"
    # flow per holding at its current value.
    all_flows: list[CashFlow] = []
    for holding in holdings:
        position = compute_position(list(holding.transactions))
        all_flows.extend(position.cash_flows)
        value = current_value_of(holding, position)
        if value > ZERO or position.units > ZERO_UNITS:
            all_flows.append(CashFlow(date.today(), float(value)))
    portfolio_xirr = xirr(all_flows)

    by_type: dict[str, dict] = {}
    for row in rows:
        bucket = by_type.setdefault(
            row["asset_type"], {"asset_type": row["asset_type"], "invested": ZERO, "current_value": ZERO}
        )
        bucket["invested"] += row["invested_amount"]
        bucket["current_value"] += row["current_value"]
    allocation = [
        {
            "asset_type": b["asset_type"],
            "invested": float(b["invested"]),
            "current_value": float(b["current_value"]),
            "share": round(float(b["current_value"] / current_value * 100), 1) if current_value > ZERO else 0.0,
        }
        for b in by_type.values()
    ]
    allocation.sort(key=lambda b: b["current_value"], reverse=True)

    ranked = sorted(rows, key=lambda r: r["unrealised_pnl"], reverse=True)
    top_gainers = [r for r in ranked if r["unrealised_pnl"] > ZERO][:5]
    top_losers = [r for r in ranked if r["unrealised_pnl"] < ZERO][-5:][::-1]

    month_of = func.substr(func.cast(InvestmentTransaction.txn_date, String), 1, 7)
    monthly_rows = db.execute(
        select(month_of.label("month"), func.coalesce(func.sum(InvestmentTransaction.amount), 0))
        .where(
            InvestmentTransaction.user_id == user_id,
            InvestmentTransaction.txn_type == InvestmentTxnType.BUY.value,
        )
        .group_by("month")
        .order_by("month")
    ).all()
    monthly_investment = [{"month": row[0], "amount": float(_money(row[1]))} for row in monthly_rows]

    return {
        "total_invested": total_invested,
        "current_value": current_value,
        "unrealised_pnl": unrealised,
        "realised_pnl": realised,
        "total_dividends": dividends,
        "total_return": total_return,
        "return_percent": round(return_percent, 2),
        "xirr_percent": round(portfolio_xirr * 100, 2) if portfolio_xirr is not None else None,
        "holding_count": len(rows),
        "by_asset_type": allocation,
        "top_gainers": top_gainers,
        "top_losers": top_losers,
        "monthly_investment": monthly_investment[-12:],
        "value_history": [],
    }


# --- Investment goal planner --------------------------------------------


def _portfolio_value(db: Session, user_id: uuid.UUID) -> Decimal:
    holdings = list(
        db.execute(
            owned_query(InvestmentHolding, user_id)
            .where(InvestmentHolding.is_active.is_(True))
            .options(selectinload(InvestmentHolding.transactions))
        ).scalars()
    )
    return sum(
        (current_value_of(h, compute_position(list(h.transactions))) for h in holdings), ZERO
    )


def serialise_goal(db: Session, user_id: uuid.UUID, goal: InvestmentGoal) -> dict:
    if goal.use_portfolio_value:
        corpus = _portfolio_value(db, user_id)
    else:
        corpus = goal.current_corpus or ZERO

    if goal.target_date:
        years = max((goal.target_date - date.today()).days / 365.0, 1 / 12)
    elif goal.current_age is not None and goal.target_age is not None:
        years = max(goal.target_age - goal.current_age, 1 / 12)
    else:
        years = 10.0

    projection = project_goal(
        current_corpus=corpus,
        monthly_sip=goal.monthly_investment,
        expected_annual_return=goal.expected_return,
        years=years,
        step_up_percent=goal.step_up_percent,
        target_amount=goal.target_amount,
    )

    return {
        "id": goal.id,
        "name": goal.name,
        "category": goal.category,
        "description": goal.description,
        "target_amount": goal.target_amount,
        "target_date": goal.target_date,
        "current_age": goal.current_age,
        "target_age": goal.target_age,
        "current_corpus": goal.current_corpus,
        "use_portfolio_value": goal.use_portfolio_value,
        "expected_return": goal.expected_return,
        "monthly_investment": goal.monthly_investment,
        "step_up_percent": goal.step_up_percent,
        "inflation_rate": goal.inflation_rate,
        "priority": goal.priority,
        "status": goal.status,
        "created_at": goal.created_at,
        "years_remaining": round(years, 1),
        "effective_corpus": _money(corpus),
        "projected_value": projection.future_value_at_current_sip,
        "required_monthly_sip": projection.required_monthly_sip,
        "shortfall": projection.shortfall,
        "surplus": projection.surplus,
        "on_track": projection.on_track,
        "projection_chart": projection.projection,
    }


def list_goals(db: Session, user_id: uuid.UUID) -> list[dict]:
    goals = db.execute(owned_query(InvestmentGoal, user_id).order_by(InvestmentGoal.target_date)).scalars()
    return [serialise_goal(db, user_id, g) for g in goals]


def create_goal(db: Session, user_id: uuid.UUID, data: dict) -> InvestmentGoal:
    goal = InvestmentGoal(user_id=user_id, **{k: v for k, v in data.items() if v is not None})
    db.add(goal)
    db.flush()
    return goal


def update_goal(db: Session, user_id: uuid.UUID, goal_id: uuid.UUID, data: dict) -> InvestmentGoal:
    goal = get_owned(db, InvestmentGoal, goal_id, user_id)
    for field_name, value in data.items():
        if value is not None:
            setattr(goal, field_name, value)
    return goal


def delete_goal(db: Session, user_id: uuid.UUID, goal_id: uuid.UUID) -> None:
    db.delete(get_owned(db, InvestmentGoal, goal_id, user_id))
