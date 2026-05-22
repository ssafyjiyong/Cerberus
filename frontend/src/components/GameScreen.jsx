import React, { useState, useRef, useEffect } from 'react';
import './GameScreen.css';
import Timer from './Timer';
import LevelIndicator from './LevelIndicator';
import ChatMessage, { TypingIndicator } from './ChatMessage';

/**
 * GameScreen - 메인 게임(채팅) 화면
 * 타이머, 레벨 표시, 채팅 영역, 입력 영역으로 구성됩니다.
 */
export default function GameScreen({
  messages,
  currentLevel,
  clearedLevels,
  promptCount,
  maxPrompts,
  timeRemaining,
  isWarning,
  isDanger,
  isLoading,
  gameState,
  levelInfo,
  onSendMessage,
}) {
  const [inputText, setInputText] = useState('');
  const chatEndRef = useRef(null);
  const inputRef = useRef(null);

  // 새 메시지가 추가되면 스크롤
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // 레벨 클리어 후 포커스 복원
  useEffect(() => {
    if (gameState === 'playing') {
      inputRef.current?.focus();
    }
  }, [gameState]);

  const handleSend = () => {
    const trimmed = inputText.trim();
    if (!trimmed || isLoading || gameState !== 'playing') return;
    onSendMessage(trimmed);
    setInputText('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const isInputDisabled = isLoading || gameState !== 'playing';

  return (
    <div className="game-screen" id="game-screen">
      {/* 상단 헤더 */}
      <div className="game-screen__header">
        <div className="game-screen__header-left">
          <Timer
            timeRemaining={timeRemaining}
            isWarning={isWarning}
            isDanger={isDanger}
          />
          <div>
            <div className="game-screen__level-title">
              {levelInfo?.emoji} {levelInfo?.title}
            </div>
            <div className="game-screen__level-subtitle">
              {levelInfo?.subtitle}
            </div>
          </div>
        </div>
        <div className="game-screen__header-right">
          <LevelIndicator
            currentLevel={currentLevel}
            clearedLevels={clearedLevels}
            promptCount={promptCount}
            maxPrompts={maxPrompts}
          />
        </div>
      </div>

      {/* 채팅 영역 */}
      <div className="game-screen__chat-area" id="chat-area">
        {messages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}
        {isLoading && <TypingIndicator />}
        <div ref={chatEndRef} />
      </div>

      {/* 레벨 클리어 오버레이 */}
      {gameState === 'levelClear' && (
        <div className="game-screen__level-clear-overlay">
          <div className="game-screen__level-clear-text">
            STAGE {currentLevel} CLEAR!
          </div>
        </div>
      )}

      {/* 입력 영역 */}
      <div className="game-screen__input-area">
        <textarea
          ref={inputRef}
          className="game-screen__input"
          placeholder={isInputDisabled ? '대기 중...' : '답변을 입력하세요...'}
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isInputDisabled}
          rows={1}
          id="chat-input"
        />
        <button
          className="game-screen__send-btn"
          onClick={handleSend}
          disabled={isInputDisabled || !inputText.trim()}
          id="btn-send"
        >
          SEND ▶
        </button>
      </div>
    </div>
  );
}
