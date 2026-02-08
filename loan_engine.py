from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import pow
from typing import List, Dict, Tuple
from typing import Optional


# ============================
# TYPES
# ============================
TYPE_IN_FINE = "IN_FINE"
TYPE_CONSTANT_AMORTIZATION = "CONSTANT_AMORTIZATION"
TYPE_ANNUITY = "ANNUITY"  # Annuité constante (paiement constant)

# ============================
# BASES
# ============================
BASE_MENSUELLE_12 = "BASE_12"   # r = annual_rate * freq / 12
BASE_360 = "BASE_360"           # interest = balance * (annual_rate/360) * days


@dataclass
class ScheduleRow:
    period: int
    date: date
    payment: float
    interest: float
    principal: float
    balance: float


# ============================
# DATE HELPERS
# ============================
def _add_months(d: date, months: int) -> date:
    import calendar
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    last_day = calendar.monthrange(y, m)[1]
    day = min(d.day, last_day)
    return date(y, m, day)


def _days_between(d1: date, d2: date) -> int:
    return (d2 - d1).days

def _npv_rate_with_dates(rate: float, cashflows: List[float], dates: List[date], day_basis: int) -> float:
    """NPV(rate) with irregular dates: sum(CF_k / (1+rate)^(days_k/basis))."""
    if rate <= -0.999999:
        return float("inf")

    d0 = dates[0]
    total = 0.0
    for cf, dk in zip(cashflows, dates):
        days = (dk - d0).days
        t = days / float(day_basis)
        total += cf / pow(1.0 + rate, t)
    return total


def _irr_bisection_with_dates(
    cashflows: List[float],
    dates: List[date],
    day_basis: int,
    low: float = 0.0,
    high: float = 5.0,
    eps: float = 1e-7,
    max_iter: int = 200,
) -> float:
    """
    Find IRR such that NPV=0 using bisection.
    Returns annual rate (since we use year fractions).
    """
    f_low = _npv_rate_with_dates(low, cashflows, dates, day_basis)
    f_high = _npv_rate_with_dates(high, cashflows, dates, day_basis)

    # Expand high if needed
    tries = 0
    while f_low * f_high > 0 and tries < 12:
        high *= 2.0
        f_high = _npv_rate_with_dates(high, cashflows, dates, day_basis)
        tries += 1

    if f_low * f_high > 0:
        return float("nan")

    a, b = low, high
    fa, fb = f_low, f_high

    for _ in range(max_iter):
        c = (a + b) / 2.0
        fc = _npv_rate_with_dates(c, cashflows, dates, day_basis)
        if abs(fc) < eps or abs(b - a) < eps:
            return c
        if fa * fc <= 0:
            b, fb = c, fc
        else:
            a, fa = c, fc

    return (a + b) / 2.0


def compute_taeg(
    disbursement_date: date,
    amount: float,
    fee_amount: float,
    rows: List["ScheduleRow"],
    base: str,
) -> float:
    """
    TAEG (annual IRR) from:
      CF0 = + (amount - fee)
      CFk = - payment at each schedule row date where payment > 0
    day_basis: 365 for BASE_12, 360 for BASE_360 (convention bancaire)
    """
    if amount <= 0:
        return float("nan")

    day_basis = 360 if base == BASE_360 else 365

    cashflows = [float(amount - fee_amount)]
    dates = [disbursement_date]

    for r in rows:
        if r.payment and r.payment > 0:
            cashflows.append(-float(r.payment))
            dates.append(r.date)

    # Need at least one outflow
    if len(cashflows) < 2:
        return float("nan")

    return _irr_bisection_with_dates(cashflows, dates, day_basis=day_basis)

# ============================
# RATES + INTEREST
# ============================
def _rate_base12(annual_rate: float, frequency_months: int) -> float:
    return annual_rate * frequency_months / 12.0


