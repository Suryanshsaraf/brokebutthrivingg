import React from 'react';
import './LogoLoop.css';

interface LogoLoopProps {
  items: { icon: React.ReactNode; text?: string }[];
  direction?: 'left' | 'right';
  speed?: number;
  title?: string;
}

export const LogoLoop = ({ 
  items, 
  direction = 'left', 
  speed = 40,
  title
}: LogoLoopProps) => {
  // Duplicate items to ensure smooth infinite scroll
  const fullItems = [...items, ...items, ...items, ...items];

  return (
    <div className="logo-loop-container">
      {title && <p className="logo-loop-title">{title}</p>}
      <div className="logo-loop-wrapper overflow-hidden relative">
        <div 
          className={`logo-loop-track animate-loop-${direction}`}
          style={{ '--speed': `${speed}s` } as React.CSSProperties}
        >
          {fullItems.map((item, idx) => (
            <div key={idx} className="logo-loop-item">
              <span className="logo-loop-icon">{item.icon}</span>
              {item.text && <span className="logo-loop-text">{item.text}</span>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
