from __future__ import annotations

from datetime import date, datetime, timezone
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class LivingSituation(StrEnum):
    HOSTEL = "hostel"
    PG = "pg"
    WITH_FAMILY = "with_family"
    RENTAL = "rental"
    OTHER = "other"


class DietPreference(StrEnum):
    VEG = "veg"
    NON_VEG = "non_veg"
    EGGETARIAN = "eggetarian"
    VEGAN = "vegan"
    OTHER = "other"


class ExpenseCategory(StrEnum):
    FOOD = "food"
    TRANSPORT = "transport"
    ENTERTAINMENT = "entertainment"
    SHOPPING = "shopping"
    EDUCATION = "education"
    HEALTH = "health"
    UTILITIES = "utilities"
    SUBSCRIPTION = "subscription"
    TRAVEL = "travel"
    OTHER = "other"


class CashflowCategory(StrEnum):
    ALLOWANCE = "allowance"
    SALARY = "salary"
    FREELANCE = "freelance"
    SCHOLARSHIP = "scholarship"
    REFUND = "refund"
    TRANSFER = "transfer"
    OTHER = "other"


class Participant(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    participant_code: str = Field(index=True, unique=True)
    first_name: str | None = Field(default=None, max_length=80)
    age: int | None = Field(default=None, ge=16, le=35)
    institution: str | None = Field(default=None, max_length=160)
    course_name: str | None = Field(default=None, max_length=120)
    country: str = Field(default="India", max_length=80)
    timezone: str = Field(default="Asia/Kolkata", max_length=80)
    living_situation: LivingSituation = Field(default=LivingSituation.HOSTEL)
    dietary_preference: DietPreference = Field(default=DietPreference.VEG)
    monthly_budget: float = Field(ge=0)
    monthly_income: float = Field(default=0, ge=0)
    starting_balance: float = Field(default=0)
    created_at: datetime = Field(default_factory=utc_now)


class BehaviorSurvey(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("participant_id", name="uq_behavior_survey_participant"),)

    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    participant_id: str = Field(foreign_key="participant.id", index=True)
    stress_spending_score: int = Field(ge=1, le=5)
    social_pressure_score: int = Field(ge=1, le=5)
    boredom_spending_score: int = Field(ge=1, le=5)
    planning_confidence_score: int = Field(ge=1, le=5)
    self_described_trigger: str | None = Field(default=None, max_length=320)
    created_at: datetime = Field(default_factory=utc_now)


class ExpenseEntry(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    participant_id: str = Field(foreign_key="participant.id", index=True)
    occurred_at: datetime = Field(index=True)
    amount: float = Field(gt=0)
    category: ExpenseCategory = Field(index=True)
    merchant: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=240)
    is_social: bool = Field(default=False)
    is_essential: bool = Field(default=False)
    payment_mode: str | None = Field(default=None, max_length=40)
    source: str = Field(default="manual", max_length=40)
    created_at: datetime = Field(default_factory=utc_now)


class CashflowEntry(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    participant_id: str = Field(foreign_key="participant.id", index=True)
    occurred_at: datetime = Field(index=True)
    amount: float = Field(gt=0)
    category: CashflowCategory = Field(default=CashflowCategory.OTHER, index=True)
    source: str = Field(default="manual", max_length=40)
    note: str | None = Field(default=None, max_length=240)
    created_at: datetime = Field(default_factory=utc_now)


class RecurrenceFrequency(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ChallengeStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"


class DailyCheckIn(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("participant_id", "check_in_date", name="uq_daily_checkin"),)

    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    participant_id: str = Field(foreign_key="participant.id", index=True)
    check_in_date: date = Field(index=True)
    opening_balance: float | None = Field(default=None)
    closing_balance: float | None = Field(default=None)
    stress_level: int = Field(ge=1, le=5)
    exam_pressure: int = Field(ge=1, le=5)
    social_pressure: int = Field(ge=1, le=5)
    mood_energy: int = Field(ge=1, le=5)
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    notes: str | None = Field(default=None, max_length=320)
    created_at: datetime = Field(default_factory=utc_now)


class RecurringEntry(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    participant_id: str = Field(foreign_key="participant.id", index=True)
    amount: float = Field(gt=0)
    category: ExpenseCategory = Field(default=ExpenseCategory.OTHER)
    merchant: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=240)
    frequency: RecurrenceFrequency = Field(default=RecurrenceFrequency.MONTHLY)
    is_expense: bool = Field(default=True)
    is_active: bool = Field(default=True)
    next_due: date = Field(index=True)
    created_at: datetime = Field(default_factory=utc_now)


class Challenge(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    participant_id: str = Field(foreign_key="participant.id", index=True)
    title: str = Field(max_length=120)
    description: str = Field(max_length=320)
    challenge_type: str = Field(max_length=40)
    target_value: float = Field(default=0)
    current_value: float = Field(default=0)
    status: ChallengeStatus = Field(default=ChallengeStatus.ACTIVE)
    start_date: date = Field(default_factory=lambda: date.today())
    end_date: date | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)


class Achievement(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("participant_id", "badge_id", name="uq_achievement_badge"),)

    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    participant_id: str = Field(foreign_key="participant.id", index=True)
    badge_id: str = Field(max_length=60, index=True)
    title: str = Field(max_length=120)
    description: str = Field(max_length=240)
    icon: str = Field(default="🏆", max_length=10)
    earned_at: datetime = Field(default_factory=utc_now)

