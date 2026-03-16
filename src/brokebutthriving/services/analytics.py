from __future__ import annotations

from calendar import monthrange
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta

from sqlmodel import Session, select

from brokebutthriving.models.entities import CashflowEntry, DailyCheckIn, ExpenseEntry, Participant
from brokebutthriving.schemas.api import CategoryBreakdown, DashboardSummary, SimulationRequest, SimulationResponse


def _coerce_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _month_start(today: date) -> date:
    return today.replace(day=1)


def _latest_reported_balance(
    participant: Participant,
    expenses: list[ExpenseEntry],
    cashflows: list[CashflowEntry],
    checkins: list[DailyCheckIn],
) -> float:
    if checkins:
        latest = sorted(checkins, key=lambda item: item.check_in_date)[-1]
        if latest.closing_balance is not None:
            return latest.closing_balance

    baseline = participant.starting_balance
    expense_total = sum(item.amount for item in expenses)
    inflow_total = sum(item.amount for item in cashflows)
    return baseline + inflow_total - expense_total


def _risk_from_projection(balance: float, daily_spend: float, days_left: int) -> tuple[float, str]:
    if days_left <= 0:
        return 0.0, "stable"

    required_balance = daily_spend * days_left
    if required_balance <= 0:
        return 0.0, "stable"

    shortfall_ratio = max(0.0, (required_balance - balance) / required_balance)
    risk_score = round(min(1.0, shortfall_ratio), 3)

    if risk_score >= 0.75:
        return risk_score, "critical"
    if risk_score >= 0.45:
        return risk_score, "elevated"
    if risk_score >= 0.2:
        return risk_score, "watch"
    return risk_score, "stable"


def _project_end_balance(balance: float, average_daily_spend: float, horizon_days: int) -> float:
    return round(balance - (average_daily_spend * horizon_days), 2)


def build_dashboard(session: Session, participant_id: str) -> DashboardSummary:
    participant = session.get(Participant, participant_id)
    if participant is None:
        raise ValueError("Participant not found")

    expenses = session.exec(
        select(ExpenseEntry).where(ExpenseEntry.participant_id == participant_id)
    ).all()
    cashflows = session.exec(
        select(CashflowEntry).where(CashflowEntry.participant_id == participant_id)
    ).all()
    checkins = session.exec(
        select(DailyCheckIn).where(DailyCheckIn.participant_id == participant_id)
    ).all()

    today = date.today()
    start_of_month = _month_start(today)
    recent_cutoff = datetime.now(UTC) - timedelta(days=14)

    current_month_spend = round(
        sum(item.amount for item in expenses if _coerce_utc(item.occurred_at).date() >= start_of_month),
        2,
    )
    current_month_inflow = round(
        sum(item.amount for item in cashflows if _coerce_utc(item.occurred_at).date() >= start_of_month),
        2,
    )

    recent_expenses = [item for item in expenses if _coerce_utc(item.occurred_at) >= recent_cutoff]
    avg_daily_spend_14d = round(
        sum(item.amount for item in recent_expenses) / max(1, 14),
        2,
    )

    current_balance = round(_latest_reported_balance(participant, expenses, cashflows, checkins), 2)
    days_left = max(1, monthrange(today.year, today.month)[1] - today.day + 1)
    risk_score, risk_band = _risk_from_projection(current_balance, avg_daily_spend_14d, days_left)

    totals_by_category: dict[str, float] = defaultdict(float)
    for item in expenses:
        if _coerce_utc(item.occurred_at).date() >= start_of_month:
            totals_by_category[item.category.value] += item.amount

    ordered_categories = sorted(totals_by_category.items(), key=lambda pair: pair[1], reverse=True)
    top_categories = [
        CategoryBreakdown(
            category=category,
            total_spend=round(total, 2),
            share_of_spend=round(total / current_month_spend, 3) if current_month_spend else 0,
        )
        for category, total in ordered_categories[:4]
    ]

    projected_days_remaining = 99 if avg_daily_spend_14d == 0 else max(0, int(current_balance / avg_daily_spend_14d))

    highlights: list[str] = []
    if top_categories:
        highlights.append(
            f"{top_categories[0].category.title()} is your largest spend bucket this month at Rs {top_categories[0].total_spend:.0f}."
        )
    if risk_band in {"critical", "elevated"}:
        highlights.append(
            f"At the current burn rate, your balance may feel tight within about {projected_days_remaining} days."
        )
    if checkins:
        latest_checkin = sorted(checkins, key=lambda item: item.check_in_date)[-1]
        if latest_checkin.exam_pressure >= 4:
            highlights.append("Recent check-ins show high exam pressure, which is worth tracking against impulse spending.")
    if not highlights:
        highlights.append("Start logging a week of expenses and check-ins to unlock stronger behavior insights.")

    return DashboardSummary(
        participant_id=participant_id,
        current_balance=current_balance,
        current_month_spend=current_month_spend,
        current_month_inflow=current_month_inflow,
        average_daily_spend_14d=avg_daily_spend_14d,
        projected_days_remaining=projected_days_remaining,
        risk_score=risk_score,
        risk_band=risk_band,
        top_categories=top_categories,
        highlight_messages=highlights,
    )


