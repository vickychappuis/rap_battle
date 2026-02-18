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
      className="battle-timeline max-h-[400px] overflow-y-auto flex flex-col gap-4"
    >
      {turnHistory.map((turn) => {
        const roundNum = Math.ceil(turn.turn_number / 2);
        const isUser = turn.player === 'user';

        return (
          <div
            key={`${turn.player}-${turn.turn_number}`}
            className="card"
            style={{
              borderLeft: isUser ? '4px solid var(--color-ink-black)' : '4px solid var(--color-spray-paint-red)',
              marginLeft: isUser ? '0' : '1rem',
              marginRight: isUser ? '1rem' : '0',
            }}
          >
            <div className="turn-header flex justify-between mb-2">
              <span className="stamp text-xs px-2 py-1">
                {isUser ? 'You' : 'AI'}
              </span>
              <span className="text-xerox-gray text-sm">Round {roundNum}</span>
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
