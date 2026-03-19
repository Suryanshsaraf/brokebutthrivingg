from __future__ import annotations

from calendar import monthrange
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from sqlmodel import Session, func, select

from brokebutthriving.models.entities import CashflowEntry, DailyCheckIn, ExpenseEntry, Participant
from brokebutthriving.schemas.api import (
    AlertItem,
    CategoryBreakdown,
    DailySpendPoint,
    DashboardSummary,
    MoodReading,
    MoodSpendingResponse,
    PeerComparisonItem,
    PeerComparisonResponse,
    SemesterProjectionPoint,
    SemesterProjectionResponse,
    SimulationRequest,
    SimulationResponse,
    SpendingTrendsResponse,
)


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

    # Budget tracking
    monthly_budget = participant.monthly_budget
    budget_used_pct = round((current_month_spend / monthly_budget) * 100, 1) if monthly_budget > 0 else 0
    budget_remaining = round(monthly_budget - current_month_spend, 2)
    if budget_used_pct >= 100:
        budget_status = "over_budget"
    elif budget_used_pct >= 80:
        budget_status = "warning"
    elif budget_used_pct >= 60:
        budget_status = "caution"
    else:
        budget_status = "on_track"

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
        monthly_budget=monthly_budget,
        budget_used_pct=budget_used_pct,
        budget_remaining=budget_remaining,
        budget_status=budget_status,
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


# ---------------------------------------------------------------------------
# Smart Alerts
# ---------------------------------------------------------------------------

def generate_alerts(session: Session, participant_id: str) -> list[AlertItem]:
    """Rule-based alert engine generating actionable notifications."""
    participant = session.get(Participant, participant_id)
    if participant is None:
        raise ValueError("Participant not found")

    dashboard = build_dashboard(session, participant_id)
    alerts: list[AlertItem] = []

    # Budget alerts
    if dashboard.budget_used_pct >= 100:
        alerts.append(AlertItem(
            id=uuid4().hex[:8], severity="critical", icon="🔴",
            title="Over budget!",
            message=f"You've spent Rs {dashboard.current_month_spend:.0f} against Rs {dashboard.monthly_budget:.0f} budget. Time to cut non-essentials.",
        ))
    elif dashboard.budget_used_pct >= 80:
        alerts.append(AlertItem(
            id=uuid4().hex[:8], severity="warning", icon="🟡",
            title="Budget almost used up",
            message=f"{dashboard.budget_used_pct:.0f}% of your budget is used with {dashboard.projected_days_remaining} days left this month.",
        ))

    # Risk alerts
    if dashboard.risk_band == "critical":
        alerts.append(AlertItem(
            id=uuid4().hex[:8], severity="critical", icon="🚨",
            title="High financial risk",
            message="At your current burn rate, funds may run out before the month ends. Consider reducing discretionary spending.",
        ))
    elif dashboard.risk_band == "elevated":
        alerts.append(AlertItem(
            id=uuid4().hex[:8], severity="warning", icon="⚠️",
            title="Elevated risk level",
            message="Your spending pace is higher than your runway can comfortably support.",
        ))

    # Category spikes — compare last 7 days vs prior 7 days
    now = datetime.now(UTC)
    cutoff_7 = now - timedelta(days=7)
    cutoff_14 = now - timedelta(days=14)
    expenses = session.exec(
        select(ExpenseEntry)
        .where(ExpenseEntry.participant_id == participant_id)
        .where(ExpenseEntry.occurred_at >= cutoff_14)
    ).all()

    recent_totals: dict[str, float] = defaultdict(float)
    prior_totals: dict[str, float] = defaultdict(float)
    for item in expenses:
        dt = _coerce_utc(item.occurred_at)
        if dt >= cutoff_7:
            recent_totals[item.category.value] += item.amount
        else:
            prior_totals[item.category.value] += item.amount

    for cat, recent_val in recent_totals.items():
        prior_val = prior_totals.get(cat, 0)
        if prior_val > 0 and recent_val > prior_val * 1.4:
            pct_increase = int(((recent_val - prior_val) / prior_val) * 100)
            alerts.append(AlertItem(
                id=uuid4().hex[:8], severity="info", icon="📈",
                title=f"{cat.title()} spending up {pct_increase}%",
                message=f"Your {cat} spending this week (Rs {recent_val:.0f}) is {pct_increase}% higher than last week (Rs {prior_val:.0f}).",
            ))

    # Positive alerts
    streak = compute_no_spend_streak(session, participant_id)
    if streak >= 3:
        alerts.append(AlertItem(
            id=uuid4().hex[:8], severity="success", icon="🔥",
            title=f"{streak}-day no-spend streak!",
            message=f"Amazing! You've gone {streak} days without spending. Keep it up!",
        ))

    under_budget = compute_under_budget_days(session, participant_id)
    if under_budget >= 5:
        alerts.append(AlertItem(
            id=uuid4().hex[:8], severity="success", icon="🏆",
            title=f"Under budget for {under_budget} days",
            message=f"Great discipline! You've stayed under your daily target for {under_budget} consecutive days.",
        ))

    if not alerts:
        alerts.append(AlertItem(
            id=uuid4().hex[:8], severity="info", icon="✨",
            title="All looks good",
            message="No alerts right now. Keep logging to stay on track!",
        ))

    return alerts


