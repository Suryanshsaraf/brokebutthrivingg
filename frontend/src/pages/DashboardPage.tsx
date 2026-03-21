import { useEffect, useState } from 'react';
import type {
  AlertItem, DashboardSummary, ExpenseEntryRead, CashflowEntryRead,
  GamificationSummary,
} from '../types/api';
import {
  getDashboard, getAlerts, listExpenses, listCashflows, getGamification,
} from '../lib/api';
import { MagicBento, BentoCard } from '../components/MagicBento/MagicBento';
import { LogoLoop } from '../components/LogoLoop/LogoLoop';
import { 
  FaReact, FaPython, FaDatabase 
} from 'react-icons/fa';
import { 
  SiFastapi, SiSqlite, SiGooglecloud, SiVite, SiTypescript 
} from 'react-icons/si';
import './DashboardPage.css';

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

  const techStack = [
    { icon: <FaReact style={{ color: '#61DAFB' }} />, text: 'React 19' },
    { icon: <SiTypescript style={{ color: '#3178C6' }} />, text: 'TypeScript' },
    { icon: <SiVite style={{ color: '#646CFF' }} />, text: 'Vite' },
    { icon: <SiFastapi style={{ color: '#05998B' }} />, text: 'FastAPI' },
    { icon: <FaPython style={{ color: '#3776AB' }} />, text: 'Python 3.12' },
    { icon: <SiSqlite style={{ color: '#003B57' }} />, text: 'SQLModel' },
    { icon: <FaDatabase style={{ color: '#336791' }} />, text: 'PostgreSQL' },
    { icon: <SiGooglecloud style={{ color: '#4285F4' }} />, text: 'Google Gemini' },
  ];

  const categories = [
    { icon: '🏠', text: 'Rent' },
    { icon: '🍔', text: 'Food' },
    { icon: '🚗', text: 'Travel' },
    { icon: '⚡', text: 'Utilities' },
    { icon: '🎮', text: 'Fun' },
    { icon: '🏥', text: 'Health' },
    { icon: '🛍️', text: 'Shopping' },
  ];

  return (
    <div className="dashboard-container">
      <div className="page-header">
        <h2>Dashboard</h2>
        <p>Your financial overview at a glance</p>
      </div>

      <MagicBento>
        {/* Row 1: Key Metrics */}
        <BentoCard title="Current Balance" span="small">
          <div className="metric-value big" style={{ color: (dashboard?.current_balance ?? 0) >= 0 ? '#5cd6a0' : '#f5695b' }}>
            ₹{dashboard?.current_balance.toFixed(0) ?? '0'}
          </div>
        </BentoCard>

        <BentoCard title="Performance" subtitle="14-Day Average & Monthly Spend" span="medium">
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 10 }}>
            <div>
              <div className="metric-value">₹{dashboard?.average_daily_spend_14d.toFixed(0) ?? '0'}</div>
              <div className="metric-subtitle">Avg Burn / Day</div>
            </div>
            <div>
              <div className="metric-value">₹{dashboard?.current_month_spend.toFixed(0) ?? '0'}</div>
              <div className="metric-subtitle">This Month</div>
            </div>
          </div>
        </BentoCard>

        <BentoCard title="Risk Score" span="small">
          <div className="metric-value">{dashboard ? Math.round(dashboard.risk_score * 100) : 0}%</div>
          {dashboard && (
            <span className={`risk-badge risk-${dashboard.risk_band}`} style={{ marginTop: 6, display: 'inline-block' }}>
              {dashboard.risk_band}
            </span>
          )}
        </BentoCard>

        <BentoCard title="Savings Potential" span="small">
          {(() => {
            const income = dashboard?.current_month_inflow || 0;
            const spend = dashboard?.current_month_spend || 0;
            const potential = Math.max(0, income - spend);
            return (
              <>
                <div className="metric-value" style={{ color: '#5cd6a0' }}>₹{potential.toFixed(0)}</div>
                <div className="metric-subtitle">Left from Income</div>
              </>
            );
          })()}
        </BentoCard>

        {/* Row 2: Visual Insights */}
        <BentoCard title="Budget Health" span="large">
          <div className="budget-ring-container bento-center">
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
                <div className="budget-ring-label">Used</div>
              </div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 13, color: 'var(--text-tertiary)' }}>
                ₹{dashboard?.budget_remaining.toFixed(0) ?? '0'} remaining
              </div>
            </div>
          </div>
        </BentoCard>

        <BentoCard title="Smart Alerts" span="tall">
          <div className="stack" style={{ gap: 12 }}>
            {alerts.length > 0 ? alerts.map((a) => (
              <div key={a.id} className={`alert-card alert-${a.severity}`} style={{ padding: '12px' }}>
                <span className="alert-icon" style={{ fontSize: '16px' }}>{a.icon}</span>
                <div className="alert-body">
                  <h4 style={{ fontSize: '13px' }}>{a.title}</h4>
                </div>
              </div>
            )) : (
              <p style={{ opacity: 0.4, fontSize: '13px' }}>No active alerts. You're doing great!</p>
            )}
          </div>
        </BentoCard>

        <BentoCard title="Category Budgets" span="tall">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {(() => {
              const savedAlloc = localStorage.getItem(`bbt_alloc_${participantId}`);
              const allocations = savedAlloc ? JSON.parse(savedAlloc) : {};
              
              // We want to show all core categories, even if spend is 0, if they have a budget
              const cats = ['food', 'travel', 'utilities', 'health', 'entertainment', 'shopping'];
              
              return cats.map((cat) => {
                const spend = dashboard?.top_categories.find(c => c.category === cat)?.total_spend || 0;
                const budget = allocations[cat] || 0;
                const pctUsed = budget > 0 ? (spend / budget) * 100 : 0;
                const barColor = pctUsed >= 100 ? '#f5695b' : pctUsed >= 80 ? '#f5a65b' : 'var(--accent-green)';

                return (
                  <div key={cat}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                      <strong style={{ textTransform: 'capitalize' }}>{cat}</strong>
                      <span style={{ opacity: 0.8 }}>
                        ₹{Math.round(spend)} / <span style={{ color: 'var(--text-tertiary)' }}>₹{Math.round(budget)}</span>
                      </span>
                    </div>
                    <div className="progress-bar-subtle">
                      <div 
                        className="progress-fill" 
                        style={{ 
                          width: `${Math.min(100, pctUsed)}%`,
                          background: barColor,
                          boxShadow: pctUsed >= 100 ? '0 0 10px rgba(245, 105, 91, 0.3)' : 'none'
                        }} 
                      />
                    </div>
                  </div>
                );
              });
            })()}
          </div>
        </BentoCard>

        {/* Row 3: Insights & Achievements */}
        <BentoCard title="AI Copilot Insights" span="medium">
          <ul className="insights-list">
            {dashboard?.highlight_messages.slice(0, 3).map((m, i) => (
              <li key={i}>{m}</li>
            ))}
          </ul>
        </BentoCard>

        <BentoCard title="Achievements" span="medium">
          {gamification && (
            <div style={{ display: 'flex', gap: 20, alignItems: 'center', height: '100%' }}>
              <div className="p-avatar big" style={{ width: 60, height: 60, fontSize: '2rem' }}>
                {gamification.no_spend_streak > 3 ? '🔥' : '🏆'}
              </div>
              <div>
                <div className="metric-value small">{gamification.no_spend_streak} Day Streak</div>
                <div className="metric-subtitle">{gamification.under_budget_days} Days Under Budget</div>
              </div>
            </div>
          )}
        </BentoCard>

        {/* Row 4: Timeline */}
        <BentoCard title="Recent Activity" span="full">
          <div className="horizontal-timeline">
            {[...expenses.slice(0, 3), ...cashflows.slice(0, 2)].map((item: any, idx) => (
              <div key={idx} className={`timeline-capsule ${'amount' in item && 'participant_id' in item ? '' : 'cashflow'}`}>
                <strong>{item.category}</strong>
                <span>₹{item.amount.toFixed(0)}</span>
              </div>
            ))}
          </div>
        </BentoCard>
      </MagicBento>

      {/* Corporate/Tech Showcase */}
      <footer className="dashboard-footer">
        <LogoLoop items={techStack} title="Built With Cutting Edge Tech" speed={30} />
        <LogoLoop items={categories} title="Support for all categories" direction="right" speed={40} />
      </footer>
    </div>
  );
}
