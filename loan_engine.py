from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import pow
from typing import List, Dict, Tuple


TYPE_IN_FINE = "IN_FINE"
TYPE_CONSTANT_AMORTIZATION = "CONSTANT_AMORTIZATION"
TYPE_SPECIFIC_REPAYMENT = "SPECIFIC_REPAYMENT"

BASE_MENSUELLE_12 = "BASE_12"   # annualRate * freq / 12
BASE_360 = "BASE_360"           # interest = balance * (annualRate/360) * days ; approx month length 30.478 for periodic conversion


@dataclass
class ScheduleRow:
    period: int
    date: date
    payment: float
    interest: float
    principal: float
    balance: float


def _add_months(d: date, months: int) -> date:
    # add months without external libs (simple + safe)
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    # clamp day to month end
    import calendar
    last_day = calendar.monthrange(y, m)[1]
    day = min(d.day, last_day)
    return date(y, m, day)


def _days_between(d1: date, d2: date) -> int:
    return (d2 - d1).days


def _periodic_rate(annual_rate: float, frequency_months: int, base: str) -> float:
    """
    Returns periodic rate (for BASE_12) or an equivalent factor (for BASE_360) used in some formulas.
    Note: for BASE_360 we usually compute interest with daily rate * days.
    """
    if base == BASE_MENSUELLE_12:
        return annual_rate * frequency_months / 12.0
    # base 360: in the Java code they sometimes use rate * freq * 30.478 / 360 for periodic conversion
    return annual_rate * frequency_months * 30.478 / 360.0


def _monthly_payment_annuity(principal: float, annual_rate: float, total_payments: int, periodic_rate: float) -> float:
    # periodic_rate is already per period (e.g., monthly if frequency_months=1)
    r = periodic_rate
    n = total_payments
    if n <= 0:
        return 0.0
    if abs(r) < 1e-12:
        return principal / n
    return principal * (r * pow(1 + r, n)) / (pow(1 + r, n) - 1)


def _compute_teg_irr_bisection(cashflows: List[float], a: float = 0.0, b: float = 1.10, eps: float = 1e-6) -> float:
    """
    Find IRR 't' such that sum_{i=0..n} CF_i / (1+t)^i = 0, with CF_0 positive (net disbursed),
    subsequent negative (payments). Returns per-period IRR.
    """
    def f(t: float) -> float:
        s = 0.0
        for i, cf in enumerate(cashflows):
            s += cf / pow(1 + t, i)
        return s

    fa, fb = f(a), f(b)
    if fa * fb > 0:
        return float("nan")

    while abs(b - a) > eps:
        c = (a + b) / 2.0
        fc = f(c)
        if fa * fc <= 0:
            b, fb = c, fc
        else:
            a, fa = c, fc
    return (a + b) / 2.0


def build_schedule(
    repayment_type: str,
    amount: float,
    annual_rate: float,
    period_count: int,
    payment_frequency_months: int,
    base: str,
    disbursement_date: date,
    first_installment_date: date,
    # specific repayment options
    interest_frequency_months: int = 1,
    deferred_periods: int = 0,
    flat: bool = False,
    fee_amount: float = 0.0,
) -> Tuple[List[ScheduleRow], Dict[str, float]]:
    """
    Returns (schedule_rows, summary)
    schedule_rows: full schedule rows
    summary: totals + TEG if applicable
    """

    if amount < 0 or annual_rate < 0 or period_count <= 0 or payment_frequency_months <= 0:
        return [], {}

    if repayment_type == TYPE_IN_FINE:
        return _schedule_in_fine(amount, annual_rate, period_count, payment_frequency_months, base, disbursement_date, first_installment_date)

    if repayment_type == TYPE_CONSTANT_AMORTIZATION:
        return _schedule_constant_amortization(amount, annual_rate, period_count, payment_frequency_months, base, disbursement_date, first_installment_date)

    if repayment_type == TYPE_SPECIFIC_REPAYMENT:
        return _schedule_specific(
            amount=amount,
            annual_rate=annual_rate,
            period_count=period_count,
            payment_frequency_months=payment_frequency_months,
            interest_frequency_months=interest_frequency_months,
            deferred_periods=deferred_periods,
            flat=flat,
            fee_amount=fee_amount,
            base=base,
            disbursement_date=disbursement_date,
            first_installment_date=first_installment_date,
        )

    return [], {}


def _schedule_in_fine(amount: float, annual_rate: float, period_count: int, freq_m: int, base: str, disb: date, first: date):
    rows: List[ScheduleRow] = []
    bal = amount
    periodic = _periodic_rate(annual_rate, freq_m, base)

    # In fine: interest each period, principal at last period
    current = first
    total_payment = total_interest = total_principal = 0.0

    for i in range(1, period_count + 1):
        # interest
        if base == BASE_MENSUELLE_12:
            interest = bal * periodic
        else:
            # daily
            if i == 1:
                days = _days_between(disb, current)
            else:
                prev = _add_months(current, -freq_m)
                days = _days_between(prev, current)
            daily = annual_rate / 360.0
            interest = bal * daily * days

        principal = amount if i == period_count else 0.0
        payment = interest + principal
        bal = max(0.0, bal - principal)

        rows.append(ScheduleRow(i, current, payment, interest, principal, bal))

        total_payment += payment
        total_interest += interest
        total_principal += principal
        current = _add_months(current, freq_m)

    summary = {
        "total_payment": total_payment,
        "total_interest": total_interest,
        "total_principal": total_principal,
    }
    return rows, summary


