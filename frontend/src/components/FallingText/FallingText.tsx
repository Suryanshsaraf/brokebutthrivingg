import { useEffect, useState } from 'react';
import './FallingText.css';

interface FallingTextProps {
  text: string;
  delay?: number;
  highlightWords?: string[];
  trigger?: boolean;
}

const FallingText = ({ text, delay = 0, highlightWords = [], trigger = true }: FallingTextProps) => {
  const [words, setWords] = useState<{id: number, text: string, delay: number, left: number, rotate: number, duration: number}[]>([]);
  
  useEffect(() => {
    if (trigger) {
      const wordList = text.split(' ');
      const newWords = wordList.map((w, i) => ({
        id: i,
        text: w,
        delay: delay + i * 0.4 + Math.random() * 0.5,
        left: Math.random() * 90 + 5,
        rotate: (Math.random() - 0.5) * 90,
        duration: 2.5 + Math.random() * 1.5
      }));
      setWords(newWords);
    } else {
      setWords([]);
    }
  }, [text, trigger, delay]);

  return (
    <div className="falling-text-container">
      {words.map((word) => (
        <span 
          key={word.id} 
          className={`falling-word ${highlightWords.includes(word.text) ? 'highlight' : ''}`}
          style={{ 
            animationDelay: `${word.delay}s`,
            left: `${word.left}%`,
            '--random-rotate': `${word.rotate}deg`,
            '--fall-duration': `${word.duration}s`
          } as React.CSSProperties}
        >
          {word.text}
        </span>
      ))}
    </div>
  );
};

export default FallingText;