def _rate_equiv_360(annual_rate: float, frequency_months: int) -> float:
    # conversion approchée mensualisée (comme ton Java)
    return annual_rate * frequency_months * 30.478 / 360.0


def _interest_amount(
    balance: float,
    annual_rate: float,
    base: str,
    period_index: int,
    current_date: date,
    prev_date: date | None,
    disbursement_date: date,
    frequency_months: int,
) -> float:
    """
    Intérêt par période :
    - BASE_12 : I = balance * r_period
    - BASE_360 : I = balance * (annual_rate/360) * nb_jours
    """
    if balance <= 0:
        return 0.0

    if base == BASE_MENSUELLE_12:
        r = _rate_base12(annual_rate, frequency_months)
        return balance * r

    # BASE_360
    daily = annual_rate / 360.0
    if period_index == 1:
        days = _days_between(disbursement_date, current_date)
    else:
        if prev_date is None:
            prev_date = _add_months(current_date, -frequency_months)
        days = _days_between(prev_date, current_date)
    return balance * daily * max(days, 0)


# ============================
# CORE API
# ============================
def build_schedule(
    repayment_type: str,
    amount: float,
    annual_rate: float,
    period_count: int,
    payment_frequency_months: int,
    base: str,
    disbursement_date: date,
    first_installment_date: date,
    # paramètres avancés
    interest_frequency_months: int = 1,
    deferred_periods: int = 0,
    flat: bool = False,
    fee_amount: float = 0.0,
) -> Tuple[List[ScheduleRow], Dict[str, float]]:
    """
    Retourne (rows, summary)

    - repayment_type : IN_FINE / CONSTANT_AMORTIZATION / ANNUITY
    - payment_frequency_months : fréquence des paiements
    - interest_frequency_months : fréquence de calcul des intérêts (peut être différente)
    - deferred_periods : périodes de différé (pas de remboursement du principal)
    - flat : intérêts calculés sur capital initial (surtout pour annuité)
    - fee_amount : frais (impact coût total, et TEG si tu ajoutes IRR plus tard)
    """

    # validations simples
    if amount <= 0 or annual_rate < 0 or period_count <= 0:
        return [], {}
    if payment_frequency_months <= 0 or interest_frequency_months <= 0:
        return [], {}

    if repayment_type == TYPE_IN_FINE:
        return _schedule_in_fine(
            amount, annual_rate, period_count,
            payment_frequency_months, interest_frequency_months,
            deferred_periods, base, disbursement_date, first_installment_date, fee_amount
        )

    if repayment_type == TYPE_CONSTANT_AMORTIZATION:
        return _schedule_constant_amortization(
            amount, annual_rate, period_count,
            payment_frequency_months, interest_frequency_months,
            deferred_periods, base, disbursement_date, first_installment_date, fee_amount
        )

    if repayment_type == TYPE_ANNUITY:
        return _schedule_annuity(
            amount, annual_rate, period_count,
            payment_frequency_months, interest_frequency_months,
            deferred_periods, flat, base, disbursement_date, first_installment_date, fee_amount
        )

    return [], {}