# ---------------------------------------------------------------------------
# Spending trends
# ---------------------------------------------------------------------------

def get_spending_trends(session: Session, participant_id: str, days: int = 30) -> SpendingTrendsResponse:
    """Aggregated spending data for charts."""
    participant = session.get(Participant, participant_id)
    if participant is None:
        raise ValueError("Participant not found")

    cutoff = datetime.now(UTC) - timedelta(days=days)
    expenses = session.exec(
        select(ExpenseEntry)
        .where(ExpenseEntry.participant_id == participant_id)
        .where(ExpenseEntry.occurred_at >= cutoff)
    ).all()
    cashflows = session.exec(
        select(CashflowEntry)
        .where(CashflowEntry.participant_id == participant_id)
        .where(CashflowEntry.occurred_at >= cutoff)
    ).all()

    # Daily spend
    daily: dict[str, float] = defaultdict(float)
    for item in expenses:
        day_str = _coerce_utc(item.occurred_at).date().isoformat()
        daily[day_str] += item.amount

    today = date.today()
    daily_spend: list[DailySpendPoint] = []
    for i in range(days):
        d = (today - timedelta(days=days - 1 - i)).isoformat()
        daily_spend.append(DailySpendPoint(date=d, amount=round(daily.get(d, 0), 2)))

    # Weekly totals
    weekly: dict[str, float] = defaultdict(float)
    for item in expenses:
        dt = _coerce_utc(item.occurred_at).date()
        week_start = (dt - timedelta(days=dt.weekday())).isoformat()
        weekly[week_start] += item.amount

    weekly_totals = [DailySpendPoint(date=k, amount=round(v, 2)) for k, v in sorted(weekly.items())]

    # Category totals
    cat_totals: dict[str, float] = defaultdict(float)
    for item in expenses:
        cat_totals[item.category.value] += item.amount
    grand = sum(cat_totals.values())
    category_totals = [
        CategoryBreakdown(
            category=cat,
            total_spend=round(total, 2),
            share_of_spend=round(total / grand, 3) if grand else 0,
        )
        for cat, total in sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)
    ]

    # Income vs expense by week
    weekly_income: dict[str, float] = defaultdict(float)
    for item in cashflows:
        dt = _coerce_utc(item.occurred_at).date()
        week_start = (dt - timedelta(days=dt.weekday())).isoformat()
        weekly_income[week_start] += item.amount

    all_weeks = sorted(set(list(weekly.keys()) + list(weekly_income.keys())))
    income_vs_expense = [
        {"week": w, "income": round(weekly_income.get(w, 0), 2), "expense": round(weekly.get(w, 0), 2)}
        for w in all_weeks
    ]

    return SpendingTrendsResponse(
        daily_spend=daily_spend,
        weekly_totals=weekly_totals,
        category_totals=category_totals,
        income_vs_expense=income_vs_expense,
    )


# ---------------------------------------------------------------------------
# Peer comparison
# ---------------------------------------------------------------------------

