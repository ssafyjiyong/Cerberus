import React, { useState } from 'react';
import './ResultScreen.css';
import { getGrade, formatTime } from '../utils/scoring';
import ExemplarPanel from './ExemplarPanel';

/**
 * ResultScreen - 모든 단계 클리어 결과 화면
 *
 * 단계 단위 독립 세션이므로:
 * - score / timeUsed / promptCount 는 모든 단계의 합산값
 * - clearedStages 는 각 단계별 상세 내역 ({ level, score, time_used, prompt_count })
 */
export default function ResultScreen({
  score,
  timeUsed,
  promptCount,
  clearedStages = [],
  onSubmitScore,
  onPlayAgain,
  onShowLeaderboard,
  isSubmitting,
}) {
  const [playerName, setPlayerName] = useState('');
  const [isSubmitted, setIsSubmitted] = useState(false);

  const grade = getGrade(score);

  const handleSubmit = async () => {
    if (!playerName.trim() || isSubmitted) return;
    await onSubmitScore(playerName.trim().toUpperCase());
    setIsSubmitted(true);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleSubmit();
    }
  };

  return (
    <div className="result-screen" id="result-screen">
      <div className="result-screen__content">
        {/* 승리 타이틀 */}
        <div className="result-screen__title">ALL STAGES CLEARED!</div>
        <div className="result-screen__subtitle">
          케르베로스의 세 관문을 모두 통과했습니다
        </div>

        {/* 점수 박스 */}
        <div className="result-screen__score-box">
          <div className="result-screen__score-label">TOTAL SCORE</div>
          <div className="result-screen__score-value">{score}</div>
          <div className={`result-screen__grade result-screen__grade--${grade}`}>
            RANK: {grade}
          </div>
        </div>

        {/* 단계별 브레이크다운 */}
        <div className="result-screen__breakdown">
          {clearedStages.length > 0 && clearedStages.map((s) => (
            <div key={s.level} className="result-screen__breakdown-row">
              <span className="result-screen__breakdown-label">
                🎯 STAGE {s.level}
                {s.tier === 'full' && (
                  <span style={{ marginLeft: 8, color: 'var(--color-neon-green, #00ff88)' }}>
                    ★ 만점
                  </span>
                )}
                {s.tier === 'half' && (
                  <span style={{ marginLeft: 8, color: 'var(--color-fire-orange, #ffae42)' }}>
                    ◇ 절반
                  </span>
                )}
              </span>
              <span className="result-screen__breakdown-value">
                +{s.score}점 · {formatTime(Math.round(s.time_used))} · {s.prompt_count}회
              </span>
            </div>
          ))}
          <div className="result-screen__breakdown-row">
            <span className="result-screen__breakdown-label">⏱ 총 소요 시간</span>
            <span className="result-screen__breakdown-value">{formatTime(Math.round(timeUsed))}</span>
          </div>
          <div className="result-screen__breakdown-row">
            <span className="result-screen__breakdown-label">💬 총 답변 횟수</span>
            <span className="result-screen__breakdown-value">{promptCount}회</span>
          </div>
        </div>

        {/* 이름 입력 (랭킹 등록) */}
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
                id="input-player-name"
              />
              <button
                className="arcade-btn arcade-btn--green"
                onClick={handleSubmit}
                disabled={!playerName.trim() || isSubmitting}
                id="btn-submit-score"
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

        {/* 모범답안 토글 */}
        <ExemplarPanel
          sessions={clearedStages.map((s) => ({
            level: s.level,
            session_id: s.session_id,
            tier: s.tier,
          }))}
        />

        {/* 액션 버튼들 */}
        <div className="result-screen__actions">
          <button
            className="arcade-btn"
            onClick={onPlayAgain}
            id="btn-play-again"
          >
            PLAY AGAIN
          </button>
          <button
            className="arcade-btn arcade-btn--blue"
            onClick={onShowLeaderboard}
            id="btn-view-ranking"
          >
            🏆 RANKING
          </button>
        </div>
      </div>
    </div>
  );
}
