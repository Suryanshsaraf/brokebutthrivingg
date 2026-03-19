import { useEffect, useState } from 'react';
import { listParticipants } from './lib/api';
import type { ParticipantRead } from './types/api';
import DashboardPage from './pages/DashboardPage';
import LogPage from './pages/LogPage';
import InsightsPage from './pages/InsightsPage';
import ChatPage from './pages/ChatPage';
import SettingsPage from './pages/SettingsPage';
import OnboardingPage from './pages/OnboardingPage';
import Galaxy from './components/Galaxy/Galaxy';
import './index.css';

/* ============================================================
   App — Sidebar layout with page navigation (no React Router)
   ============================================================ */

type PageId = 'dashboard' | 'log' | 'insights' | 'chat' | 'settings';

const NAV_ITEMS: { id: PageId; icon: string; label: string }[] = [
  { id: 'dashboard', icon: '📊', label: 'Dashboard' },
  { id: 'log', icon: '✏️', label: 'Log Entry' },
  { id: 'insights', icon: '📈', label: 'Insights' },
  { id: 'chat', icon: '🤖', label: 'AI Copilot' },
  { id: 'settings', icon: '⚙️', label: 'Settings' },
];

export default function App() {
  const [participants, setParticipants] = useState<ParticipantRead[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [page, setPage] = useState<PageId>('dashboard');
  const [showOnboarding, setShowOnboarding] = useState(false);

  useEffect(() => {
    listParticipants()
      .then((list) => {
        setParticipants(list);
        if (list.length > 0) {
          const saved = localStorage.getItem('bbt_pid');
          const found = list.find((p) => p.id === saved);
          setSelectedId(found ? found.id : list[0].id);
        } else {
          setShowOnboarding(true);
        }
      })
      .catch(() => setShowOnboarding(true));
  }, []);

  const handleOnboardingComplete = (id: string) => {
    localStorage.setItem('bbt_pid', id);
    setSelectedId(id);
    setShowOnboarding(false);
    listParticipants().then(setParticipants);
  };

  if (showOnboarding) {
    return (
      <>
        <div className="galaxy-background">
          <Galaxy />
        </div>
        <OnboardingPage onComplete={handleOnboardingComplete} />
      </>
    );
  }

  const handleSelectParticipant = (id: string) => {
    setSelectedId(id);
    localStorage.setItem('bbt_pid', id);
  };

  return (
    <div className="app-layout">
      <div className="galaxy-background">
        <Galaxy />
      </div>
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="sidebar-brand-icon">💰</div>
          <div>
            <h1>BrokeButThriving</h1>
            <small>Student Finance Copilot</small>
          </div>
        </div>

        <nav className="sidebar-nav">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              className={`nav-link ${page === item.id ? 'active' : ''}`}
              onClick={() => setPage(item.id)}
              type="button"
            >
              <span className="nav-icon">{item.icon}</span>
              {item.label}
            </button>
          ))}
        </nav>

        <div className="sidebar-participant">
          <label>Participant</label>
          <select
            value={selectedId ?? ''}
            onChange={(e) => handleSelectParticipant(e.target.value)}
          >
            {participants.map((p) => (
              <option key={p.id} value={p.id}>
                {p.first_name || p.participant_code} — ₹{p.monthly_budget}
              </option>
            ))}
          </select>
          <button
            className="btn btn-secondary btn-sm"
            style={{ marginTop: 10, width: '100%' }}
            onClick={() => setShowOnboarding(true)}
            type="button"
          >
            + New Participant
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="main-content">
        {page === 'dashboard' && <DashboardPage participantId={selectedId} />}
        {page === 'log' && <LogPage participantId={selectedId} />}
        {page === 'insights' && <InsightsPage participantId={selectedId} />}
        {page === 'chat' && <ChatPage participantId={selectedId} />}
        {page === 'settings' && <SettingsPage participantId={selectedId} />}
      </main>
    </div>
  );
}
