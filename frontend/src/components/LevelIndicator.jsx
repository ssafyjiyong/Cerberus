import React from 'react';
import './LevelIndicator.css';

const HEADS = [
  { level: 1, icon: '🔥', label: 'LV1' },
  { level: 2, icon: '💀', label: 'LV2' },
  { level: 3, icon: '⚡', label: 'LV3' },
];

/**
 * LevelIndicator - 레벨 진행 표시기
 * 케르베로스의 3개 머리로 현재 진행 상황을 표시합니다.
 */
export default function LevelIndicator({ currentLevel, clearedLevels, promptCount, maxPrompts }) {
  const promptPercent = promptCount / maxPrompts;
  const promptClass = promptPercent >= 0.8 ? 'level-indicator__prompt-count--danger' 
    : promptPercent >= 0.6 ? 'level-indicator__prompt-count--warning' 
    : '';

  return (
    <div className="level-indicator" id="level-indicator">
      {HEADS.map((head, index) => {
        const isActive = head.level === currentLevel;
        const isCleared = clearedLevels.includes(head.level);
        
        return (
          <React.Fragment key={head.level}>
            {index > 0 && (
              <div className={`level-indicator__separator ${
                clearedLevels.includes(HEADS[index - 1].level) ? 'level-indicator__separator--cleared' : ''
              }`} />
            )}
            <div className={`level-indicator__head ${
              isActive ? 'level-indicator__head--active' : ''
            } ${isCleared ? 'level-indicator__head--cleared' : ''}`}>
              <span className="level-indicator__icon">{head.icon}</span>
              <span className="level-indicator__label">{head.label}</span>
            </div>
          </React.Fragment>
        );
      })}
      
      {/* 답변 횟수 카운터 */}
      <div className="level-indicator__prompts">
        <span className="level-indicator__prompt-label">MSG</span>
        <span className={`level-indicator__prompt-count ${promptClass}`}>
          {promptCount}/{maxPrompts}
        </span>
      </div>
    </div>
  );
}
