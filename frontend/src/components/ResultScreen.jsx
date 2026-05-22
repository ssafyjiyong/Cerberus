import React, { useState } from 'react';
import './ResultScreen.css';
import { getTimeScore, getPromptScore, getGrade, formatTime } from '../utils/scoring';

/**
 * ResultScreen - 게임 클리어 결과 화면
 * 최종 점수, 등급, 브레이크다운을 보여주고 랭킹 등록을 제공합니다.
 */
export default function ResultScreen({
  score,
  timeUsed,
  promptCount,
  onSubmitScore,
  onPlayAgain,
  onShowLeaderboard,
  isSubmitting,
}) {
  const [playerName, setPlayerName] = useState('');
  const [isSubmitted, setIsSubmitted] = useState(false);

  const grade = getGrade(score);
  const timeScore = getTimeScore(timeUsed);
  const promptScore = getPromptScore(promptCount);

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

        {/* 점수 브레이크다운 */}
        <div className="result-screen__breakdown">
          <div className="result-screen__breakdown-row">
            <span className="result-screen__breakdown-label">⏱ 클리어 시간</span>
            <span className="result-screen__breakdown-value">{formatTime(timeUsed)}</span>
          </div>
          <div className="result-screen__breakdown-row">
            <span className="result-screen__breakdown-label">⏱ 시간 점수</span>
            <span className="result-screen__breakdown-value">+{timeScore}</span>
          </div>
          <div className="result-screen__breakdown-row">
            <span className="result-screen__breakdown-label">💬 답변 횟수</span>
            <span className="result-screen__breakdown-value">{promptCount}회</span>
          </div>
          <div className="result-screen__breakdown-row">
            <span className="result-screen__breakdown-label">💬 효율 점수</span>
            <span className="result-screen__breakdown-value">+{promptScore}</span>
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