def simulate_plan(session: Session, participant_id: str, request: SimulationRequest) -> SimulationResponse:
    participant = session.get(Participant, participant_id)
    if participant is None:
        raise ValueError("Participant not found")

    expenses = session.exec(
        select(ExpenseEntry).where(ExpenseEntry.participant_id == participant_id)
    ).all()
    cashflows = session.exec(
        select(CashflowEntry).where(CashflowEntry.participant_id == participant_id)
    ).all()
    checkins = session.exec(
        select(DailyCheckIn).where(DailyCheckIn.participant_id == participant_id)
    ).all()

    current_balance = _latest_reported_balance(participant, expenses, cashflows, checkins)
    cutoff = datetime.now(UTC) - timedelta(days=request.lookback_days)

    category_daily_average: dict[str, float] = defaultdict(float)
    for item in expenses:
        if _coerce_utc(item.occurred_at) >= cutoff:
            category_daily_average[item.category.value] += item.amount / request.lookback_days

    baseline_daily_spend = sum(category_daily_average.values())
    adjusted_daily_spend = baseline_daily_spend
    takeaways: list[str] = []
    for category, pct_change in request.category_adjustments.items():
        average = category_daily_average.get(category, 0)
        adjusted_daily_spend += average * pct_change
        if average:
            takeaways.append(
                f"{category.title()} adjusted by {pct_change * 100:.0f}% changes daily burn by about Rs {average * pct_change:.0f}."
            )

    adjusted_balance = current_balance + request.additional_income
    baseline_end_balance = _project_end_balance(current_balance, baseline_daily_spend, request.horizon_days)
    adjusted_end_balance = _project_end_balance(adjusted_balance, adjusted_daily_spend, request.horizon_days)

    baseline_risk, _ = _risk_from_projection(current_balance, baseline_daily_spend, request.horizon_days)
    adjusted_risk, _ = _risk_from_projection(adjusted_balance, adjusted_daily_spend, request.horizon_days)

    takeaways.append(
        f"Projected end balance moves by Rs {adjusted_end_balance - baseline_end_balance:.0f} over the next {request.horizon_days} days."
    )
    if request.additional_income:
        takeaways.append(f"An extra Rs {request.additional_income:.0f} improves cash runway immediately.")

    return SimulationResponse(
        baseline_end_balance=baseline_end_balance,
        adjusted_end_balance=adjusted_end_balance,
        balance_delta=round(adjusted_end_balance - baseline_end_balance, 2),
        baseline_risk_score=baseline_risk,
        adjusted_risk_score=adjusted_risk,
        key_takeaways=takeaways,
    )
