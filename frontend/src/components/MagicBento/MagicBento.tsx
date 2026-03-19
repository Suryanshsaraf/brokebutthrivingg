import React, { useState, useRef } from 'react';
import './MagicBento.css';

interface MagicBentoProps {
  children: React.ReactNode;
  className?: string;
}

export const MagicBento = ({ children, className = '' }: MagicBentoProps) => {
  return (
    <div className={`magic-bento-grid ${className}`}>
      {children}
    </div>
  );
};

interface BentoCardProps {
  children: React.ReactNode;
  title?: string;
  subtitle?: string;
  className?: string;
  span?: 'small' | 'medium' | 'large' | 'tall' | 'wide' | 'full';
}

export const BentoCard = ({ children, title, subtitle, className = '', span = 'small' }: BentoCardProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [isHovered, setIsHovered] = useState(false);

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    setMousePos({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    });
  };

  return (
    <div
      ref={containerRef}
      className={`bento-card bento-span-${span} ${className}`}
      onMouseMove={handleMouseMove}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div 
        className="bento-spotlight" 
        style={{
          opacity: isHovered ? 1 : 0,
          background: `radial-gradient(400px circle at ${mousePos.x}px ${mousePos.y}px, rgba(99, 102, 241, 0.1), transparent 80%)`
        }}
      />
      <div className="bento-content">
        {(title || subtitle) && (
          <div className="bento-header">
            {title && <h3>{title}</h3>}
            {subtitle && <p className="bento-subtitle">{subtitle}</p>}
          </div>
        )}
        <div className="bento-inner">
          {children}
        </div>
      </div>
    </div>
  );
};