def _schedule_constant_amortization(amount: float, annual_rate: float, period_count: int, freq_m: int, base: str, disb: date, first: date):
    rows: List[ScheduleRow] = []
    bal = amount
    amort = amount / period_count

    periodic = _periodic_rate(annual_rate, freq_m, base)
    daily = annual_rate / 360.0

    current = first
    total_payment = total_interest = total_principal = 0.0

    for i in range(1, period_count + 1):
        if base == BASE_MENSUELLE_12:
            interest = bal * periodic
        else:
            if i == 1:
                days = _days_between(disb, current)
            else:
                prev = _add_months(current, -freq_m)
                days = _days_between(prev, current)
            interest = bal * daily * days

        principal = amort
        payment = principal + interest
        bal = max(0.0, bal - principal)

        rows.append(ScheduleRow(i, current, payment, interest, principal, bal))

        total_payment += payment
        total_interest += interest
        total_principal += principal
        current = _add_months(current, freq_m)

    summary = {
        "total_payment": total_payment,
        "total_interest": total_interest,
        "total_principal": total_principal,
    }
    return rows, summary


def _schedule_specific(
    amount: float,
    annual_rate: float,
    period_count: int,
    payment_frequency_months: int,
    interest_frequency_months: int,
    deferred_periods: int,
    flat: bool,
    fee_amount: float,
    base: str,
    disbursement_date: date,
    first_installment_date: date,
):
    """
    "Specific" repayment close to your Java behavior:
    - interest calculated each interest_frequency period
    - payment occurs every payment_frequency period (can be multiple of interest_frequency)
    - deferred_periods: periods where no payment/interest
    - last period closes remaining balance
    - computes a TEG-like IRR from net disbursed (amount - fee) and payments (negative)
    """
    rows: List[ScheduleRow] = []
    bal = amount

    # Adjusted number of interest periods
    if interest_frequency_months <= 0:
        interest_frequency_months = 1
    adjusted_periods = period_count // interest_frequency_months
    if adjusted_periods <= 0:
        adjusted_periods = 1

    # Rates
    daily = annual_rate / 360.0
    if base == BASE_MENSUELLE_12:
        rate_per_interest_period = annual_rate * interest_frequency_months / 12.0
    else:
        # used only for some annuity-style formula; interest itself uses daily*days
        rate_per_interest_period = annual_rate * interest_frequency_months * 30.478 / 360.0

    # Determine payment cadence in interest periods
    # e.g. payment every 3 months, interest monthly => payment_step = 3/1 = 3
    payment_step = max(1, payment_frequency_months // interest_frequency_months)

    # Number of payments after deferment
    total_payment_events = (period_count // payment_frequency_months) - deferred_periods
    total_payment_events = max(1, total_payment_events)

    # Periodic payment (vpm) using annuity formula on payment events
    # For simplicity/pro: we compute payment per payment event using rate corresponding to payment frequency
    if base == BASE_MENSUELLE_12:
        r_pay = annual_rate * payment_frequency_months / 12.0
    else:
        r_pay = annual_rate * payment_frequency_months * 30.478 / 360.0

    vpm = _monthly_payment_annuity(amount, annual_rate, total_payment_events, r_pay)

    current = first_installment_date
    total_payment = total_interest = total_principal = 0.0

    payments_for_irr: List[float] = [amount - fee_amount]  # CF0 positive (net disbursed)

    interest_carry = 0.0

    for i in range(1, adjusted_periods + 1):
        payment = 0.0
        principal = 0.0
        interest = 0.0

        if i <= deferred_periods:
            # defer: no interest charged and no payments (matching your Java)
            interest = 0.0
            payment = 0.0
            principal = 0.0
        else:
            # compute interest for this interest period
            if base == BASE_MENSUELLE_12:
                interest = bal * rate_per_interest_period
            else:
                # days between previous and current interest date
                if i == 1:
                    days = _days_between(disbursement_date, current)
                else:
                    prev = _add_months(current, -interest_frequency_months)
                    days = _days_between(prev, current)
                interest = bal * daily * days

            # payment happens at cadence
            is_payment_event = (i % payment_step == 0)

            if is_payment_event:
                payment = vpm
                # manage carry like your interestDiff
                if payment < (interest_carry + interest):
                    # not enough to cover interest
                    interest_carry = interest_carry + interest - payment
                    interest = payment
                    principal = 0.0
                else:
                    if interest_carry != 0:
                        interest = interest_carry + interest
                        interest_carry = 0.0
                    principal = max(0.0, payment - interest)

                # last period: close balance
                if i == adjusted_periods:
                    payment = bal + interest
                    principal = max(0.0, payment - interest)

            else:
                # interest-only line
                payment = interest
                principal = 0.0

        bal = max(0.0, bal - principal)

        rows.append(ScheduleRow(i, current, payment, interest, principal, bal))

        total_payment += payment
        total_interest += interest
        total_principal += principal
        payments_for_irr.append(-payment)  # outflow

        current = _add_months(current, interest_frequency_months)

    # TEG (approx) per interest period -> annualized
    irr = _compute_teg_irr_bisection(payments_for_irr)
    if irr != irr:  # NaN
        teg = float("nan")
    else:
        # annualize based on interest_frequency_months
        teg = pow(1 + irr, (12.0 / interest_frequency_months)) - 1.0

    summary = {
        "total_payment": total_payment,
        "total_interest": total_interest,
        "total_principal": total_principal,
        "vpm": vpm,
        "teg": teg,
    }
    return rows, summary
