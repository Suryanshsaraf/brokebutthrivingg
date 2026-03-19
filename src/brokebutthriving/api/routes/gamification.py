"""Gamification routes — challenges, achievements, and streak tracking."""

from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from brokebutthriving.core.database import get_session
from brokebutthriving.models.entities import Achievement, Challenge, ChallengeStatus, Participant
from brokebutthriving.schemas.api import AchievementRead, ChallengeRead, GamificationSummary
from brokebutthriving.services.analytics import compute_no_spend_streak, compute_under_budget_days

router = APIRouter(prefix="/participants/{participant_id}/gamification", tags=["gamification"])


def _ensure_participant(session: Session, participant_id: str) -> Participant:
    participant = session.get(Participant, participant_id)
    if participant is None:
        raise HTTPException(status_code=404, detail="Participant not found")
    return participant


def _check_and_award_achievements(session: Session, participant_id: str) -> None:
    """Check if the participant qualifies for any new achievements."""
    existing = session.exec(
        select(Achievement.badge_id).where(Achievement.participant_id == participant_id)
    ).all()
    existing_set = set(existing)

    no_spend = compute_no_spend_streak(session, participant_id)
    under_budget = compute_under_budget_days(session, participant_id)

    badges = [
        ("streak_3", "3-Day Streak", "Went 3 consecutive days without spending", "🔥", no_spend >= 3),
        ("streak_7", "Week Warrior", "7 consecutive no-spend days", "⚡", no_spend >= 7),
        ("streak_14", "Frugal Fortress", "14 consecutive no-spend days", "🏰", no_spend >= 14),
        ("budget_5", "Budget Keeper", "Stayed under daily budget for 5 days", "🏆", under_budget >= 5),
        ("budget_14", "Budget Boss", "Stayed under daily budget for 14 days", "👑", under_budget >= 14),
        ("budget_30", "Budget Legend", "Under budget for 30 days straight!", "💎", under_budget >= 30),
    ]

    for badge_id, title, desc, icon, qualified in badges:
        if qualified and badge_id not in existing_set:
            session.add(Achievement(
                participant_id=participant_id,
                badge_id=badge_id,
                title=title,
                description=desc,
                icon=icon,
            ))

    session.commit()


@router.get("", response_model=GamificationSummary)
def get_gamification_summary(
    participant_id: str, session: Session = Depends(get_session)
) -> GamificationSummary:
    _ensure_participant(session, participant_id)
    _check_and_award_achievements(session, participant_id)

    challenges = session.exec(
        select(Challenge)
        .where(Challenge.participant_id == participant_id)
        .where(Challenge.status == ChallengeStatus.ACTIVE)
    ).all()

    achievements = session.exec(
        select(Achievement)
        .where(Achievement.participant_id == participant_id)
        .order_by(Achievement.earned_at.desc())
    ).all()

    no_spend = compute_no_spend_streak(session, participant_id)
    under_budget = compute_under_budget_days(session, participant_id)

    challenge_reads = [
        ChallengeRead(
            id=c.id,
            participant_id=c.participant_id,
            title=c.title,
            description=c.description,
            challenge_type=c.challenge_type,
            target_value=c.target_value,
            current_value=c.current_value,
            progress_pct=round((c.current_value / c.target_value * 100) if c.target_value > 0 else 0, 1),
            status=c.status,
            start_date=c.start_date,
            end_date=c.end_date,
        )
        for c in challenges
    ]

    achievement_reads = [
        AchievementRead(
            id=a.id,
            badge_id=a.badge_id,
            title=a.title,
            description=a.description,
            icon=a.icon,
            earned_at=a.earned_at,
        )
        for a in achievements
    ]

    return GamificationSummary(
        active_challenges=challenge_reads,
        achievements=achievement_reads,
        no_spend_streak=no_spend,
        under_budget_days=under_budget,
    )


@router.post("/challenges", response_model=ChallengeRead, status_code=201)
def create_challenge(
    participant_id: str,
    session: Session = Depends(get_session),
) -> ChallengeRead:
    """Create a default no-spend challenge for the participant."""
    _ensure_participant(session, participant_id)

    challenge = Challenge(
        participant_id=participant_id,
        title="No-Spend Weekend",
        description="Go the entire weekend without any non-essential spending",
        challenge_type="no_spend",
        target_value=2,
        current_value=0,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=7),
    )
    session.add(challenge)
    session.commit()
    session.refresh(challenge)

    return ChallengeRead(
        id=challenge.id,
        participant_id=challenge.participant_id,
        title=challenge.title,
        description=challenge.description,
        challenge_type=challenge.challenge_type,
        target_value=challenge.target_value,
        current_value=challenge.current_value,
        progress_pct=0,
        status=challenge.status,
        start_date=challenge.start_date,
        end_date=challenge.end_date,
    )
