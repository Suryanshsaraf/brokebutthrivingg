export interface Participant {
  id: string
  participant_code: string
  first_name: string | null
  age: number | null
  institution: string | null
  course_name: string | null
  country: string
  timezone: string
  living_situation: string
  dietary_preference: string
  monthly_budget: number
  monthly_income: number
  starting_balance: number
  created_at: string
}

export interface CategoryBreakdown {
  category: string
  total_spend: number
  share_of_spend: number
}

export interface DashboardSummary {
  participant_id: string
  current_balance: number
  current_month_spend: number
  current_month_inflow: number
  average_daily_spend_14d: number
  projected_days_remaining: number
  risk_score: number
  risk_band: string
  top_categories: CategoryBreakdown[]
  highlight_messages: string[]
}

export interface ExpenseEntry {
  id: string
  participant_id: string
  occurred_at: string
  amount: number
  category: string
  merchant: string | null
  note: string | null
  is_social: boolean
  is_essential: boolean
  payment_mode: string | null
  source: string
  created_at: string
}

export interface CashflowEntry {
  id: string
  participant_id: string
  occurred_at: string
  amount: number
  category: string
  source: string
  note: string | null
  created_at: string
}

export interface SimulationResponse {
  baseline_end_balance: number
  adjusted_end_balance: number
  balance_delta: number
  baseline_risk_score: number
  adjusted_risk_score: number
  key_takeaways: string[]
}

export interface ModelMetricSummary {
  model_id: string
  model_label: string
  primary_metric_name: string
  primary_metric_value: number
  metrics: Record<string, number>
  is_best: boolean
}

export interface ModelFeatureGroup {
  name: string
  features: string[]
}

export interface SubgroupEvaluationSummary {
  label: string
  row_count: number
  group_count: number
  best_model: string | null
  primary_metric_name: string | null
  primary_metric_value: number | null
}

export interface TrainedModelTask {
  task_id: string
  title: string
  family: string
  task_type: string
  benchmark_file: string | null
  run_id: string
  note: string
  dataset_sources: string[]
  row_count: number
  split_counts: Record<string, number>
  feature_count: number
  auxiliary_feature_count: number | null
  auxiliary_feature_label: string | null
  positive_class_rate: number | null
  best_model: string
  primary_metric_name: string
  primary_metric_value: number
  highlight: string
  feature_summary: string
  feature_groups: ModelFeatureGroup[]
  metrics: ModelMetricSummary[]
  subgroup_evaluation: SubgroupEvaluationSummary | null
}

export interface ModelRegistrySummary {
  public_benchmark_run_id: string | null
  sequence_run_id: string | null
  total_trained_tasks: number
  available_families: string[]
  note: string
  missing_artifacts: string[]
  tasks: TrainedModelTask[]
}
