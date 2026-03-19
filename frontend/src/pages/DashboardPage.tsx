import { useEffect, useRef, useState } from 'react';
import type {
  AlertItem, DashboardSummary, ExpenseEntryRead, CashflowEntryRead,
  GamificationSummary,
} from '../types/api';
import {
  getDashboard, getAlerts, listExpenses, listCashflows, getGamification,
} from '../lib/api';

/* ============================================================
   Dashboard Page — budget ring, metrics, alerts, recent activity
   ============================================================ */

interface Props {
  participantId: string | null;
}

export default function DashboardPage({ participantId }: Props) {
  const [dashboard, setDashboard] = useState<DashboardSummary | null>(null);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [expenses, setExpenses] = useState<ExpenseEntryRead[]>([]);
  const [cashflows, setCashflows] = useState<CashflowEntryRead[]>([]);
  const [gamification, setGamification] = useState<GamificationSummary | null>(null);

  useEffect(() => {
    if (!participantId) return;
    getDashboard(participantId).then(setDashboard).catch(console.error);
    getAlerts(participantId).then(setAlerts).catch(console.error);
    listExpenses(participantId, 10).then(setExpenses).catch(console.error);
    listCashflows(participantId, 10).then(setCashflows).catch(console.error);
    getGamification(participantId).then(setGamification).catch(console.error);
  }, [participantId]);

  if (!participantId) {
    return (
      <div className="empty-state">
        <p className="empty-state-icon">📊</p>
        <h3>Select a participant</h3>
        <p>Choose a participant from the sidebar or create a new one in Settings.</p>
      </div>
    );
  }

  // Budget ring SVG
  const radius = 75;
  const circumference = 2 * Math.PI * radius;
  const pct = dashboard ? Math.min(dashboard.budget_used_pct, 100) : 0;
  const offset = circumference - (pct / 100) * circumference;
  const ringColor =
    pct >= 100 ? '#f5695b' :
    pct >= 80 ? '#f5a65b' :
    pct >= 60 ? '#f5d05b' : '#5cd6a0';

  return (
    <div>
      <div className="page-header">
        <h2>Dashboard</h2>
        <p>Your financial overview at a glance</p>
      </div>

      {/* Top metrics */}
      <div className="grid-4" style={{ marginBottom: 24 }}>
        <div className="metric-card">
          <div className="metric-label">Current Balance</div>
          <div className="metric-value" style={{ color: (dashboard?.current_balance ?? 0) >= 0 ? '#5cd6a0' : '#f5695b' }}>
            ₹{dashboard?.current_balance.toFixed(0) ?? '0'}
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-label">14-Day Avg Burn</div>
          <div className="metric-value">₹{dashboard?.average_daily_spend_14d.toFixed(0) ?? '0'}</div>
          <div className="metric-subtitle">per day</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Month Spend</div>
          <div className="metric-value">₹{dashboard?.current_month_spend.toFixed(0) ?? '0'}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Risk Score</div>
          <div className="metric-value">{dashboard ? Math.round(dashboard.risk_score * 100) : 0}%</div>
          {dashboard && (
            <span className={`risk-badge risk-${dashboard.risk_band}`} style={{ marginTop: 6 }}>
              {dashboard.risk_band}
            </span>
          )}
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: 24 }}>
        {/* Budget ring */}
        <div className="glass-panel" style={{ display: 'flex', justifyContent: 'center' }}>
          <div className="budget-ring-container">
            <div className="budget-ring-wrapper">
              <svg className="budget-ring-svg" width="180" height="180" viewBox="0 0 180 180">
                <circle className="budget-ring-bg" cx="90" cy="90" r={radius} />
                <circle
                  className="budget-ring-fill"
                  cx="90" cy="90" r={radius}
                  stroke={ringColor}
                  strokeDasharray={circumference}
                  strokeDashoffset={offset}
                />
              </svg>
              <div className="budget-ring-center">
                <div className="budget-ring-pct" style={{ color: ringColor }}>{pct.toFixed(0)}%</div>
                <div className="budget-ring-label">Budget used</div>
              </div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 14, color: 'var(--text-secondary)' }}>
                ₹{dashboard?.current_month_spend.toFixed(0) ?? '0'} / ₹{dashboard?.monthly_budget.toFixed(0) ?? '0'}
              </div>
              <div style={{ fontSize: 13, color: 'var(--text-tertiary)', marginTop: 4 }}>
                ₹{dashboard?.budget_remaining.toFixed(0) ?? '0'} remaining
              </div>
            </div>
          </div>
        </div>

        {/* Alerts */}
        <div className="glass-panel">
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>🔔 Smart Alerts</h3>
          <div className="stack" style={{ gap: 10 }}>
            {alerts.map((a) => (
              <div key={a.id} className={`alert-card alert-${a.severity}`}>
                <span className="alert-icon">{a.icon}</span>
                <div className="alert-body">
                  <h4>{a.title}</h4>
                  <p>{a.message}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: 24 }}>
        {/* Highlights */}
        <div className="glass-panel">
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>💡 Insights</h3>
          <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 8 }}>
            {dashboard?.highlight_messages.map((m, i) => (
              <li key={i} style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                • {m}
              </li>
            ))}
          </ul>
        </div>

        {/* Top categories */}
        <div className="glass-panel">
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>📊 Spend Mix</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {dashboard?.top_categories.map((cat) => (
              <div key={cat.category}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 4 }}>
                  <strong style={{ textTransform: 'capitalize' }}>{cat.category}</strong>
                  <span style={{ color: 'var(--text-secondary)' }}>₹{cat.total_spend.toFixed(0)}</span>
                </div>
                <div style={{ height: 6, borderRadius: 3, background: 'var(--bg-input)', overflow: 'hidden' }}>
                  <div style={{
                    height: '100%', borderRadius: 3,
                    background: 'var(--gradient-accent)',
                    width: `${Math.max(5, cat.share_of_spend * 100)}%`,
                    transition: 'width 0.8s ease',
                  }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid-2">
        {/* Gamification summary */}
        <div className="glass-panel">
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>🏆 Achievements</h3>
          {gamification && gamification.achievements.length > 0 ? (
            <div className="badge-grid">
              {gamification.achievements.map((a) => (
                <div key={a.id} className="achievement-badge">
                  <span className="badge-icon">{a.icon}</span>
                  <div className="badge-info">
                    <h4>{a.title}</h4>
                    <p>{a.description}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: 'var(--text-tertiary)', fontSize: 14 }}>
              Keep logging to earn your first badge! 🔥 {gamification ? `${gamification.no_spend_streak}-day no-spend streak` : ''}
            </p>
          )}
          {gamification && (
            <div className="grid-2" style={{ marginTop: 12, gap: 10 }}>
              <div className="metric-card" style={{ padding: 14 }}>
                <div className="metric-label" style={{ fontSize: 11 }}>No-Spend Streak</div>
                <div className="metric-value" style={{ fontSize: 22 }}>{gamification.no_spend_streak} 🔥</div>
              </div>
              <div className="metric-card" style={{ padding: 14 }}>
                <div className="metric-label" style={{ fontSize: 11 }}>Under Budget Days</div>
                <div className="metric-value" style={{ fontSize: 22 }}>{gamification.under_budget_days} 🏆</div>
              </div>
            </div>
          )}
        </div>

        {/* Recent activity */}
        <div className="glass-panel">
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>📝 Recent Activity</h3>
          <div className="stack" style={{ gap: 8 }}>
            {expenses.slice(0, 5).map((e) => (
              <div key={e.id} className="timeline-item">
                <strong>{e.category}</strong>
                <span>₹{e.amount.toFixed(0)} · {new Date(e.occurred_at).toLocaleDateString()}</span>
              </div>
            ))}
            {cashflows.slice(0, 3).map((c) => (
              <div key={c.id} className="timeline-item cashflow-item">
                <strong>{c.category}</strong>
                <span>+₹{c.amount.toFixed(0)} · {new Date(c.occurred_at).toLocaleDateString()}</span>
              </div>
            ))}
            {expenses.length === 0 && cashflows.length === 0 && (
              <p style={{ color: 'var(--text-tertiary)', fontSize: 14 }}>No records yet. Start logging!</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
