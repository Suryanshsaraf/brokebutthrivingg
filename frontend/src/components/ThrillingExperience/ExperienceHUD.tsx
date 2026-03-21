import { useState, useEffect } from 'react';
import GlitchText from '../GlitchText/GlitchText';
import FallingText from '../FallingText/FallingText';
import './ThrillingExperience.css';

// Text Scrambler Effect Hook
function useScrambleText(text: string, isActive: string | boolean) {
  const [displayText, setDisplayText] = useState('');
  
  useEffect(() => {
    if (!isActive) {
      setDisplayText('');
      return;
    }
    
    let iterations = 0;
    const interval = setInterval(() => {
      setDisplayText(text.split('').map((letter, index) => {
        if (index < iterations) return letter;
        return String.fromCharCode(33 + Math.floor(Math.random() * 94));
      }).join(''));

      if (iterations >= text.length) clearInterval(interval);
      iterations += 1/3;
    }, 30);
    
    return () => clearInterval(interval);
  }, [text, isActive]);
  
  return displayText;
}

export function ExperienceHUD({ scrollProgress, onComplete }: { scrollProgress: number, onComplete: () => void }) {
  const [timeLeft, setTimeLeft] = useState(9000); // 9.000s countdown timer

  useEffect(() => {
    if (scrollProgress > 0.5 && scrollProgress < 0.8) {
      const interval = setInterval(() => {
        setTimeLeft(prev => Math.max(0, prev - 11)); // fast tick
      }, 10);
      return () => clearInterval(interval);
    }
  }, [scrollProgress]);

  const phase = scrollProgress < 0.25 ? 'denial' :
                scrollProgress < 0.50 ? 'intelligence' :
                scrollProgress < 0.80 ? 'intervention' : 'control';

  // Absolute fail-safe inline style generator
  const getPhaseStyle = (targetPhase: string): React.CSSProperties => {
    const isActive = phase === targetPhase;
    return {
      opacity: isActive ? 1 : 0,
      pointerEvents: isActive ? 'auto' : 'none',
      transform: isActive ? 'translate(-50%, -50%) scale(1)' : 'translate(-50%, calc(-50% + 20px)) scale(0.95)',
      transition: 'opacity 0.4s ease, transform 0.4s ease',
      visibility: isActive ? 'visible' : 'hidden',
    };
  };

  // Scramble text
  const agentText = useScrambleText("EMOTIONAL_SPEND_DETECTED: At this rate, you'll be broke in 9 days.", phase === 'intelligence');

  return (
    <div className="hud-container">

      {/* DENIAL PHASE */}
      <div className="hud-phase" style={getPhaseStyle('denial')}>
        <div style={{ minHeight: '100px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <GlitchText speed={1}>YOU THINK YOU'RE FINE</GlitchText>
        </div>
        <p className="phase-subtitle subtle">Scroll to face the reality of your ghost spending.</p>
      </div>

      {/* INTELLIGENCE PHASE */}
      <div className="hud-phase" style={getPhaseStyle('intelligence')}>
        <div className="agent-text-box" style={{ padding: '20px 40px' }}>
          <span className="scramble-text">{agentText}</span>
        </div>
        
        <div className="mirror-effect">
          <div className="projected-self" style={{ borderStyle: 'dotted', border: '1px solid rgba(255,255,255,0.2)', padding: '20px' }}>
            <span className="label" style={{ fontWeight: 'bold', color: '#c9ada7' }}>PROJECTED SELF (30 DAYS)</span>
            <span className="value" style={{ fontSize: '5rem', display: 'block', color: '#ffffff' }}>-₹14,500</span>
          </div>
        </div>
      </div>

      {/* INTERVENTION PHASE */}
      <div className="hud-phase" style={getPhaseStyle('intervention')}>
        <div className="countdown-container" style={{ position: 'relative', zIndex: 20 }}>
          <h3 style={{ color: '#c9ada7' }}>TIME TO ZERO BALANCE</h3>
          <div className="harsh-timer" style={{ fontSize: '9rem', color: '#ffffff' }}>{(timeLeft / 1000).toFixed(3)}s</div>
        </div>
        <FallingText 
          text="DEBT CRISIS OVERSPENDING DEFAULT INSOLVENCY BROKE INTEREST INFLATION BANKRUPTCY" 
          highlightWords={["DEBT", "BROKE", "CRISIS"]}
          trigger={phase === 'intervention'}
        />
      </div>

      {/* CONTROL PHASE */}
      <div className="hud-phase" style={getPhaseStyle('control')}>
        <h2 className="phase-title flashy-brand-text">You need BrokeButThriving.</h2>
        <p className="phase-subtitle">Stop being a passenger in your own economy.</p>
        <button className="btn btn-primary mt-4" style={{ padding: '16px 32px', fontSize: '1.2rem' }} onClick={() => {
          window.scrollTo({ top: 0, behavior: 'smooth' });
          setTimeout(onComplete, 100);
        }}>
          Take Control
        </button>
      </div>
    </div>
  );
}