# ============================
# MODE 1 — IN FINE
# ============================
def _schedule_in_fine(
    amount: float,
    annual_rate: float,
    period_count: int,
    payment_freq_m: int,
    interest_freq_m: int,
    deferred_periods: int,
    base: str,
    disb: date,
    first: date,
    fee_amount: float,
) -> Tuple[List[ScheduleRow], Dict[str, float]]:
    """
    In fine :
    - intérêts à chaque échéance d'intérêt
    - paiements possibles à une cadence différente (payment_freq)
    - principal payé à la dernière échéance de paiement
    - différé : pendant deferred_periods (périodes d’intérêt), aucun paiement
    """
    rows: List[ScheduleRow] = []
    balance = amount

    # nombre de périodes d'intérêt
    n_interest = max(1, period_count // interest_freq_m)
    payment_step = max(1, payment_freq_m // interest_freq_m)

    current = first
    prev_date = None

    total_payment = total_interest = total_principal = 0.0

    for i in range(1, n_interest + 1):
        # différé : pas de paiement / pas de principal
        if i <= deferred_periods:
            interest = 0.0
            payment = 0.0
            principal = 0.0
        else:
            interest = _interest_amount(
                balance=balance,
                annual_rate=annual_rate,
                base=base,
                period_index=i,
                current_date=current,
                prev_date=prev_date,
                disbursement_date=disb,
                frequency_months=interest_freq_m,
            )

            is_payment_event = (i % payment_step == 0)

            # Paiement uniquement à chaque event de paiement
            if is_payment_event:
                # principal uniquement au dernier paiement
                if i == n_interest:
                    principal = balance
                else:
                    principal = 0.0
                payment = interest + principal
            else:
                # ligne d’intérêt (sans paiement)
                payment = interest
                principal = 0.0

        balance = max(0.0, balance - principal)

        rows.append(ScheduleRow(i, current, payment, interest, principal, balance))
        total_payment += payment
        total_interest += interest
        total_principal += principal

        prev_date = current
        current = _add_months(current, interest_freq_m)

    summary = {
        "total_payment": total_payment,
        "total_interest": total_interest,
        "total_principal": total_principal,
        "fee_amount": fee_amount,
    }
    summary["taeg"] = compute_taeg(disb, amount, fee_amount, rows, base)
    return rows, summary


# ============================
# MODE 2 — AMORTISSEMENT CONSTANT
# ============================
def _schedule_constant_amortization(
    amount: float,
    annual_rate: float,
    period_count: int,
    payment_freq_m: int,
    interest_freq_m: int,
    deferred_periods: int,
    base: str,
    disb: date,
    first: date,
    fee_amount: float,
) -> Tuple[List[ScheduleRow], Dict[str, float]]:
    """
    Amortissement constant :
    - principal constant payé uniquement aux dates de paiement
    - intérêts calculés à la fréquence interest_freq_m
    - si paiement moins fréquent que les intérêts, on capitalise l’intérêt dans les paiements (carry)
    """
    rows: List[ScheduleRow] = []
    balance = amount

    n_interest = max(1, period_count // interest_freq_m)
    payment_step = max(1, payment_freq_m // interest_freq_m)

    # nombre d’évènements de paiement après différé
    n_payments = max(1, (period_count // payment_freq_m) - max(0, deferred_periods // payment_step))
    amort_per_payment = amount / n_payments

    current = first
    prev_date = None

    carry_interest = 0.0
    total_payment = total_interest = total_principal = 0.0

    payment_event_count = 0

    for i in range(1, n_interest + 1):
        if i <= deferred_periods:
            interest = 0.0
            payment = 0.0
            principal = 0.0
        else:
            interest = _interest_amount(
                balance=balance,
                annual_rate=annual_rate,
                base=base,
                period_index=i,
                current_date=current,
                prev_date=prev_date,
                disbursement_date=disb,
                frequency_months=interest_freq_m,
            )

            is_payment_event = (i % payment_step == 0)

            if is_payment_event:
                payment_event_count += 1

                # paiement = amortissement + intérêts accumulés
                interest_total = interest + carry_interest
                carry_interest = 0.0

                principal = amort_per_payment
                # dernier paiement : on ferme le solde
                if payment_event_count == n_payments:
                    principal = balance

                payment = principal + interest_total

            else:
                # pas de paiement => on accumule les intérêts
                carry_interest += interest
                payment = 0.0
                principal = 0.0

        balance = max(0.0, balance - principal)

        rows.append(ScheduleRow(i, current, payment, interest, principal, balance))
        total_payment += payment
        total_interest += interest
        total_principal += principal

        prev_date = current
        current = _add_months(current, interest_freq_m)

    summary = {
        "total_payment": total_payment,
        "total_interest": total_interest,
        "total_principal": total_principal,
        "fee_amount": fee_amount,
    }
    summary["taeg"] = compute_taeg(disb, amount, fee_amount, rows, base)
    return rows, summary


# ============================
# MODE 3 — ANNUITE CONSTANTE
# ============================
def _annuity_payment(P: float, r: float, n: int) -> float:
    if n <= 0:
        return 0.0
    if abs(r) < 1e-12:
        return P / n
    return (P * r) / (1 - pow(1 + r, -n))


def _schedule_annuity(
    amount: float,
    annual_rate: float,
    period_count: int,
    payment_freq_m: int,
    interest_freq_m: int,
    deferred_periods: int,
    flat: bool,
    base: str,
    disb: date,
    first: date,
    fee_amount: float,
) -> Tuple[List[ScheduleRow], Dict[str, float]]:
    """
    Annuité constante :
    - on calcule une échéance constante aux dates de paiement
    - intérêts calculés à la fréquence interest_freq_m
    - si flat=True : intérêts basés sur capital initial (P0), sinon sur solde restant
    - si paiement moins fréquent que les intérêts : intérêts s'accumulent (carry)
    """
    rows: List[ScheduleRow] = []
    balance = amount

    n_interest = max(1, period_count // interest_freq_m)
    payment_step = max(1, payment_freq_m // interest_freq_m)

    n_payments = max(1, (period_count // payment_freq_m) - max(0, deferred_periods // payment_step))

    # taux par période de paiement (pour calculer l'annuité)
    if base == BASE_MENSUELLE_12:
        r_pay = _rate_base12(annual_rate, payment_freq_m)
    else:
        r_pay = _rate_equiv_360(annual_rate, payment_freq_m)

    payment_const = _annuity_payment(amount, r_pay, n_payments)

    current = first
    prev_date = None

    carry_interest = 0.0
    total_payment = total_interest = total_principal = 0.0
    payment_event_count = 0

    for i in range(1, n_interest + 1):
        if i <= deferred_periods:
            interest = 0.0
            payment = 0.0
            principal = 0.0
        else:
            # intérêt calculé sur solde ou capital initial (flat)
            base_balance_for_interest = amount if flat else balance

            interest = _interest_amount(
                balance=base_balance_for_interest,
                annual_rate=annual_rate,
                base=base,
                period_index=i,
                current_date=current,
                prev_date=prev_date,
                disbursement_date=disb,
                frequency_months=interest_freq_m,
            )

            is_payment_event = (i % payment_step == 0)

            if is_payment_event:
                payment_event_count += 1

                interest_total = interest + carry_interest
                carry_interest = 0.0

                payment = payment_const

                # si annuité < intérêts -> principal nul, carry
                if payment < interest_total:
                    carry_interest = interest_total - payment
                    principal = 0.0
                else:
                    principal = payment - interest_total

                # dernier paiement : fermeture
                if payment_event_count == n_payments:
                    payment = balance + interest_total
                    principal = balance

            else:
                # pas de paiement => on accumule intérêts
                carry_interest += interest
                payment = 0.0
                principal = 0.0

        balance = max(0.0, balance - principal)

        rows.append(ScheduleRow(i, current, payment, interest, principal, balance))
        total_payment += payment
        total_interest += interest
        total_principal += principal

        prev_date = current
        current = _add_months(current, interest_freq_m)

    summary = {
        "total_payment": total_payment,
        "total_interest": total_interest,
        "total_principal": total_principal,
        "payment_const": payment_const,
        "flat": float(flat),
        "fee_amount": fee_amount,
        "interest_frequency_months": float(interest_freq_m),
        "payment_frequency_months": float(payment_freq_m),
        "deferred_periods": float_toggle(deferred_periods),
    }
    summary["taeg"] = compute_taeg(disb, amount, fee_amount, rows, base)
    return rows, summary


def float_toggle(x: int) -> float:
    return float(x)
