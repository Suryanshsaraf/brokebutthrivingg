import { useEffect, useState } from 'react';
import './FloatingEmojis.css';

const EMOJIS = ['🍔', '🍕', '🍟', '🍜', '💸', '💰', '🪙', '💳', '☕'];

export default function FloatingEmojis() {
  const [items, setItems] = useState<{ id: number; emoji: string; left: number; delay: number; duration: number; size: number }[]>([]);

  useEffect(() => {
    // Generate some initial emojis
    const initialItems = Array.from({ length: 40 }).map((_, i) => ({
      id: i,
      emoji: EMOJIS[Math.floor(Math.random() * EMOJIS.length)],
      left: Math.random() * 100, // random x position %
      delay: Math.random() * -20, // negative delay so they start already on screen
      duration: 10 + Math.random() * 20, // 10-30s float duration
      size: 16 + Math.random() * 24, // 16px-40px font size
    }));
    setItems(initialItems);
  }, []);

  return (
    <div className="floating-emojis-container">
      {items.map((item) => (
        <div
          key={item.id}
          className="floating-emoji"
          style={{
            left: `${item.left}%`,
            animationDelay: `${item.delay}s`,
            animationDuration: `${item.duration}s`,
            fontSize: `${item.size}px`,
          }}
        >
          {item.emoji}
        </div>
      ))}
    </div>
  );
}
