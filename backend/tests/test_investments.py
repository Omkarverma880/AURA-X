"""Investment portfolio: cost-basis accounting, returns and goal planning."""

from __future__ import annotations

from datetime import date, timedelta

INVESTMENTS = "/api/v1/investments"
GOALS = "/api/v1/investment-goals"


def unlocked(user, pin="4059"):
    user.set_pin(pin)
    user.unlock(pin)
    return user


def make_holding(user, **overrides):
    payload = {
        "name": "Nifty 50 Index Fund",
        "asset_type": "mutual_fund",
        "initial_units": 100,
        "initial_amount": 10000,
        "purchase_date": date.today().isoformat(),
        **overrides,
    }
    response = user.post(INVESTMENTS, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_investments_are_locked_without_pin_unlock(alice):
    alice.set_pin("3141")
    response = alice.get(INVESTMENTS)
    assert response.status_code == 423


def test_creating_a_holding_records_the_opening_buy(alice):
    unlocked(alice)
    holding = make_holding(alice)

    assert holding["units_held"] == 100
    assert holding["avg_price"] == 100
    assert holding["invested_amount"] == 10000
    # No live price entered yet: value falls back to cost, not zero.
    assert holding["current_value"] == 10000
    assert holding["unrealised_pnl"] == 0
    assert len(holding["transactions"]) == 1


def test_average_price_updates_across_multiple_buys(alice):
    unlocked(alice)
    holding = make_holding(alice, initial_units=100, initial_amount=10000)

    alice.post(
        f"{INVESTMENTS}/{holding['id']}/transactions",
        json={"txn_type": "buy", "units": 100, "amount": 12000},
    )
    detail = alice.get(f"{INVESTMENTS}/{holding['id']}").json()

    assert detail["units_held"] == 200
    assert detail["invested_amount"] == 22000
    assert detail["avg_price"] == 110.00


def test_updating_current_price_computes_unrealised_pnl(alice):
    unlocked(alice)
    holding = make_holding(alice, initial_units=100, initial_amount=10000)

    updated = alice.patch(f"{INVESTMENTS}/{holding['id']}", json={"current_price": 125})
    assert updated.status_code == 200
    body = updated.json()
    assert body["current_value"] == 12500
    assert body["unrealised_pnl"] == 2500
    assert body["return_percent"] == 25.0


def test_sell_realises_pnl_against_average_cost(alice):
    unlocked(alice)
    holding = make_holding(alice, initial_units=100, initial_amount=10000)  # avg 100

    response = alice.post(
        f"{INVESTMENTS}/{holding['id']}/transactions",
        json={"txn_type": "sell", "units": 40, "amount": 5200},  # sold at 130
    )
    assert response.status_code == 201
    detail = response.json()

    assert detail["units_held"] == 60
    assert detail["invested_amount"] == 6000  # 60 units still at avg cost 100
    assert detail["realised_pnl"] == 1200  # (5200 - 40*100)


def test_cannot_sell_more_units_than_held(alice):
    unlocked(alice)
    holding = make_holding(alice, initial_units=50, initial_amount=5000)
    response = alice.post(
        f"{INVESTMENTS}/{holding['id']}/transactions",
        json={"txn_type": "sell", "units": 100, "amount": 12000},
    )
    assert response.status_code == 400


def test_dividends_do_not_change_units_but_add_to_income(alice):
    unlocked(alice)
    holding = make_holding(alice, initial_units=100, initial_amount=10000)
    alice.post(
        f"{INVESTMENTS}/{holding['id']}/transactions",
        json={"txn_type": "dividend", "amount": 250},
    )
    detail = alice.get(f"{INVESTMENTS}/{holding['id']}").json()
    assert detail["units_held"] == 100
    assert detail["total_dividends"] == 250


def test_bonus_units_dilute_average_price(alice):
    unlocked(alice)
    holding = make_holding(alice, initial_units=100, initial_amount=10000)  # avg 100
    alice.post(
        f"{INVESTMENTS}/{holding['id']}/transactions",
        json={"txn_type": "bonus", "units": 100, "amount": 0},
    )
    detail = alice.get(f"{INVESTMENTS}/{holding['id']}").json()
    assert detail["units_held"] == 200
    assert detail["invested_amount"] == 10000  # cost unchanged
    assert detail["avg_price"] == 50.00


def test_holding_xirr_is_reasonable_for_a_one_year_gain(alice):
    unlocked(alice)
    a_year_ago = (date.today() - timedelta(days=365)).isoformat()
    holding = make_holding(
        alice, initial_units=100, initial_amount=100000, purchase_date=a_year_ago
    )
    updated = alice.patch(f"{INVESTMENTS}/{holding['id']}", json={"current_price": 1100})
    body = updated.json()
    assert body["xirr_percent"] is not None
    assert 8 <= body["xirr_percent"] <= 12  # ~10% annual gain


def test_portfolio_summary_aggregates_holdings(alice):
    unlocked(alice)
    h1 = make_holding(alice, name="Fund A", initial_units=100, initial_amount=10000)
    make_holding(alice, name="Gold ETF", asset_type="gold", initial_units=10, initial_amount=5000)
    alice.patch(f"{INVESTMENTS}/{h1['id']}", json={"current_price": 120})

    summary = alice.get(f"{INVESTMENTS}/summary").json()
    assert summary["total_invested"] == 15000
    assert summary["current_value"] == 17000  # 12000 + 5000
    assert summary["unrealised_pnl"] == 2000
    assert summary["holding_count"] == 2
    assert len(summary["by_asset_type"]) == 2


def test_account_can_be_linked_and_deletion_detaches_holdings(alice):
    unlocked(alice)
    account = alice.post(INVESTMENTS + "/accounts", json={"name": "Zerodha", "broker": "Zerodha"}).json()
    holding = make_holding(alice, account_id=account["id"])
    assert holding["account_name"] == "Zerodha"

    response = alice.delete(f"{INVESTMENTS}/accounts/{account['id']}")
    assert response.status_code == 200

    detail = alice.get(f"{INVESTMENTS}/{holding['id']}").json()
    assert detail["account_id"] is None


# --- Investment goal planner ---------------------------------------------


def test_goal_planner_computes_required_sip(alice):
    unlocked(alice)
    response = alice.post(
        GOALS,
        json={
            "name": "Retirement",
            "target_amount": 10000000,
            "current_age": 30,
            "target_age": 45,
            "expected_return": 12,
            "monthly_investment": 0,
            "use_portfolio_value": False,
            "current_corpus": 0,
        },
    )
    assert response.status_code == 201
    goal = response.json()
    assert goal["years_remaining"] == 15.0
    assert goal["on_track"] is False
    # ~1cr in 15y at 12% needs roughly 21k/month.
    assert 19000 <= goal["required_monthly_sip"] <= 23000


def test_goal_on_track_when_sip_is_sufficient(alice):
    unlocked(alice)
    response = alice.post(
        GOALS,
        json={
            "name": "House",
            "target_amount": 5000000,
            "target_date": (date.today().replace(year=date.today().year + 10)).isoformat(),
            "expected_return": 10,
            "monthly_investment": 30000,
            "use_portfolio_value": False,
            "current_corpus": 500000,
        },
    )
    assert response.status_code == 201
    goal = response.json()
    assert goal["on_track"] is True
    assert goal["shortfall"] == 0


def test_goal_uses_live_portfolio_value_when_requested(alice):
    unlocked(alice)
    make_holding(alice, initial_units=100, initial_amount=200000)  # 2L invested

    goal = alice.post(
        GOALS,
        json={
            "name": "Freedom",
            "target_amount": 20000000,
            "current_age": 30,
            "target_age": 40,
            "use_portfolio_value": True,
            "monthly_investment": 50000,
        },
    ).json()
    assert goal["effective_corpus"] == 200000


def test_goal_target_age_must_be_after_current_age(alice):
    unlocked(alice)
    response = alice.post(
        GOALS,
        json={
            "name": "Bad Goal",
            "target_amount": 100000,
            "current_age": 40,
            "target_age": 35,
        },
    )
    assert response.status_code == 422


# --- Cross-user isolation -------------------------------------------------


def test_cross_user_investment_isolation(alice, bob):
    unlocked(alice)
    unlocked(bob, "5926")
    holding = make_holding(alice)

    assert bob.get(f"{INVESTMENTS}/{holding['id']}").status_code == 404
    assert bob.patch(f"{INVESTMENTS}/{holding['id']}", json={"current_price": 1}).status_code == 404
    assert bob.get(INVESTMENTS).json() == []

    goal = alice.post(GOALS, json={"name": "Alice Goal", "target_amount": 100000}).json()
    assert bob.get(GOALS).json() == []
    assert bob.delete(f"{GOALS}/{goal['id']}").status_code == 404
