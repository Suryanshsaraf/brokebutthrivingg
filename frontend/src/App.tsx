import { useCallback, useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'
import { api } from './lib/api'
import type {
  CashflowEntry,
  DashboardSummary,
  ExpenseEntry,
  Participant,
  SimulationResponse,
} from './types/api'

const expenseCategories = [
  'food',
  'transport',
  'entertainment',
  'shopping',
  'education',
  'health',
  'utilities',
  'subscription',
  'travel',
  'other',
]

const cashflowCategories = [
  'allowance',
  'salary',
  'freelance',
  'scholarship',
  'refund',
  'transfer',
  'other',
]

const livingSituations = ['hostel', 'pg', 'with_family', 'rental', 'other']
const dietaryPreferences = ['veg', 'non_veg', 'eggetarian', 'vegan', 'other']

function App() {
  const [participants, setParticipants] = useState<Participant[]>([])
  const [selectedParticipantId, setSelectedParticipantId] = useState<string>('')
  const [dashboard, setDashboard] = useState<DashboardSummary | null>(null)
  const [expenses, setExpenses] = useState<ExpenseEntry[]>([])
  const [cashflows, setCashflows] = useState<CashflowEntry[]>([])
  const [simulation, setSimulation] = useState<SimulationResponse | null>(null)
  const [status, setStatus] = useState<string>('Bootstrapping project workspace...')
  const [loading, setLoading] = useState<boolean>(false)

  const [participantForm, setParticipantForm] = useState({
    participant_code: '',
    first_name: '',
    age: '20',
    institution: '',
    course_name: '',
    country: 'India',
    timezone: 'Asia/Kolkata',
    living_situation: 'hostel',
    dietary_preference: 'veg',
    monthly_budget: '12000',
    monthly_income: '0',
    starting_balance: '4000',
  })

  const [surveyForm, setSurveyForm] = useState({
    stress_spending_score: '3',
    social_pressure_score: '3',
    boredom_spending_score: '3',
    planning_confidence_score: '3',
    self_described_trigger: '',
  })

  const [expenseForm, setExpenseForm] = useState({
    occurred_at: new Date().toISOString().slice(0, 16),
    amount: '',
    category: 'food',
    merchant: '',
    note: '',
    is_social: false,
    is_essential: false,
    payment_mode: 'upi',
  })

  const [cashflowForm, setCashflowForm] = useState({
    occurred_at: new Date().toISOString().slice(0, 16),
    amount: '',
    category: 'allowance',
    note: '',
  })

  const [checkinForm, setCheckinForm] = useState({
    check_in_date: new Date().toISOString().slice(0, 10),
    opening_balance: '',
    closing_balance: '',
    stress_level: '3',
    exam_pressure: '2',
    social_pressure: '2',
    mood_energy: '3',
    sleep_hours: '7',
    notes: '',
  })

  const [simulationForm, setSimulationForm] = useState({
    lookback_days: '21',
    horizon_days: '14',
    food_change: '-0.15',
    entertainment_change: '-0.2',
    shopping_change: '0',
    additional_income: '0',
  })

  const selectedParticipant = useMemo(
    () => participants.find((participant) => participant.id === selectedParticipantId) ?? null,
    [participants, selectedParticipantId],
  )

  const refreshParticipants = useCallback(async () => {
    setLoading(true)
    try {
      const items = await api.listParticipants()
      setParticipants(items)
      setSelectedParticipantId((current) => current || items[0]?.id || '')
      setStatus(
        items.length > 0
          ? `Loaded ${items.length} participant workspace${items.length > 1 ? 's' : ''}.`
          : 'No participants yet. Create the first profile to begin collecting real data.',
      )
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Could not reach the backend API.')
    } finally {
      setLoading(false)
    }
  }, [])

  const refreshParticipantWorkspace = useCallback(async (participantId: string) => {
    setLoading(true)
    try {
      const [dashboardPayload, expensePayload, cashflowPayload] = await Promise.all([
        api.getDashboard(participantId),
        api.listExpenses(participantId),
        api.listCashflows(participantId),
      ])
      setDashboard(dashboardPayload)
      setExpenses(expensePayload.slice(0, 6))
      setCashflows(cashflowPayload.slice(0, 4))
      setStatus('Participant workspace refreshed from live database records.')
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Unable to load participant workspace.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refreshParticipants()
  }, [refreshParticipants])

  useEffect(() => {
    if (!selectedParticipantId) {
      return
    }
    void refreshParticipantWorkspace(selectedParticipantId)
  }, [refreshParticipantWorkspace, selectedParticipantId])

  async function handleCreateParticipant(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    try {
      const created = await api.createParticipant({
        ...participantForm,
        age: participantForm.age ? Number(participantForm.age) : null,
        monthly_budget: Number(participantForm.monthly_budget),
        monthly_income: Number(participantForm.monthly_income),
        starting_balance: Number(participantForm.starting_balance),
      })
      setParticipants((current) => [created, ...current])
      setSelectedParticipantId(created.id)
      setStatus(`Participant ${created.participant_code} created. You can start logging real data now.`)
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Could not create participant.')
    } finally {
      setLoading(false)
    }
  }

  async function handleSubmitSurvey(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedParticipantId) {
      setStatus('Create or select a participant before saving the behavioral survey.')
      return
    }

    setLoading(true)
    try {
      await api.submitSurvey(selectedParticipantId, {
        ...surveyForm,
        stress_spending_score: Number(surveyForm.stress_spending_score),
        social_pressure_score: Number(surveyForm.social_pressure_score),
        boredom_spending_score: Number(surveyForm.boredom_spending_score),
        planning_confidence_score: Number(surveyForm.planning_confidence_score),
      })
      setStatus('Behavior survey saved. This unlocks archetype supervision for model training.')
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Could not save survey.')
    } finally {
      setLoading(false)
    }
  }

  async function handleSubmitExpense(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedParticipantId) {
      setStatus('Create or select a participant before logging expenses.')
      return
    }

    setLoading(true)
    try {
      await api.createExpense(selectedParticipantId, {
        ...expenseForm,
        amount: Number(expenseForm.amount),
      })
      setExpenseForm((current) => ({
        ...current,
        amount: '',
        merchant: '',
        note: '',
      }))
      await refreshParticipantWorkspace(selectedParticipantId)
      setStatus('Expense saved to the real dataset.')
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Could not log the expense.')
    } finally {
      setLoading(false)
    }
  }

  async function handleSubmitCashflow(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedParticipantId) {
      setStatus('Create or select a participant before logging inflows.')
      return
    }

    setLoading(true)
    try {
      await api.createCashflow(selectedParticipantId, {
        ...cashflowForm,
        amount: Number(cashflowForm.amount),
      })
      setCashflowForm((current) => ({
        ...current,
        amount: '',
        note: '',
      }))
      await refreshParticipantWorkspace(selectedParticipantId)
      setStatus('Cash inflow saved to the dataset.')
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Could not log the cash inflow.')
    } finally {
      setLoading(false)
    }
  }

  async function handleSubmitCheckin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedParticipantId) {
      setStatus('Create or select a participant before adding a daily check-in.')
      return
    }

    setLoading(true)
    try {
      await api.createCheckin(selectedParticipantId, {
        ...checkinForm,
        opening_balance: checkinForm.opening_balance
          ? Number(checkinForm.opening_balance)
          : null,
        closing_balance: checkinForm.closing_balance
          ? Number(checkinForm.closing_balance)
          : null,
        stress_level: Number(checkinForm.stress_level),
        exam_pressure: Number(checkinForm.exam_pressure),
        social_pressure: Number(checkinForm.social_pressure),
        mood_energy: Number(checkinForm.mood_energy),
        sleep_hours: Number(checkinForm.sleep_hours),
      })
      await refreshParticipantWorkspace(selectedParticipantId)
      setStatus('Daily check-in captured. This will become part of the training signals.')
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Could not save the daily check-in.')
    } finally {
      setLoading(false)
    }
  }

  async function handleRunSimulation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedParticipantId) {
      setStatus('Create or select a participant before running what-if simulations.')
      return
    }

    setLoading(true)
    try {
      const result = await api.simulate(selectedParticipantId, {
        lookback_days: Number(simulationForm.lookback_days),
        horizon_days: Number(simulationForm.horizon_days),
        additional_income: Number(simulationForm.additional_income),
        category_adjustments: {
          food: Number(simulationForm.food_change),
          entertainment: Number(simulationForm.entertainment_change),
          shopping: Number(simulationForm.shopping_change),
        },
      })
      setSimulation(result)
      setStatus('Simulation complete. These values are derived from the participant’s real spending history.')
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Simulation failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="shell">
      <header className="hero">
        <div>
          <p className="eyebrow">Behavioral Finance Deep Learning Platform</p>
          <h1>BrokeButThriving</h1>
          <p className="hero-copy">
            Collect real student finance behavior, turn it into sequence-ready training data,
            and surface coaching-style interventions instead of static charts.
          </p>
        </div>
        <div className="hero-panel">
          <span className={`pulse pulse-${dashboard?.risk_band ?? 'stable'}`} />
          <p className="panel-label">Live Status</p>
          <strong>{loading ? 'Syncing workspace...' : status}</strong>
        </div>
      </header>

      <main className="workspace">
        <section className="column column-left">
          <article className="panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Step 1</p>
                <h2>Create Participant</h2>
              </div>
              <span className="panel-chip">Data intake</span>
            </div>
            <form className="grid-form" onSubmit={handleCreateParticipant}>
              <label>
                Participant code
                <input
                  value={participantForm.participant_code}
                  onChange={(event) =>
                    setParticipantForm((current) => ({
                      ...current,
                      participant_code: event.target.value,
                    }))
                  }
                  placeholder="bt-riya-001"
                  required
                />
              </label>
              <label>
                First name
                <input
                  value={participantForm.first_name}
                  onChange={(event) =>
                    setParticipantForm((current) => ({
                      ...current,
                      first_name: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                Age
                <input
                  type="number"
                  value={participantForm.age}
                  onChange={(event) =>
                    setParticipantForm((current) => ({
                      ...current,
                      age: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                Institution
                <input
                  value={participantForm.institution}
                  onChange={(event) =>
                    setParticipantForm((current) => ({
                      ...current,
                      institution: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                Course
                <input
                  value={participantForm.course_name}
                  onChange={(event) =>
                    setParticipantForm((current) => ({
                      ...current,
                      course_name: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                Monthly budget
                <input
                  type="number"
                  value={participantForm.monthly_budget}
                  onChange={(event) =>
                    setParticipantForm((current) => ({
                      ...current,
                      monthly_budget: event.target.value,
                    }))
                  }
                  required
                />
              </label>
              <label>
                Monthly income
                <input
                  type="number"
                  value={participantForm.monthly_income}
                  onChange={(event) =>
                    setParticipantForm((current) => ({
                      ...current,
                      monthly_income: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                Starting balance
                <input
                  type="number"
                  value={participantForm.starting_balance}
                  onChange={(event) =>
                    setParticipantForm((current) => ({
                      ...current,
                      starting_balance: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                Living situation
                <select
                  value={participantForm.living_situation}
                  onChange={(event) =>
                    setParticipantForm((current) => ({
                      ...current,
                      living_situation: event.target.value,
                    }))
                  }
                >
                  {livingSituations.map((item) => (
                    <option key={item} value={item}>
                      {item.replace('_', ' ')}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Diet
                <select
                  value={participantForm.dietary_preference}
                  onChange={(event) =>
                    setParticipantForm((current) => ({
                      ...current,
                      dietary_preference: event.target.value,
                    }))
                  }
                >
                  {dietaryPreferences.map((item) => (
                    <option key={item} value={item}>
                      {item.replace('_', ' ')}
                    </option>
                  ))}
                </select>
              </label>
              <button className="primary-button" type="submit">
                Create participant
              </button>
            </form>
          </article>

          <article className="panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Step 2</p>
                <h2>Behavior Survey</h2>
              </div>
              <span className="panel-chip">Training labels</span>
            </div>
            <form className="grid-form compact-form" onSubmit={handleSubmitSurvey}>
              <label>
                Stress spending
                <input
                  type="range"
                  min="1"
                  max="5"
                  value={surveyForm.stress_spending_score}
                  onChange={(event) =>
                    setSurveyForm((current) => ({
                      ...current,
                      stress_spending_score: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                Social pressure spending
                <input
                  type="range"
                  min="1"
                  max="5"
                  value={surveyForm.social_pressure_score}
                  onChange={(event) =>
                    setSurveyForm((current) => ({
                      ...current,
                      social_pressure_score: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                Boredom spending
                <input
                  type="range"
                  min="1"
                  max="5"
                  value={surveyForm.boredom_spending_score}
                  onChange={(event) =>
                    setSurveyForm((current) => ({
                      ...current,
                      boredom_spending_score: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                Planning confidence
                <input
                  type="range"
                  min="1"
                  max="5"
                  value={surveyForm.planning_confidence_score}
                  onChange={(event) =>
                    setSurveyForm((current) => ({
                      ...current,
                      planning_confidence_score: event.target.value,
                    }))
                  }
                />
              </label>
              <label className="full-span">
                Main trigger
                <textarea
                  rows={3}
                  value={surveyForm.self_described_trigger}
                  onChange={(event) =>
                    setSurveyForm((current) => ({
                      ...current,
                      self_described_trigger: event.target.value,
                    }))
                  }
                  placeholder="Exams, FOMO on weekends, online food orders, late-night shopping..."
                />
              </label>
              <button className="secondary-button" type="submit">
                Save survey
              </button>
            </form>
          </article>

          <article className="panel dual-grid">
            <form className="stack-form" onSubmit={handleSubmitExpense}>
              <div className="panel-heading inline">
                <div>
                  <p className="eyebrow">Step 3</p>
                  <h2>Expense Log</h2>
                </div>
              </div>
              <label>
                When
                <input
                  type="datetime-local"
                  value={expenseForm.occurred_at}
                  onChange={(event) =>
                    setExpenseForm((current) => ({
                      ...current,
                      occurred_at: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                Amount
                <input
                  type="number"
                  value={expenseForm.amount}
                  onChange={(event) =>
                    setExpenseForm((current) => ({
                      ...current,
                      amount: event.target.value,
                    }))
                  }
                  required
                />
              </label>
              <label>
                Category
                <select
                  value={expenseForm.category}
                  onChange={(event) =>
                    setExpenseForm((current) => ({
                      ...current,
                      category: event.target.value,
                    }))
                  }
                >
                  {expenseCategories.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Merchant
                <input
                  value={expenseForm.merchant}
                  onChange={(event) =>
                    setExpenseForm((current) => ({
                      ...current,
                      merchant: event.target.value,
                    }))
                  }
                />
              </label>
              <label className="full-span">
                Note
                <textarea
                  rows={2}
                  value={expenseForm.note}
                  onChange={(event) =>
                    setExpenseForm((current) => ({
                      ...current,
                      note: event.target.value,
                    }))
                  }
                />
              </label>
              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={expenseForm.is_social}
                  onChange={(event) =>
                    setExpenseForm((current) => ({
                      ...current,
                      is_social: event.target.checked,
                    }))
                  }
                />
                Social spending
              </label>
              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={expenseForm.is_essential}
                  onChange={(event) =>
                    setExpenseForm((current) => ({
                      ...current,
                      is_essential: event.target.checked,
                    }))
                  }
                />
                Essential spend
              </label>
              <button className="primary-button" type="submit">
                Add expense
              </button>
            </form>

            <form className="stack-form" onSubmit={handleSubmitCashflow}>
              <div className="panel-heading inline">
                <div>
                  <p className="eyebrow">Step 4</p>
                  <h2>Cash Inflow</h2>
                </div>
              </div>
              <label>
                When
                <input
                  type="datetime-local"
                  value={cashflowForm.occurred_at}
                  onChange={(event) =>
                    setCashflowForm((current) => ({
                      ...current,
                      occurred_at: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                Amount
                <input
                  type="number"
                  value={cashflowForm.amount}
                  onChange={(event) =>
                    setCashflowForm((current) => ({
                      ...current,
                      amount: event.target.value,
                    }))
                  }
                  required
                />
              </label>
              <label>
                Category
                <select
                  value={cashflowForm.category}
                  onChange={(event) =>
                    setCashflowForm((current) => ({
                      ...current,
                      category: event.target.value,
                    }))
                  }
                >
                  {cashflowCategories.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </label>
              <label className="full-span">
                Note
                <textarea
                  rows={2}
                  value={cashflowForm.note}
                  onChange={(event) =>
                    setCashflowForm((current) => ({
                      ...current,
                      note: event.target.value,
                    }))
                  }
                />
              </label>
              <button className="secondary-button" type="submit">
                Add cashflow
              </button>
            </form>
          </article>

          <article className="panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Step 5</p>
                <h2>Daily Context Check-In</h2>
              </div>
              <span className="panel-chip">Behavioral signals</span>
            </div>
            <form className="grid-form compact-form" onSubmit={handleSubmitCheckin}>
              <label>
                Date
                <input
                  type="date"
                  value={checkinForm.check_in_date}
                  onChange={(event) =>
                    setCheckinForm((current) => ({
                      ...current,
                      check_in_date: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                Opening balance
                <input
                  type="number"
                  value={checkinForm.opening_balance}
                  onChange={(event) =>
                    setCheckinForm((current) => ({
                      ...current,
                      opening_balance: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                Closing balance
                <input
                  type="number"
                  value={checkinForm.closing_balance}
                  onChange={(event) =>
                    setCheckinForm((current) => ({
                      ...current,
                      closing_balance: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                Stress
                <input
                  type="number"
                  min="1"
                  max="5"
                  value={checkinForm.stress_level}
                  onChange={(event) =>
                    setCheckinForm((current) => ({
                      ...current,
                      stress_level: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                Exam pressure
                <input
                  type="number"
                  min="1"
                  max="5"
                  value={checkinForm.exam_pressure}
                  onChange={(event) =>
                    setCheckinForm((current) => ({
                      ...current,
                      exam_pressure: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                Social pressure
                <input
                  type="number"
                  min="1"
                  max="5"
                  value={checkinForm.social_pressure}
                  onChange={(event) =>
                    setCheckinForm((current) => ({
                      ...current,
                      social_pressure: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                Energy
                <input
                  type="number"
                  min="1"
                  max="5"
                  value={checkinForm.mood_energy}
                  onChange={(event) =>
                    setCheckinForm((current) => ({
                      ...current,
                      mood_energy: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                Sleep hours
                <input
                  type="number"
                  value={checkinForm.sleep_hours}
                  onChange={(event) =>
                    setCheckinForm((current) => ({
                      ...current,
                      sleep_hours: event.target.value,
                    }))
                  }
                />
              </label>
              <label className="full-span">
                Notes
                <textarea
                  rows={3}
                  value={checkinForm.notes}
                  onChange={(event) =>
                    setCheckinForm((current) => ({
                      ...current,
                      notes: event.target.value,
                    }))
                  }
                />
              </label>
              <button className="primary-button" type="submit">
                Save check-in
              </button>
            </form>
          </article>
        </section>

        <section className="column column-right">
          <article className="panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Workspace</p>
                <h2>Participant Switcher</h2>
              </div>
            </div>
            <div className="participant-list">
              {participants.map((participant) => (
                <button
                  key={participant.id}
                  className={
                    participant.id === selectedParticipantId
                      ? 'participant-button active'
                      : 'participant-button'
                  }
                  onClick={() => setSelectedParticipantId(participant.id)}
                  type="button"
                >
                  <strong>{participant.participant_code}</strong>
                  <span>
                    {participant.institution || 'Institution pending'} · Rs{' '}
                    {participant.monthly_budget.toFixed(0)}
                  </span>
                </button>
              ))}
            </div>
          </article>

          <article className="panel accent-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Live dashboard</p>
                <h2>{selectedParticipant?.first_name || selectedParticipant?.participant_code || 'No participant selected'}</h2>
              </div>
              {dashboard ? <span className="risk-pill">{dashboard.risk_band}</span> : null}
            </div>
            <div className="metric-grid">
              <div className="metric-card">
                <span>Current balance</span>
                <strong>Rs {dashboard?.current_balance.toFixed(0) ?? '0'}</strong>
              </div>
              <div className="metric-card">
                <span>14-day burn</span>
                <strong>Rs {dashboard?.average_daily_spend_14d.toFixed(0) ?? '0'}/day</strong>
              </div>
              <div className="metric-card">
                <span>Month spend</span>
                <strong>Rs {dashboard?.current_month_spend.toFixed(0) ?? '0'}</strong>
              </div>
              <div className="metric-card">
                <span>Risk score</span>
                <strong>{dashboard ? Math.round(dashboard.risk_score * 100) : 0}%</strong>
              </div>
            </div>
            <div className="insight-block">
              <h3>Current signals</h3>
              <ul>
                {dashboard?.highlight_messages.map((message) => (
                  <li key={message}>{message}</li>
                )) ?? <li>Log a few records to unlock insights.</li>}
              </ul>
            </div>
            <div className="insight-block">
              <h3>Spend mix</h3>
              <div className="bars">
                {dashboard?.top_categories.map((item) => (
                  <div key={item.category} className="bar-row">
                    <div>
                      <strong>{item.category}</strong>
                      <span>Rs {item.total_spend.toFixed(0)}</span>
                    </div>
                    <div className="bar-track">
                      <div
                        className="bar-fill"
                        style={{ width: `${Math.max(8, item.share_of_spend * 100)}%` }}
                      />
                    </div>
                  </div>
                )) ?? <p>No category data yet.</p>}
              </div>
            </div>
          </article>

          <article className="panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Decision support</p>
                <h2>What-If Simulator</h2>
              </div>
              <span className="panel-chip">Based on recent history</span>
            </div>
            <form className="grid-form compact-form" onSubmit={handleRunSimulation}>
              <label>
                Lookback days
                <input
                  type="number"
                  value={simulationForm.lookback_days}
                  onChange={(event) =>
                    setSimulationForm((current) => ({
                      ...current,
                      lookback_days: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                Horizon days
                <input
                  type="number"
                  value={simulationForm.horizon_days}
                  onChange={(event) =>
                    setSimulationForm((current) => ({
                      ...current,
                      horizon_days: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                Food adjustment
                <input
                  type="number"
                  step="0.05"
                  value={simulationForm.food_change}
                  onChange={(event) =>
                    setSimulationForm((current) => ({
                      ...current,
                      food_change: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                Entertainment adjustment
                <input
                  type="number"
                  step="0.05"
                  value={simulationForm.entertainment_change}
                  onChange={(event) =>
                    setSimulationForm((current) => ({
                      ...current,
                      entertainment_change: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                Shopping adjustment
                <input
                  type="number"
                  step="0.05"
                  value={simulationForm.shopping_change}
                  onChange={(event) =>
                    setSimulationForm((current) => ({
                      ...current,
                      shopping_change: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                Additional income
                <input
                  type="number"
                  value={simulationForm.additional_income}
                  onChange={(event) =>
                    setSimulationForm((current) => ({
                      ...current,
                      additional_income: event.target.value,
                    }))
                  }
                />
              </label>
              <button className="secondary-button" type="submit">
                Run simulation
              </button>
            </form>
            {simulation ? (
              <div className="simulation-result">
                <div className="metric-grid">
                  <div className="metric-card">
                    <span>Baseline end balance</span>
                    <strong>Rs {simulation.baseline_end_balance.toFixed(0)}</strong>
                  </div>
                  <div className="metric-card">
                    <span>Adjusted end balance</span>
                    <strong>Rs {simulation.adjusted_end_balance.toFixed(0)}</strong>
                  </div>
                  <div className="metric-card">
                    <span>Risk change</span>
                    <strong>
                      {Math.round(simulation.baseline_risk_score * 100)}% →{' '}
                      {Math.round(simulation.adjusted_risk_score * 100)}%
                    </strong>
                  </div>
                  <div className="metric-card">
                    <span>Balance delta</span>
                    <strong>Rs {simulation.balance_delta.toFixed(0)}</strong>
                  </div>
                </div>
                <ul>
                  {simulation.key_takeaways.map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </article>

          <article className="panel timeline-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Recent entries</p>
                <h2>Latest logs</h2>
              </div>
            </div>
            <div className="timeline">
              {expenses.map((item) => (
                <div key={item.id} className="timeline-item">
                  <strong>{item.category}</strong>
                  <span>
                    Rs {item.amount.toFixed(0)} · {new Date(item.occurred_at).toLocaleString()}
                  </span>
                </div>
              ))}
              {cashflows.map((item) => (
                <div key={item.id} className="timeline-item cashflow">
                  <strong>{item.category}</strong>
                  <span>
                    + Rs {item.amount.toFixed(0)} · {new Date(item.occurred_at).toLocaleString()}
                  </span>
                </div>
              ))}
              {expenses.length === 0 && cashflows.length === 0 ? (
                <p className="empty-state">No records yet. Start with the onboarding form and log the first day.</p>
              ) : null}
            </div>
          </article>
        </section>
      </main>
    </div>
  )
}

export default App
