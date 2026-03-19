import { useState } from 'react';
import type { ExpenseCategory, CashflowCategory, DailyCheckInCreate } from '../types/api';
import {
  createExpense, createCashflow, createCheckin, importSms,
} from '../lib/api';

/* ============================================================
   Log Page — quick expense & income entry, check-in, SMS import
   ============================================================ */

interface Props { participantId: string | null; }

const EXPENSE_CATEGORIES: ExpenseCategory[] = [
  'food', 'transport', 'entertainment', 'shopping', 'education',
  'health', 'utilities', 'subscription', 'travel', 'social', 'emergency', 'other',
];
const CASHFLOW_CATEGORIES: CashflowCategory[] = [
  'allowance', 'part_time_job', 'scholarship', 'freelance', 'refund', 'gift', 'other',
];

const EMOJIS = ['😌', '😐', '😰', '😫', '🤯'];

export default function LogPage({ participantId }: Props) {
  const [tab, setTab] = useState<'expense' | 'income' | 'checkin' | 'sms'>('expense');
  const [status, setStatus] = useState('');

  // Expense form
  const [expAmount, setExpAmount] = useState('');
  const [expCategory, setExpCategory] = useState<ExpenseCategory>('food');
  const [expMerchant, setExpMerchant] = useState('');
  const [expNote, setExpNote] = useState('');

  // Cashflow form
  const [cfAmount, setCfAmount] = useState('');
  const [cfCategory, setCfCategory] = useState<CashflowCategory>('allowance');
  const [cfNote, setCfNote] = useState('');

  // Check-in form
  const [ciDate, setCiDate] = useState(new Date().toISOString().split('T')[0]);
  const [ciOpenBal, setCiOpenBal] = useState('');
  const [ciCloseBal, setCiCloseBal] = useState('');
  const [ciStress, setCiStress] = useState(3);
  const [ciExam, setCiExam] = useState(3);
  const [ciSocial, setCiSocial] = useState(3);
  const [ciEnergy, setCiEnergy] = useState(3);
  const [ciSleep, setCiSleep] = useState('');
  const [ciNotes, setCiNotes] = useState('');

  // SMS
  const [smsText, setSmsText] = useState('');
  const [smsResult, setSmsResult] = useState<{ count: number; errors: string[] } | null>(null);

  if (!participantId) {
    return (
      <div className="empty-state">
        <p className="empty-state-icon">✏️</p>
        <h3>Select a participant first</h3>
        <p>Choose or create a participant from the sidebar.</p>
      </div>
    );
  }

  const handleExpense = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createExpense(participantId, {
        occurred_at: new Date().toISOString(),
        amount: Number(expAmount),
        category: expCategory,
        merchant: expMerchant || undefined,
        note: expNote || undefined,
      });
      setExpAmount(''); setExpMerchant(''); setExpNote('');
      setStatus('✅ Expense logged!');
      setTimeout(() => setStatus(''), 3000);
    } catch { setStatus('❌ Failed to log expense'); }
  };

  const handleCashflow = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createCashflow(participantId, {
        occurred_at: new Date().toISOString(),
        amount: Number(cfAmount),
        category: cfCategory,
        note: cfNote || undefined,
      });
      setCfAmount(''); setCfNote('');
      setStatus('✅ Income logged!');
      setTimeout(() => setStatus(''), 3000);
    } catch { setStatus('❌ Failed to log income'); }
  };

  const handleCheckin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createCheckin(participantId, {
        check_in_date: ciDate,
        opening_balance: ciOpenBal ? Number(ciOpenBal) : undefined,
        closing_balance: ciCloseBal ? Number(ciCloseBal) : undefined,
        stress_level: ciStress,
        exam_pressure: ciExam,
        social_pressure: ciSocial,
        mood_energy: ciEnergy,
        sleep_hours: ciSleep ? Number(ciSleep) : undefined,
        notes: ciNotes || undefined,
      });
      setStatus('✅ Check-in saved!');
      setTimeout(() => setStatus(''), 3000);
    } catch { setStatus('❌ Failed to save check-in'); }
  };

  const handleSms = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await importSms(participantId, smsText);
      setSmsResult({ count: res.parsed_count, errors: res.errors });
      setSmsText('');
      setStatus(`✅ Imported ${res.parsed_count} transactions`);
      setTimeout(() => setStatus(''), 3000);
    } catch { setStatus('❌ SMS import failed'); }
  };

  const StarPicker = ({ value, onChange, labels }: { value: number; onChange: (v: number) => void; labels: string[] }) => (
    <div className="star-rating">
      {[1, 2, 3, 4, 5].map((i) => (
        <button
          key={i} type="button"
          className={`star-btn ${i <= value ? 'active' : ''}`}
          onClick={() => onChange(i)}
          title={labels[i - 1] || `${i}`}
        >
          {EMOJIS[i - 1]}
        </button>
      ))}
    </div>
  );

  return (
    <div>
      <div className="page-header">
        <h2>Log Entry</h2>
        <p>Record expenses, income, or your daily check-in</p>
      </div>

      {status && (
        <div className="glass-panel" style={{ marginBottom: 16, padding: '12px 18px', textAlign: 'center', fontSize: 14 }}>
          {status}
        </div>
      )}

      {/* Tab switcher */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
        {[
          { id: 'expense' as const, label: '💸 Expense', },
          { id: 'income' as const, label: '💰 Income' },
          { id: 'checkin' as const, label: '📋 Check-in' },
          { id: 'sms' as const, label: '📱 SMS Import' },
        ].map((t) => (
          <button
            key={t.id}
            className={`btn ${tab === t.id ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setTab(t.id)}
            type="button"
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Expense tab */}
      {tab === 'expense' && (
        <div className="glass-panel">
          <h3 style={{ marginBottom: 20 }}>Log an Expense</h3>
          <form className="form-grid" onSubmit={handleExpense}>
            <div className="form-group">
              <label className="form-label">Amount (₹)</label>
              <input className="form-input" type="number" min="1" step="1" required
                value={expAmount} onChange={(e) => setExpAmount(e.target.value)}
                placeholder="Enter amount" />
            </div>
            <div className="form-group">
              <label className="form-label">Category</label>
              <select className="form-select" value={expCategory} onChange={(e) => setExpCategory(e.target.value as ExpenseCategory)}>
                {EXPENSE_CATEGORIES.map((c) => <option key={c} value={c}>{c.replace(/_/g, ' ')}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Merchant</label>
              <input className="form-input" value={expMerchant} onChange={(e) => setExpMerchant(e.target.value)}
                placeholder="e.g. Zomato, Swiggy" />
            </div>
            <div className="form-group full-width">
              <label className="form-label">Note</label>
              <textarea className="form-textarea" rows={2} value={expNote} onChange={(e) => setExpNote(e.target.value)}
                placeholder="Optional note" />
            </div>
            <div className="form-group">
              <button className="btn btn-primary" type="submit">Log Expense</button>
            </div>
          </form>
        </div>
      )}

      {/* Income tab */}
      {tab === 'income' && (
        <div className="glass-panel">
          <h3 style={{ marginBottom: 20 }}>Log Income</h3>
          <form className="form-grid" onSubmit={handleCashflow}>
            <div className="form-group">
              <label className="form-label">Amount (₹)</label>
              <input className="form-input" type="number" min="1" step="1" required
                value={cfAmount} onChange={(e) => setCfAmount(e.target.value)}
                placeholder="Enter amount" />
            </div>
            <div className="form-group">
              <label className="form-label">Category</label>
              <select className="form-select" value={cfCategory} onChange={(e) => setCfCategory(e.target.value as CashflowCategory)}>
                {CASHFLOW_CATEGORIES.map((c) => <option key={c} value={c}>{c.replace(/_/g, ' ')}</option>)}
              </select>
            </div>
            <div className="form-group full-width">
              <label className="form-label">Note</label>
              <textarea className="form-textarea" rows={2} value={cfNote} onChange={(e) => setCfNote(e.target.value)}
                placeholder="Optional note" />
            </div>
            <div className="form-group">
              <button className="btn btn-primary" type="submit">Log Income</button>
            </div>
          </form>
        </div>
      )}

      {/* Check-in tab */}
      {tab === 'checkin' && (
        <div className="glass-panel">
          <h3 style={{ marginBottom: 20 }}>Daily Check-In</h3>
          <form className="form-grid" onSubmit={handleCheckin}>
            <div className="form-group">
              <label className="form-label">Date</label>
              <input className="form-input" type="date" value={ciDate} onChange={(e) => setCiDate(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Opening Balance</label>
              <input className="form-input" type="number" value={ciOpenBal} onChange={(e) => setCiOpenBal(e.target.value)} placeholder="₹" />
            </div>
            <div className="form-group">
              <label className="form-label">Closing Balance</label>
              <input className="form-input" type="number" value={ciCloseBal} onChange={(e) => setCiCloseBal(e.target.value)} placeholder="₹" />
            </div>
            <div className="form-group">
              <label className="form-label">Sleep Hours</label>
              <input className="form-input" type="number" min="0" max="24" value={ciSleep} onChange={(e) => setCiSleep(e.target.value)} />
            </div>
            <div className="form-group full-width">
              <label className="form-label">Stress Level</label>
              <StarPicker value={ciStress} onChange={setCiStress} labels={['Calm', 'Slight', 'Moderate', 'High', 'Extreme']} />
            </div>
            <div className="form-group full-width">
              <label className="form-label">Exam Pressure</label>
              <StarPicker value={ciExam} onChange={setCiExam} labels={['None', 'Low', 'Medium', 'High', 'Critical']} />
            </div>
            <div className="form-group full-width">
              <label className="form-label">Social Pressure</label>
              <StarPicker value={ciSocial} onChange={setCiSocial} labels={['None', 'Low', 'Medium', 'High', 'Intense']} />
            </div>
            <div className="form-group full-width">
              <label className="form-label">Energy / Mood</label>
              <StarPicker value={ciEnergy} onChange={setCiEnergy} labels={['Drained', 'Low', 'Okay', 'Good', 'Great']} />
            </div>
            <div className="form-group full-width">
              <label className="form-label">Notes</label>
              <textarea className="form-textarea" rows={3} value={ciNotes} onChange={(e) => setCiNotes(e.target.value)}
                placeholder="How was your day financially?" />
            </div>
            <div className="form-group">
              <button className="btn btn-primary" type="submit">Save Check-In</button>
            </div>
          </form>
        </div>
      )}

      {/* SMS Import tab */}
      {tab === 'sms' && (
        <div className="glass-panel">
          <h3 style={{ marginBottom: 8 }}>📱 SMS Import</h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: 14, marginBottom: 20 }}>
            Paste your bank SMS messages below. We'll auto-detect debited amounts, merchants, and categorize them.
          </p>
          <form onSubmit={handleSms}>
            <div className="form-group full-width">
              <textarea
                className="form-textarea" rows={8}
                value={smsText} onChange={(e) => setSmsText(e.target.value)}
                placeholder={"Paste bank SMS messages here, one per line...\n\nExample:\nINR 250.00 debited from A/C **1234 at Zomato on 15/03/26\nRs.120 paid to UberAuto via UPI on 14/03/26"}
                required
              />
            </div>
            <button className="btn btn-primary" type="submit" style={{ marginTop: 12 }}>Import Transactions</button>
          </form>
          {smsResult && (
            <div style={{ marginTop: 16, padding: 16, borderRadius: 'var(--radius-md)', background: 'rgba(92,214,160,0.08)', border: '1px solid rgba(92,214,160,0.2)' }}>
              <strong>Imported {smsResult.count} transactions</strong>
              {smsResult.errors.length > 0 && (
                <ul style={{ marginTop: 8, color: 'var(--accent-red)', fontSize: 13 }}>
                  {smsResult.errors.map((e, i) => <li key={i}>{e}</li>)}
                </ul>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
