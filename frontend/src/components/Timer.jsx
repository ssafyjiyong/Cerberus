import React from 'react';
import './Timer.css';
import { formatTime } from '../utils/scoring';

/**
 * Timer - 5분 카운트다운 타이머
 * 남은 시간에 따라 색상이 변합니다 (초록 → 노랑 → 빨강)
 */
export default function Timer({ timeRemaining, isWarning, isDanger }) {
  const statusClass = isDanger ? 'timer--danger' : isWarning ? 'timer--warning' : 'timer--safe';

  return (
    <div className={`timer ${statusClass}`} id="game-timer">
      <span className="timer__icon">⏱️</span>
      <span className="timer__display">{formatTime(timeRemaining)}</span>
    </div>
  );
}
