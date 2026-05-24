import React, { useState } from 'react';
import './GameOverScreen.css';
import { getGrade, formatTime } from '../utils/scoring';
import ExemplarPanel from './ExemplarPanel';

/**
 * GameOverScreen — 게임 오버 화면 (v2)
 *
 * 시간 초과 또는 답변 횟수 초과 시 표시됩니다.
 * 클리어한 단계가 1개 이상이고 누적 점수가 1점 이상이면,
 * 리더보드 등록 폼이 함께 표시됩니다.
 */
export default function GameOverScreen({
  currentLevel,
  promptCount,
  clearedLevels = [],
  clearedStages = [],
  totalScore = 0,
  totalTimeUsed = 0,
  failedSessionId = null,
  onPlayAgain,
  onSubmitScore,
  onShowLeaderboard,
  isSubmitting = false,
}) {
  const [playerName, setPlayerName] = useState('');
  const [isSubmitted, setIsSubmitted] = useState(false);

  const canRegister = clearedStages.length > 0 && totalScore >= 1;
  const grade = canRegister ? getGrade(totalScore) : null;

  const handleSubmit = async () => {
    if (!playerName.trim() || isSubmitted || !canRegister) return;
    await onSubmitScore(playerName.trim().toUpperCase());
    setIsSubmitted(true);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleSubmit();
  };

  return (
    <div className="gameover-screen" id="gameover-screen">
      <div className="gameover-screen__content">
        <div className="gameover-screen__skull">💀</div>

        <div className="gameover-screen__title">GAME OVER</div>

        <div className="gameover-screen__reason">
          케르베로스의 관문을 통과하지 못했습니다
        </div>

        {/* 기본 통계 */}
        <div className="gameover-screen__stats">
          <div className="gameover-screen__stat">
            <span className="gameover-screen__stat-label">도달 레벨</span>
            <span className="gameover-screen__stat-value">LEVEL {currentLevel} / 3</span>
          </div>
          <div className="gameover-screen__stat">
            <span className="gameover-screen__stat-label">클리어한 관문</span>
            <span className="gameover-screen__stat-value">{clearedLevels.length} / 3</span>
          </div>
          <div className="gameover-screen__stat">
            <span className="gameover-screen__stat-label">사용한 답변</span>
            <span className="gameover-screen__stat-value">{promptCount}회</span>
          </div>
          {canRegister && (
            <>
              <div className="gameover-screen__stat">
                <span className="gameover-screen__stat-label">누적 점수</span>
                <span className="gameover-screen__stat-value">{totalScore}점</span>
              </div>
              <div className="gameover-screen__stat">
                <span className="gameover-screen__stat-label">랭크</span>
                <span className="gameover-screen__stat-value">{grade}</span>
              </div>
              <div className="gameover-screen__stat">
                <span className="gameover-screen__stat-label">총 소요 시간</span>
                <span className="gameover-screen__stat-value">
                  {formatTime(Math.round(totalTimeUsed))}
                </span>
              </div>
            </>
          )}
        </div>

        {/* 단계별 브레이크다운 (클리어한 단계가 있을 때만) */}
        {clearedStages.length > 0 && (
          <div className="gameover-screen__stats">
            {clearedStages.map((s) => (
              <div key={s.level} className="gameover-screen__stat">
                <span className="gameover-screen__stat-label">
                  🎯 STAGE {s.level} ({s.tier === 'full' ? '만점' : '절반'})
                </span>
                <span className="gameover-screen__stat-value">
                  +{s.score}점 · {formatTime(Math.round(s.time_used))}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* 등록 폼 (1점 이상일 때만) */}
        {canRegister && (
          <div className="result-screen__name-section">
            <div className="result-screen__name-title">
              🏆 ENTER YOUR NAME FOR HALL OF FAME
            </div>
            {!isSubmitted ? (
              <div className="result-screen__name-form">
                <input
                  type="text"
                  className="result-screen__name-input"
                  placeholder="NAME"
                  value={playerName}
                  onChange={(e) => setPlayerName(e.target.value.slice(0, 10))}
                  onKeyDown={handleKeyDown}
                  maxLength={10}
                  disabled={isSubmitting}
                  id="input-player-name-gameover"
                />
                <button
                  className="arcade-btn arcade-btn--green"
                  onClick={handleSubmit}
                  disabled={!playerName.trim() || isSubmitting}
                  id="btn-submit-score-gameover"
                >
                  {isSubmitting ? '...' : 'OK'}
                </button>
              </div>
            ) : (
              <div className="result-screen__submitted">
                ✅ SCORE REGISTERED!
              </div>
            )}
          </div>
        )}

        {/* 모범답안 토글 — 클리어 단계 + 실패한 마지막 단계까지 학습 가능 */}
        <ExemplarPanel
          sessions={[
            ...clearedStages.map((s) => ({
              level: s.level,
              session_id: s.session_id,
              tier: s.tier,
            })),
            ...(failedSessionId
              ? [{ level: currentLevel, session_id: failedSessionId, tier: 'fail' }]
              : []),
          ]}
        />

        <div className="gameover-screen__actions">
          <button
            className="arcade-btn"
            onClick={onPlayAgain}
            id="btn-retry"
          >
            CONTINUE?
          </button>
          {onShowLeaderboard && (
            <button
              className="arcade-btn arcade-btn--blue"
              onClick={onShowLeaderboard}
              id="btn-view-ranking-gameover"
            >
              🏆 RANKING
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
