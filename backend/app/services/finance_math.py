"""Financial math: XIRR and the goal-planner projection.

No numpy/scipy dependency: XIRR is a one-dimensional root-find, which Newton's
method (falling back to bisection when it misbehaves) solves in a handful of
iterations without pulling in a heavy numerical stack.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

DAYS_PER_YEAR = 365.0


@dataclass
class CashFlow:
    when: date
    amount: float  # negative = money out (invested), positive = money in (value/withdrawal)


def _xnpv(rate: float, flows: list[CashFlow], t0: date) -> float:
    if rate <= -1.0:
        return float("inf")
    return sum(
        flow.amount / (1.0 + rate) ** ((flow.when - t0).days / DAYS_PER_YEAR) for flow in flows
    )


def _xnpv_derivative(rate: float, flows: list[CashFlow], t0: date) -> float:
    if rate <= -1.0:
        return float("inf")
    return sum(
        -((flow.when - t0).days / DAYS_PER_YEAR)
        * flow.amount
        / (1.0 + rate) ** (((flow.when - t0).days / DAYS_PER_YEAR) + 1)
        for flow in flows
    )


def xirr(flows: list[CashFlow], *, guess: float = 0.15) -> float | None:
    """Annualised internal rate of return for irregularly dated cash flows.

    Returns None when there is not enough signal to solve (fewer than two
    flows, or no sign change - e.g. only inflows with no investment).
    """
    if len(flows) < 2:
        return None
    if not (any(f.amount < 0 for f in flows) and any(f.amount > 0 for f in flows)):
        return None

    flows = sorted(flows, key=lambda f: f.when)
    t0 = flows[0].when
    rate = guess

    # Newton's method: fast when it converges, which is nearly always for
    # well-behaved personal-portfolio cash flow patterns.
    for _ in range(50):
        value = _xnpv(rate, flows, t0)
        derivative = _xnpv_derivative(rate, flows, t0)
        if derivative == 0:
            break
        next_rate = rate - value / derivative
        if next_rate <= -1.0:
            break
        if abs(next_rate - rate) < 1e-7:
            return round(next_rate, 6)
        rate = next_rate

    # Fall back to bisection over a wide, sane bracket.
    low, high = -0.99, 10.0
    f_low, f_high = _xnpv(low, flows, t0), _xnpv(high, flows, t0)
    if f_low * f_high > 0:
        return None

    for _ in range(200):
        mid = (low + high) / 2
        f_mid = _xnpv(mid, flows, t0)
        if abs(f_mid) < 1e-6:
            return round(mid, 6)
        if f_low * f_mid < 0:
            high, f_high = mid, f_mid
        else:
            low, f_low = mid, f_mid
    return round((low + high) / 2, 6)


def simple_return_percent(invested: Decimal, current_value: Decimal) -> float:
    """Absolute (non-annualised) return - used when there is not enough date
    spread for XIRR to mean anything, e.g. a holding bought all at once
    yesterday."""
    if invested <= 0:
        return 0.0
    return float((current_value - invested) / invested * 100)


# --- Goal planner --------------------------------------------------------


@dataclass
class GoalProjection:
    years: float
    months: int
    future_value_at_current_sip: Decimal
    required_monthly_sip: Decimal
    shortfall: Decimal
    surplus: Decimal
    on_track: bool
    projection: list[dict]  # yearly {year, corpus} points for the chart


def _future_value_of_sip(
    monthly_sip: float, monthly_rate: float, months: int, step_up_annual: float = 0.0
) -> float:
    """Future value of a monthly SIP, optionally increased by step_up_annual
    once per completed year (a realistic model of an annual salary-linked
    step-up in contributions)."""
    corpus = 0.0
    sip = monthly_sip
    for month in range(1, months + 1):
        corpus = corpus * (1 + monthly_rate) + sip
        if step_up_annual and month % 12 == 0:
            sip *= 1 + step_up_annual
    return corpus


def project_goal(
    *,
    current_corpus: Decimal,
    monthly_sip: Decimal,
    expected_annual_return: Decimal,
    years: float,
    step_up_percent: Decimal = Decimal("0"),
    target_amount: Decimal | None = None,
) -> GoalProjection:
    """Project a SIP forward and, when a target is given, solve for the
    monthly contribution that would reach it.

    A closed-form annuity formula would break the moment a step-up is
    involved, so the projection is simulated month by month instead - cheap
    enough for a single goal and exact for any step-up pattern.
    """
    months = max(int(round(years * 12)), 1)
    annual_rate = float(expected_annual_return) / 100
    monthly_rate = (1 + annual_rate) ** (1 / 12) - 1
    step_up = float(step_up_percent) / 100

    corpus_now = float(current_corpus)
    sip_now = float(monthly_sip)

    fv_from_corpus = corpus_now * (1 + monthly_rate) ** months
    fv_from_sip = _future_value_of_sip(sip_now, monthly_rate, months, step_up)
    future_value = Decimal(str(round(fv_from_corpus + fv_from_sip, 2)))

    # Yearly points for the projection chart.
    yearly_points = []
    running_corpus = corpus_now
    running_sip = sip_now
    for year in range(1, int(months / 12) + 1):
        for month in range(12):
            running_corpus = running_corpus * (1 + monthly_rate) + running_sip
        if step_up:
            running_sip *= 1 + step_up
        yearly_points.append({"year": year, "corpus": round(running_corpus, 2)})

    required_sip = monthly_sip
    shortfall = Decimal("0.00")
    surplus = Decimal("0.00")
    on_track = True

    if target_amount is not None:
        target = float(target_amount)
        if future_value >= target_amount:
            surplus = future_value - target_amount
        else:
            shortfall = target_amount - future_value
            on_track = False
            # Binary-search the monthly SIP that lands exactly on the target,
            # holding the same step-up pattern.
            low, high = 0.0, max(sip_now, 1.0) * 1.0
            while fv_from_corpus + _future_value_of_sip(high, monthly_rate, months, step_up) < target:
                high *= 2
                if high > 10**9:
                    break
            for _ in range(60):
                mid = (low + high) / 2
                fv = fv_from_corpus + _future_value_of_sip(mid, monthly_rate, months, step_up)
                if fv < target:
                    low = mid
                else:
                    high = mid
            required_sip = Decimal(str(round(high, 2)))

    return GoalProjection(
        years=years,
        months=months,
        future_value_at_current_sip=future_value,
        required_monthly_sip=required_sip,
        shortfall=shortfall,
        surplus=surplus,
        on_track=on_track,
        projection=yearly_points,
    )
