import { useRef, useEffect, useState } from 'react';
import { AudioEngine } from './AudioEngine';
import { ParticleCanvas } from './ParticleCanvas';
import { ExperienceHUD } from './ExperienceHUD';
import './ThrillingExperience.css';

/**
 * ThrillingExperience Container
 * Appended to the bottom of the Dashboard page. When users scroll into this section,
 * it acts as a very tall container (e.g., 400vh) allowing them to strictly scroll
 * through the phases.
 */
export default function ThrillingExperience({ onComplete }: { onComplete: () => void }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [progress, setProgress] = useState(0);
  const [started, setStarted] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      const scrollY = window.scrollY;
      const height = document.documentElement.scrollHeight - window.innerHeight;
      const prog = Math.max(0, Math.min(1, scrollY / height));
      
      setProgress(prog);
      
      if (prog > 0.01 && !started) {
        setStarted(true);
        AudioEngine.start().catch(console.error);
      }

      if (started) {
        AudioEngine.updateScroll(prog);
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    // Initial sync
    handleScroll();
    
    return () => {
      window.removeEventListener('scroll', handleScroll);
      AudioEngine.stop();
    };
  }, [started]);

  return (
    <div className="thrilling-experience-wrapper" ref={containerRef}>
      {/* Sticky viewport frame that locks to the screen while scrolling through the 400vh container */}
      <div className="sticky-viewport">
        {/* Particle Canvas background */}
        <ParticleCanvas scrollProgress={progress} />

        {/* HUD Overlay */}
        <ExperienceHUD scrollProgress={progress} onComplete={onComplete} />
      </div>
    </div>
  );
}
