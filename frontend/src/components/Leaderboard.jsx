import React, { useState, useEffect } from 'react';
import './Leaderboard.css';
import { getLeaderboard } from '../utils/api';
import { formatTime } from '../utils/scoring';

const TROPHY_ICONS = {
  1: '🥇',
  2: '🥈',
  3: '🥉',
};

/**
 * Leaderboard - Top 10 랭킹 보드
 * 명예의 전당을 표시합니다.
 */
export default function Leaderboard({ onBack }) {
  const [entries, setEntries] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadLeaderboard();
  }, []);

  const loadLeaderboard = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getLeaderboard();
      setEntries(data);
    } catch (err) {
      setError(err.message);
      // 폴백: 빈 리스트
      setEntries([]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="leaderboard" id="leaderboard-screen">
      <div className="leaderboard__content">
        <div className="leaderboard__title">🏆 HALL OF FAME</div>
        <div className="leaderboard__subtitle">TOP 10 AUDITORS</div>

        <div className="leaderboard__table">
          {/* 테이블 헤더 */}
          <div className="leaderboard__header">
            <span className="leaderboard__header-cell">RANK</span>
            <span className="leaderboard__header-cell">NAME</span>
            <span className="leaderboard__header-cell" style={{ textAlign: 'right' }}>SCORE</span>
            <span className="leaderboard__header-cell" style={{ textAlign: 'right' }}>TIME</span>
          </div>

          {/* 로딩 상태 */}
          {isLoading && (
            <div className="leaderboard__loading">LOADING...</div>
          )}

          {/* 에러 상태 */}
          {error && !isLoading && (
            <div className="leaderboard__empty">
              서버에 연결할 수 없습니다<br />
              <button
                className="arcade-btn"
                onClick={loadLeaderboard}
                style={{ marginTop: '16px', fontSize: '8px' }}
              >
                RETRY
              </button>
            </div>
          )}

          {/* 빈 상태 */}
          {!isLoading && !error && entries.length === 0 && (
            <div className="leaderboard__empty">
              아직 등록된 기록이 없습니다<br />
              첫 번째 도전자가 되어보세요!
            </div>
          )}

          {/* 랭킹 데이터 */}
          {!isLoading && entries.map((entry, index) => {
            const rank = entry.rank || index + 1;
            const rankClass = rank <= 3 ? `leaderboard__rank--${rank}` : 'leaderboard__rank--other';

            return (
              <div className="leaderboard__row" key={index}>
                <span className={`leaderboard__rank ${rankClass}`}>
                  {TROPHY_ICONS[rank] ? (
                    <span className="leaderboard__trophy">{TROPHY_ICONS[rank]}</span>
                  ) : (
                    rank
                  )}
                </span>
                <span className="leaderboard__name">{entry.name}</span>
                <span className="leaderboard__score">{entry.score}</span>
                <span className="leaderboard__time">{formatTime(entry.time_used)}</span>
              </div>
            );
          })}
        </div>

        <button
          className="arcade-btn leaderboard__back-btn"
          onClick={onBack}
          id="btn-back-from-leaderboard"
        >
          ← BACK
        </button>
      </div>
    </div>
  );
}
