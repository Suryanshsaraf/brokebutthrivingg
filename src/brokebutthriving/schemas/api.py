from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from brokebutthriving.models.entities import (
    CashflowCategory,
    DietPreference,
    ExpenseCategory,
    LivingSituation,
)


class ParticipantCreate(BaseModel):
    participant_code: str = Field(min_length=3, max_length=32)
    first_name: str | None = Field(default=None, max_length=80)
    age: int | None = Field(default=None, ge=16, le=35)
    institution: str | None = Field(default=None, max_length=160)
    course_name: str | None = Field(default=None, max_length=120)
    country: str = Field(default="India", max_length=80)
    timezone: str = Field(default="Asia/Kolkata", max_length=80)
    living_situation: LivingSituation = LivingSituation.HOSTEL
    dietary_preference: DietPreference = DietPreference.VEG
    monthly_budget: float = Field(ge=0)
    monthly_income: float = Field(default=0, ge=0)
    starting_balance: float = Field(default=0)


class ParticipantRead(ParticipantCreate):
    id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BehaviorSurveyCreate(BaseModel):
    stress_spending_score: int = Field(ge=1, le=5)
    social_pressure_score: int = Field(ge=1, le=5)
    boredom_spending_score: int = Field(ge=1, le=5)
    planning_confidence_score: int = Field(ge=1, le=5)
    self_described_trigger: str | None = Field(default=None, max_length=320)


class BehaviorSurveyRead(BehaviorSurveyCreate):
    id: str
    participant_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExpenseEntryCreate(BaseModel):
    occurred_at: datetime
    amount: float = Field(gt=0)
    category: ExpenseCategory
    merchant: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=240)
    is_social: bool = False
    is_essential: bool = False
    payment_mode: str | None = Field(default=None, max_length=40)
    source: str = Field(default="manual", max_length=40)


class ExpenseEntryRead(ExpenseEntryCreate):
    id: str
    participant_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExpenseBatchCreate(BaseModel):
    expenses: list[ExpenseEntryCreate]


class CashflowEntryCreate(BaseModel):
    occurred_at: datetime
    amount: float = Field(gt=0)
    category: CashflowCategory = CashflowCategory.OTHER
    source: str = Field(default="manual", max_length=40)
    note: str | None = Field(default=None, max_length=240)


class CashflowEntryRead(CashflowEntryCreate):
    id: str
    participant_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DailyCheckInCreate(BaseModel):
    check_in_date: date
    opening_balance: float | None = None
    closing_balance: float | None = None
    stress_level: int = Field(ge=1, le=5)
    exam_pressure: int = Field(ge=1, le=5)
    social_pressure: int = Field(ge=1, le=5)
    mood_energy: int = Field(ge=1, le=5)
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    notes: str | None = Field(default=None, max_length=320)


class DailyCheckInRead(DailyCheckInCreate):
    id: str
    participant_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CategoryBreakdown(BaseModel):
    category: str
    total_spend: float
    share_of_spend: float


class DashboardSummary(BaseModel):
    participant_id: str
    current_balance: float
    current_month_spend: float
    current_month_inflow: float
    average_daily_spend_14d: float
    projected_days_remaining: int
    risk_score: float
    risk_band: str
    top_categories: list[CategoryBreakdown]
    highlight_messages: list[str]


class SimulationRequest(BaseModel):
    lookback_days: int = Field(default=21, ge=7, le=90)
    horizon_days: int = Field(default=14, ge=7, le=45)
    category_adjustments: dict[str, float] = Field(
        default_factory=dict,
        description="Percentage adjustments per category, such as {'food': -0.2}.",
    )
    additional_income: float = 0


class SimulationResponse(BaseModel):
    baseline_end_balance: float
    adjusted_end_balance: float
    balance_delta: float
    baseline_risk_score: float
    adjusted_risk_score: float
    key_takeaways: list[str]


class DailyDatasetRecord(BaseModel):
    participant_id: str
    date: date
    spend_total: float
    inflow_total: float
    estimated_balance: float
    risk_label_14d: int
    spend_next_7d: float
    primary_archetype: str | None


class ModelMetricSummary(BaseModel):
    model_id: str
    model_label: str
    primary_metric_name: str
    primary_metric_value: float
    metrics: dict[str, float]
    is_best: bool = False


class ModelFeatureGroup(BaseModel):
    name: str
    features: list[str]


class SubgroupEvaluationSummary(BaseModel):
    label: str
    row_count: int
    group_count: int
    best_model: str | None = None
    primary_metric_name: str | None = None
    primary_metric_value: float | None = None


class TrainedModelTask(BaseModel):
    task_id: str
    title: str
    family: str
    task_type: str
    benchmark_file: str | None = None
    run_id: str
    note: str
    dataset_sources: list[str]
    row_count: int
    split_counts: dict[str, int]
    feature_count: int
    auxiliary_feature_count: int | None = None
    auxiliary_feature_label: str | None = None
    positive_class_rate: float | None = None
    best_model: str
    primary_metric_name: str
    primary_metric_value: float
    highlight: str
    feature_summary: str
    feature_groups: list[ModelFeatureGroup]
    metrics: list[ModelMetricSummary]
    subgroup_evaluation: SubgroupEvaluationSummary | None = None


class ModelRegistrySummary(BaseModel):
    public_benchmark_run_id: str | None = None
    sequence_run_id: str | None = None
    total_trained_tasks: int
    available_families: list[str]
    note: str
    missing_artifacts: list[str]
    tasks: list[TrainedModelTask]
