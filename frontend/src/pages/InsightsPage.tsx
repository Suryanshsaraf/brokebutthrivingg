import { useEffect, useState } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, BarChart, Bar, Legend,
} from 'recharts';
import { getSpendingTrends, getPeerComparison, getSemesterProjection, getMoodTrends } from '../lib/api';
import type { 
  SpendingTrendsResponse, PeerComparisonResponse, SemesterProjectionResponse, 
  MoodSpendingResponse 
} from '../types/api';
import { 
  ComposedChart, Scatter, 
} from 'recharts';

/* ============================================================
   Insights Page — Charts, peer comparison, semester projection
   ============================================================ */

const CHART_COLORS = ['#5b9cf5', '#a97cf8', '#f47cbe', '#5cd6a0', '#f5a65b', '#f5d05b', '#f5695b', '#4ecdc4'];

interface Props { participantId: string | null; }

export default function InsightsPage({ participantId }: Props) {
  const [trends, setTrends] = useState<SpendingTrendsResponse | null>(null);
  const [peers, setPeers] = useState<PeerComparisonResponse | null>(null);
  const [semester, setSemester] = useState<SemesterProjectionResponse | null>(null);
  const [moodData, setMoodData] = useState<MoodSpendingResponse | null>(null);
  const [tab, setTab] = useState<'trends' | 'peers' | 'semester' | 'psych'>('trends');

  useEffect(() => {
    if (!participantId) return;
    getSpendingTrends(participantId, 30).then(setTrends).catch(console.error);
    getPeerComparison(participantId).then(setPeers).catch(console.error);
    getSemesterProjection(participantId, 4).then(setSemester).catch(console.error);
    getMoodTrends(participantId, 30).then(setMoodData).catch(console.error);
  }, [participantId]);

  if (!participantId) {
    return (
      <div className="empty-state">
        <p className="empty-state-icon">📈</p>
        <h3>Select a participant</h3>
        <p>Choose a participant to see spending insights and trends.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <h2>Insights</h2>
        <p>Charts, trends, and comparative analytics</p>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
        {[
          { id: 'trends' as const, label: '📊 Spending Trends' },
          { id: 'peers' as const, label: '👥 Peer Comparison' },
          { id: 'semester' as const, label: '🎓 Semester Planner' },
          { id: 'psych' as const, label: '🧠 Psych Insights' },
        ].map((t) => (
          <button key={t.id} className={`btn ${tab === t.id ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setTab(t.id)} type="button">
            {t.label}
          </button>
        ))}
      </div>

      {/* TRENDS TAB */}
      {tab === 'trends' && trends && (
        <div className="stack">
          {/* Daily Spending Area Chart */}
          <div className="glass-panel">
            <h3 style={{ marginBottom: 16 }}>Daily Spending (Last 30 Days)</h3>
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={trends.daily_spend}>
                <defs>
                  <linearGradient id="spendGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#5b9cf5" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#5b9cf5" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} interval={4}
                  tickFormatter={(v: string) => v.slice(5)} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => `₹${v}`} />
                <Tooltip formatter={(v: number) => [`₹${v.toFixed(0)}`, 'Spend']}
                  contentStyle={{ background: 'rgba(20,20,40,0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10 }} />
                <Area type="monotone" dataKey="amount" stroke="#5b9cf5" strokeWidth={2}
                  fill="url(#spendGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="grid-2">
            {/* Category Breakdown Donut */}
            <div className="glass-panel">
              <h3 style={{ marginBottom: 16 }}>Category Breakdown</h3>
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie data={trends.category_totals} dataKey="total_spend" nameKey="category"
                    cx="50%" cy="50%" innerRadius={60} outerRadius={100}
                    paddingAngle={3} strokeWidth={0}>
                    {trends.category_totals.map((_, i) => (
                      <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => `₹${v.toFixed(0)}`}
                    contentStyle={{ background: 'rgba(20,20,40,0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10 }} />
                  <Legend formatter={(value: string) => <span style={{ color: 'var(--text-secondary)', textTransform: 'capitalize', fontSize: 12 }}>{value}</span>} />
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* Income vs Expense Bar Chart */}
            <div className="glass-panel">
              <h3 style={{ marginBottom: 16 }}>Income vs Expense (Weekly)</h3>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={trends.income_vs_expense}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="week" tick={{ fontSize: 10 }}
                    tickFormatter={(v: string) => v.slice(5)} />
                  <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => `₹${v}`} />
                  <Tooltip contentStyle={{ background: 'rgba(20,20,40,0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10 }}
                    formatter={(v: number) => `₹${v.toFixed(0)}`} />
                  <Bar dataKey="income" fill="#5cd6a0" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="expense" fill="#f5695b" radius={[4, 4, 0, 0]} />
                  <Legend formatter={(value: string) => <span style={{ color: 'var(--text-secondary)', fontSize: 12 }}>{value}</span>} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Weekly Totals */}
          <div className="glass-panel">
            <h3 style={{ marginBottom: 16 }}>Weekly Spend Totals</h3>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={trends.weekly_totals}>
                <defs>
                  <linearGradient id="weekGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#a97cf8" stopOpacity={0.9} />
                    <stop offset="100%" stopColor="#5b9cf5" stopOpacity={0.6} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={(v: string) => `W ${v.slice(5)}`} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => `₹${v}`} />
                <Tooltip formatter={(v: number) => [`₹${v.toFixed(0)}`, 'Total']}
                  contentStyle={{ background: 'rgba(20,20,40,0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10 }} />
                <Bar dataKey="amount" fill="url(#weekGrad)" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {tab === 'trends' && !trends && (
        <div className="empty-state">
          <p className="empty-state-icon">⏳</p>
          <h3>Loading trends...</h3>
        </div>
      )}

      {/* PEERS TAB */}
      {tab === 'peers' && (
        <div className="glass-panel">
          <h3 style={{ marginBottom: 20 }}>How You Compare</h3>
          {peers && peers.comparisons.length > 0 ? (
            <div>
              <p style={{ color: 'var(--text-secondary)', fontSize: 14, marginBottom: 20 }}>
                Anonymized comparison across {peers.peer_count} participants
              </p>
              {peers.comparisons.map((c) => (
                <div key={c.metric} className="peer-bar-row">
                  <div className="peer-bar-header">
                    <strong>{c.metric}</strong>
                    <span style={{ color: 'var(--text-secondary)' }}>
                      You: ₹{c.your_value.toFixed(0)} · Avg: ₹{c.peer_avg.toFixed(0)}
                    </span>
                  </div>
                  <div className="peer-bar-track" style={{ position: 'relative' }}>
                    <div className="peer-bar-fill" style={{ width: `${Math.min(100, c.percentile)}%` }} />
                    <div className="peer-bar-avg-marker" style={{
                      left: `${Math.min(100, (c.peer_avg / Math.max(c.your_value, c.peer_avg, 1)) * 50)}%`
                    }} />
                  </div>
                  <p style={{ fontSize: 13, color: 'var(--text-tertiary)', marginTop: 4 }}>{c.interpretation}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <p className="empty-state-icon">👥</p>
              <h3>Not enough peers yet</h3>
              <p>Peer comparison needs at least 2 participants with data.</p>
            </div>
          )}
        </div>
      )}

      {/* SEMESTER TAB */}
      {tab === 'semester' && semester && (
        <div className="stack">
          <div className="grid-4" style={{ marginBottom: 4 }}>
            <div className="metric-card">
              <div className="metric-label">Current Balance</div>
              <div className="metric-value">₹{semester.current_balance.toFixed(0)}</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Projected End</div>
              <div className="metric-value" style={{ color: semester.projected_end_balance >= 0 ? '#5cd6a0' : '#f5695b' }}>
                ₹{semester.projected_end_balance.toFixed(0)}
              </div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Monthly Burn</div>
              <div className="metric-value">₹{semester.monthly_burn.toFixed(0)}</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Months Left</div>
              <div className="metric-value">{semester.months_remaining}</div>
            </div>
          </div>

          <div className="glass-panel">
            <h3 style={{ marginBottom: 16 }}>Projected Balance Over Semester</h3>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={semester.projection_points}>
                <defs>
                  <linearGradient id="semGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={semester.projected_end_balance >= 0 ? '#5cd6a0' : '#f5695b'} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={semester.projected_end_balance >= 0 ? '#5cd6a0' : '#f5695b'} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} interval={3}
                  tickFormatter={(v: string) => v.slice(5)} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => `₹${v}`} />
                <Tooltip formatter={(v: number) => [`₹${v.toFixed(0)}`, 'Balance']}
                  contentStyle={{ background: 'rgba(20,20,40,0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10 }} />
                <Area type="monotone" dataKey="projected_balance"
                  stroke={semester.projected_end_balance >= 0 ? '#5cd6a0' : '#f5695b'}
                  strokeWidth={2} fill="url(#semGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="glass-panel">
            <h3 style={{ marginBottom: 12 }}>💡 Recommendations</h3>
            <div className="recommendation-list">
              {semester.recommendations.map((r, i) => (
                <div key={i} className="recommendation-item">{r}</div>
              ))}
            </div>
          </div>
        </div>
      )}

      {tab === 'psych' && <PsychTab moodData={moodData} />}
    </div>
  );
}

function PsychTab({ moodData }: { moodData: MoodSpendingResponse | null }) {
  if (!moodData) return <div className="empty-state"><h3>Loading psych data...</h3></div>;
  if (!moodData.trends.length) return (
    <div className="empty-state">
      <p className="empty-state-icon">🧠</p>
      <h3>No check-in data yet</h3>
      <p>Log your daily mood and stress in the dashboard check-in to see patterns here.</p>
    </div>
  );

  return (
    <div className="stack">
      <div className="glass-panel" style={{ borderLeft: '4px solid var(--accent-gold)' }}>
        <h3 style={{ color: 'var(--accent-gold)', marginBottom: 8 }}>🧠 AI Mood-Spending Insight</h3>
        <p style={{ fontSize: 16, lineHeight: 1.6 }}>{moodData.correlation_insight}</p>
      </div>

      <div className="glass-panel">
        <h3 style={{ marginBottom: 20 }}>Spending vs. Stress Levels</h3>
        <ResponsiveContainer width="100%" height={350}>
          <ComposedChart data={moodData.trends}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={(v) => v.slice(5)} />
            <YAxis yAxisId="left" tick={{ fontSize: 11 }} tickFormatter={(v) => `₹${v}`} />
            <YAxis yAxisId="right" orientation="right" domain={[1, 5]} tick={{ fontSize: 11 }} label={{ value: 'Stress', angle: 90, position: 'insideRight', fontSize: 12 }} />
            <Tooltip 
              contentStyle={{ background: 'rgba(20,20,40,0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10 }}
            />
            <Legend />
            <Bar yAxisId="left" dataKey="amount" name="Daily Spend" fill="var(--accent-blue)" radius={[4, 4, 0, 0]} opacity={0.7} />
            <Area yAxisId="right" type="monotone" dataKey="stress_level" name="Stress Level" stroke="var(--accent-red)" fill="rgba(245, 105, 91, 0.1)" strokeWidth={3} />
            <Scatter yAxisId="right" dataKey="exam_pressure" name="Exam Pressure" fill="var(--accent-gold)" />
          </ComposedChart>
        </ResponsiveContainer>
        <p style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 12, textAlign: 'center' }}>
          Compare how your daily spending (bars) aligns with your stress levels (line).
        </p>
      </div>

      <div className="grid-2">
        <div className="glass-panel">
          <h3 style={{ marginBottom: 16 }}>Mood & Energy</h3>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={moodData.trends}>
              <XAxis dataKey="date" hide />
              <YAxis domain={[1, 5]} />
              <Tooltip />
              <Area type="monotone" dataKey="mood_energy" name="Mood/Energy" stroke="#5cd6a0" fill="#5cd6a0" fillOpacity={0.2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div className="glass-panel">
          <h3 style={{ marginBottom: 16 }}>Check-in Consistency</h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {moodData.trends.map((t, i) => (
              <div key={i} title={t.date} style={{ 
                width: 24, height: 24, borderRadius: 4, 
                backgroundColor: t.stress_level > 3 ? 'var(--accent-red)' : 'var(--accent-green)',
                opacity: 0.2 + (t.mood_energy / 5) * 0.8
              }} />
            ))}
          </div>
          <p style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 12 }}>
            Intensity represents your energy levels on check-in days. Red indicates high stress.
          </p>
        </div>
      </div>
    </div>
  );
}
