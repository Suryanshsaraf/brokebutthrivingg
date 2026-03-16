import type {
  CashflowEntry,
  DashboardSummary,
  ExpenseEntry,
  ModelRegistrySummary,
  Participant,
  SimulationResponse,
} from '../types/api'

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    const detail =
      payload && typeof payload.detail === 'string'
        ? payload.detail
        : 'Request failed'
    throw new Error(detail)
  }

  return response.json() as Promise<T>
}

export const api = {
  listParticipants: () => request<Participant[]>('/participants'),
  createParticipant: (payload: Record<string, unknown>) =>
    request<Participant>('/participants', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  submitSurvey: (participantId: string, payload: Record<string, unknown>) =>
    request(`/participants/${participantId}/survey`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  createExpense: (participantId: string, payload: Record<string, unknown>) =>
    request<ExpenseEntry>(`/participants/${participantId}/expenses`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  listExpenses: (participantId: string) =>
    request<ExpenseEntry[]>(`/participants/${participantId}/expenses`),
  createCashflow: (participantId: string, payload: Record<string, unknown>) =>
    request<CashflowEntry>(`/participants/${participantId}/cashflows`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  listCashflows: (participantId: string) =>
    request<CashflowEntry[]>(`/participants/${participantId}/cashflows`),
  createCheckin: (participantId: string, payload: Record<string, unknown>) =>
    request(`/participants/${participantId}/checkins`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getDashboard: (participantId: string) =>
    request<DashboardSummary>(`/participants/${participantId}/dashboard`),
  getModelRegistry: () => request<ModelRegistrySummary>('/models/registry'),
  simulate: (participantId: string, payload: Record<string, unknown>) =>
    request<SimulationResponse>(`/participants/${participantId}/simulate`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
}
