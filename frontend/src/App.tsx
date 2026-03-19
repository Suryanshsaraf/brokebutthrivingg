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
import Dock from './components/Dock/Dock';
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
  const [showParticipantOverlay, setShowParticipantOverlay] = useState(false);

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

      {/* Main content */}
      <main className="main-content">
        {page === 'dashboard' && <DashboardPage participantId={selectedId} />}
        {page === 'log' && <LogPage participantId={selectedId} />}
        {page === 'insights' && <InsightsPage participantId={selectedId} />}
        {page === 'chat' && <ChatPage participantId={selectedId} />}
        {page === 'settings' && <SettingsPage participantId={selectedId} />}
      </main>

      {/* Floating Dock */}
      <Dock 
        items={NAV_ITEMS} 
        activeId={page} 
        onSelect={(id) => setPage(id)} 
        onParticipantClick={() => setShowParticipantOverlay(!showParticipantOverlay)}
      />

      {/* Participant Switcher Overlay */}
      {showParticipantOverlay && (
        <div className="participant-overlay" onClick={() => setShowParticipantOverlay(false)}>
          <div className="participant-card" onClick={(e) => e.stopPropagation()}>
            <h3>Switch Participant</h3>
            <div className="participant-list">
              {participants.map((p) => (
                <button
                  key={p.id}
                  className={`participant-item ${selectedId === p.id ? 'active' : ''}`}
                  onClick={() => {
                    handleSelectParticipant(p.id);
                    setShowParticipantOverlay(false);
                  }}
                >
                  <div className="p-avatar">{p.first_name?.[0] || '👤'}</div>
                  <div className="p-info">
                    <span className="p-name">{p.first_name || p.participant_code}</span>
                    <span className="p-budget">Budget: ₹{p.monthly_budget}</span>
                  </div>
                </button>
              ))}
            </div>
            <button
              className="btn btn-secondary"
              style={{ marginTop: 16, width: '100%' }}
              onClick={() => {
                setShowOnboarding(true);
                setShowParticipantOverlay(false);
              }}
            >
              + New Participant
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
