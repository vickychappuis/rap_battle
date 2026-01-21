/**
 * BattleTimeline - Scrolling timeline of all battle turns.
 *
 * Displays cards for each turn with user transcriptions and AI lyrics.
 * Auto-scrolls to the latest turn.
 */

import { useEffect, useRef } from 'react';
import type { TurnData } from '../api/session';

interface BattleTimelineProps {
  turnHistory: TurnData[];
}

export function BattleTimeline({ turnHistory }: BattleTimelineProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest turn
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [turnHistory.length]);

  if (turnHistory.length === 0) {
    return null;
  }

  return (
    <div
      ref={containerRef}
      className="battle-timeline"
      style={{
        maxHeight: '400px',
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
        gap: '1rem',
      }}
    >
      {turnHistory.map((turn) => {
        const roundNum = Math.ceil(turn.turn_number / 2);
        const isUser = turn.player === 'user';

        return (
          <div
            key={`${turn.player}-${turn.turn_number}`}
            className="card"
            style={{
              borderLeft: isUser ? '4px solid var(--ink-black)' : '4px solid var(--stamp-red)',
              marginLeft: isUser ? '0' : '1rem',
              marginRight: isUser ? '1rem' : '0',
            }}
          >
            <div
              className="turn-header"
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                marginBottom: '0.5rem',
              }}
            >
              <span
                className="stamp"
                style={{
                  fontSize: '0.75rem',
                  padding: '0.25rem 0.5rem',
                }}
              >
                {isUser ? 'You' : 'AI'}
              </span>
              <span className="text-gray text-sm">Round {roundNum}</span>
            </div>

            <p
              className={isUser ? 'mono' : ''}
              style={{
                fontSize: isUser ? '0.9rem' : '1.1rem',
                lineHeight: 1.6,
                fontStyle: isUser ? 'normal' : 'italic',
              }}
            >
              "{isUser ? turn.transcription : turn.lyrics}"
            </p>
          </div>
        );
      })}
    </div>
  );
}