def get_peer_comparison(session: Session, participant_id: str) -> PeerComparisonResponse:
    """Anonymized percentile comparison across all participants."""
    participant = session.get(Participant, participant_id)
    if participant is None:
        raise ValueError("Participant not found")

    all_participants = session.exec(select(Participant)).all()
    peer_count = len(all_participants)
    if peer_count < 2:
        return PeerComparisonResponse(peer_count=peer_count, comparisons=[])

    today = date.today()
    start_of_month = _month_start(today)

    # Compute monthly spend for each participant
    user_spend = 0.0
    monthly_spends: list[float] = []
    monthly_budgets: list[float] = []
    for p in all_participants:
        expenses = session.exec(
            select(ExpenseEntry).where(ExpenseEntry.participant_id == p.id)
        ).all()
        spend = sum(
            item.amount for item in expenses
            if _coerce_utc(item.occurred_at).date() >= start_of_month
        )
        monthly_spends.append(spend)
        monthly_budgets.append(p.monthly_budget)
        if p.id == participant_id:
            user_spend = spend

    user_budget = participant.monthly_budget
    user_usage = (user_spend / user_budget * 100) if user_budget > 0 else 0
    budget_usages = [
        (s / b * 100) if b > 0 else 0
        for s, b in zip(monthly_spends, monthly_budgets)
    ]

    comparisons: list[PeerComparisonItem] = []

    # Monthly spend comparison
    avg_spend = sum(monthly_spends) / len(monthly_spends)
    spend_percentile = int(sum(1 for s in monthly_spends if s <= user_spend) / len(monthly_spends) * 100)
    diff_pct = int(((user_spend - avg_spend) / avg_spend) * 100) if avg_spend > 0 else 0
    interp = f"You spend {abs(diff_pct)}% {'more' if diff_pct > 0 else 'less'} than the average participant this month."
    comparisons.append(PeerComparisonItem(
        metric="Monthly Spend", your_value=round(user_spend, 0),
        peer_avg=round(avg_spend, 0), percentile=spend_percentile, interpretation=interp,
    ))

    # Budget usage comparison
    avg_usage = sum(budget_usages) / len(budget_usages)
    usage_percentile = int(sum(1 for u in budget_usages if u <= user_usage) / len(budget_usages) * 100)
    comparisons.append(PeerComparisonItem(
        metric="Budget Usage %", your_value=round(user_usage, 1),
        peer_avg=round(avg_usage, 1), percentile=usage_percentile,
        interpretation=f"Your budget usage is in the {_ordinal(usage_percentile)} percentile.",
    ))

    # Daily burn comparison
    cutoff_14 = datetime.now(UTC) - timedelta(days=14)
    daily_burns: list[float] = []
    user_burn = 0.0
    for p in all_participants:
        recent = session.exec(
            select(ExpenseEntry)
            .where(ExpenseEntry.participant_id == p.id)
            .where(ExpenseEntry.occurred_at >= cutoff_14)
        ).all()
        burn = sum(item.amount for item in recent) / 14
        daily_burns.append(burn)
        if p.id == participant_id:
            user_burn = burn

    avg_burn = sum(daily_burns) / len(daily_burns)
    burn_percentile = int(sum(1 for b in daily_burns if b <= user_burn) / len(daily_burns) * 100)
    comparisons.append(PeerComparisonItem(
        metric="Daily Burn Rate", your_value=round(user_burn, 0),
        peer_avg=round(avg_burn, 0), percentile=burn_percentile,
        interpretation=f"Your daily burn is in the {_ordinal(burn_percentile)} percentile among peers.",
    ))

    return PeerComparisonResponse(peer_count=peer_count, comparisons=comparisons)


def _ordinal(n: int) -> str:
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


# ---------------------------------------------------------------------------
# Semester planner
# ---------------------------------------------------------------------------

def get_semester_projection(
    session: Session, participant_id: str, months: int = 4
) -> SemesterProjectionResponse:
    """Projects balance over a multi-month horizon."""
    participant = session.get(Participant, participant_id)
    if participant is None:
        raise ValueError("Participant not found")

    dashboard = build_dashboard(session, participant_id)
    current_balance = dashboard.current_balance
    daily_spend = dashboard.average_daily_spend_14d
    monthly_burn = round(daily_spend * 30, 2)

    today = date.today()
    points: list[SemesterProjectionPoint] = []
    bal = current_balance
    for i in range(months * 30 + 1):
        d = today + timedelta(days=i)
        if i % 7 == 0:  # weekly points
            points.append(SemesterProjectionPoint(date=d.isoformat(), projected_balance=round(bal, 2)))
        bal -= daily_spend
        # Add monthly income
        if i > 0 and (today + timedelta(days=i)).day == 1:
            bal += participant.monthly_income

    projected_end_balance = round(current_balance - (monthly_burn * months) + (participant.monthly_income * months), 2)

    recommendations: list[str] = []
    if projected_end_balance < 0:
        deficit = abs(projected_end_balance)
        monthly_cut = round(deficit / months, 0)
        recommendations.append(f"At this pace you'll be Rs {deficit:.0f} short by semester end. Cutting Rs {monthly_cut:.0f}/month would close the gap.")
    if daily_spend > 0 and participant.monthly_budget > 0:
        target_daily = participant.monthly_budget / 30
        if daily_spend > target_daily * 1.1:
            recommendations.append(f"Your daily burn (Rs {daily_spend:.0f}) exceeds your budget target (Rs {target_daily:.0f}/day). Try the what-if simulator to find comfortable cuts.")
    if participant.monthly_income > 0 and monthly_burn > participant.monthly_income:
        recommendations.append(f"You're spending Rs {monthly_burn - participant.monthly_income:.0f} more per month than you earn. Consider a side gig or reducing non-essentials.")
    if not recommendations:
        recommendations.append("You're on track! Keep maintaining your current spending habits.")

    return SemesterProjectionResponse(
        current_balance=current_balance,
        projected_end_balance=projected_end_balance,
        monthly_burn=monthly_burn,
        months_remaining=months,
        projection_points=points,
        recommendations=recommendations,
    )


