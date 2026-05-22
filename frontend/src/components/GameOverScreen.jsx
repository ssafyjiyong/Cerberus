import React from 'react';
import './GameOverScreen.css';

/**
 * GameOverScreen - 게임 오버 화면
 * 시간 초과 또는 답변 횟수 초과 시 표시됩니다.
 */
export default function GameOverScreen({
  currentLevel,
  promptCount,
  clearedLevels,
  onPlayAgain,
}) {
  return (
    <div className="gameover-screen" id="gameover-screen">
      <div className="gameover-screen__content">
        <div className="gameover-screen__skull">💀</div>

        <div className="gameover-screen__title">GAME OVER</div>

        <div className="gameover-screen__reason">
          케르베로스의 관문을 통과하지 못했습니다
        </div>

        {/* 통계 */}
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
        </div>

        <div className="gameover-screen__actions">
          <button
            className="arcade-btn"
            onClick={onPlayAgain}
            id="btn-retry"
          >
            CONTINUE?
          </button>
        </div>
      </div>
    </div>
  );
}
