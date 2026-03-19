import { useEffect, useRef, useState } from 'react';
import type { ChatMessage } from '../types/api';
import { sendChat } from '../lib/api';

/* ============================================================
   Chat Page — full-screen AI copilot
   ============================================================ */

interface Props { participantId: string | null; }

export default function ChatPage({ participantId }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  if (!participantId) {
    return (
      <div className="empty-state">
        <p className="empty-state-icon">🤖</p>
        <h3>Select a participant first</h3>
        <p>The AI copilot needs a participant context to give personalized advice.</p>
      </div>
    );
  }

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: ChatMessage = { role: 'user', content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const history = messages.map((m) => ({ role: m.role, content: m.content }));
      const res = await sendChat(participantId, text, history);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: res.reply, tools_used: res.tools_used },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Sorry, something went wrong. Please try again.' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const suggestions = [
    "How am I doing this month?",
    "What am I spending the most on?",
    "What if I cut food spending by 20%?",
    "Run a simulation for the next 2 weeks",
    "Show me my recent expenses",
  ];

  return (
    <div>
      <div className="page-header">
        <h2>🤖 AI Copilot</h2>
        <p>Your personal finance assistant — powered by real data</p>
      </div>

      <div className="glass-panel" style={{ padding: 0, overflow: 'hidden' }}>
        <div className="chat-layout">
          <div className="chat-messages" style={{ padding: '24px 24px 0' }}>
            {messages.length === 0 ? (
              <div className="chat-empty">
                <p className="chat-empty-icon">💬</p>
                <p style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>Hey! I'm your finance copilot.</p>
                <p style={{ marginBottom: 16 }}>I have access to your spending data, dashboard, and simulation engine. Ask me anything:</p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, alignItems: 'center' }}>
                  {suggestions.map((s) => (
                    <button
                      key={s}
                      className="btn btn-secondary btn-sm"
                      onClick={() => { setInput(s); }}
                      type="button"
                      style={{ fontSize: 13 }}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((msg, idx) => (
                <div key={idx} className={`chat-bubble chat-bubble-${msg.role}`}>
                  <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                  {msg.tools_used && msg.tools_used.length > 0 && (
                    <div className="chat-tools-used">
                      {msg.tools_used.map((tool) => (
                        <span key={tool} className="chat-tool-badge">
                          📊 {tool.replace(/_/g, ' ')}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
            {loading && (
              <div className="chat-bubble chat-bubble-assistant">
                <div className="chat-typing"><span /><span /><span /></div>
              </div>
            )}
            <div ref={endRef} />
          </div>

          <form className="chat-input-bar" style={{ padding: '16px 24px' }} onSubmit={handleSend}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask your copilot anything..."
              disabled={loading}
              autoFocus
            />
            <button
              type="submit"
              className="chat-send-btn"
              disabled={!input.trim() || loading}
            >
              ➤
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