# ---------------------------------------------------------------------------
# Gamification helpers
# ---------------------------------------------------------------------------

def compute_no_spend_streak(session: Session, participant_id: str) -> int:
    """Count consecutive days from today with zero expenses."""
    today = date.today()
    streak = 0
    for i in range(60):
        d = today - timedelta(days=i)
        count = session.exec(
            select(func.count(ExpenseEntry.id))
            .where(ExpenseEntry.participant_id == participant_id)
            .where(func.date(ExpenseEntry.occurred_at) == d)
        ).one()
        if count == 0 and i > 0:
            streak += 1
        elif count > 0 and i > 0:
            break
    return streak


def compute_under_budget_days(session: Session, participant_id: str) -> int:
    """Count consecutive days the user spent less than budget/30."""
    participant = session.get(Participant, participant_id)
    if participant is None or participant.monthly_budget <= 0:
        return 0
    daily_target = participant.monthly_budget / 30
    today = date.today()
    streak = 0
    for i in range(1, 60):
        d = today - timedelta(days=i)
        expenses = session.exec(
            select(ExpenseEntry)
            .where(ExpenseEntry.participant_id == participant_id)
            .where(func.date(ExpenseEntry.occurred_at) == d)
        ).all()
        day_total = sum(e.amount for e in expenses)
        if day_total <= daily_target:
            streak += 1
        else:
            break
    return streak


def get_mood_spending_trends(session: Session, participant_id: str, days: int = 30) -> MoodSpendingResponse:
    """Joins check-in mood data with daily spending to identify psychological triggers."""
    _ensure_participant_exists(session, participant_id)
    
    cutoff = date.today() - timedelta(days=days)
    checkins = session.exec(
        select(DailyCheckIn)
        .where(DailyCheckIn.participant_id == participant_id)
        .where(DailyCheckIn.check_in_date >= cutoff)
        .order_by(DailyCheckIn.check_in_date)
    ).all()
    
    # Daily spending map
    daily_spend: dict[date, float] = defaultdict(float)
    expenses = session.exec(
        select(ExpenseEntry)
        .where(ExpenseEntry.participant_id == participant_id)
        .where(func.date(ExpenseEntry.occurred_at) >= cutoff)
    ).all()
    
    for e in expenses:
        d = _coerce_utc(e.occurred_at).date()
        daily_spend[d] += e.amount
        
    trends: list[MoodReading] = []
    stress_spends = []
    calm_spends = []
    
    for c in checkins:
        amt = daily_spend.get(c.check_in_date, 0)
        trends.append(MoodReading(
            date=c.check_in_date.isoformat(),
            amount=round(amt, 2),
            stress_level=c.stress_level,
            exam_pressure=c.exam_pressure,
            mood_energy=c.mood_energy
        ))
        if c.stress_level >= 4:
            stress_spends.append(amt)
        elif c.stress_level <= 2:
            calm_spends.append(amt)
            
    # Insight generation
    insight = "Keep logging check-ins and expenses to see your mood-spending patterns."
    if len(stress_spends) >= 2 and len(calm_spends) >= 2:
        avg_stress = sum(stress_spends) / len(stress_spends)
        avg_calm = sum(calm_spends) / len(calm_spends)
        if avg_stress > avg_calm * 1.5:
            diff = int(((avg_stress - avg_calm) / avg_calm) * 100)
            insight = f"You spend {diff}% more (avg ₹{avg_stress:.0f} vs ₹{avg_calm:.0f}) on high-stress days. Try deep breathing before opening your wallet!"
        elif avg_calm > avg_stress:
            insight = "Great work! You maintain disciplined spending even when stress is high."

    return MoodSpendingResponse(trends=trends, correlation_insight=insight)


def _ensure_participant_exists(session: Session, pid: str):
    if session.get(Participant, pid) is None:
        raise ValueError("Participant not found")

