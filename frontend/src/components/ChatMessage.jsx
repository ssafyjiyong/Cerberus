import React from 'react';
import './ChatMessage.css';

/**
 * ChatMessage - 채팅 메시지 컴포넌트
 * 심사원(AI), 사용자, 시스템 메시지를 각각 다른 스타일로 표시합니다.
 */
export default function ChatMessage({ message }) {
  const { type, text, status } = message;

  if (type === 'system') {
    return (
      <div className="chat-message chat-message--system">
        <div className="chat-message__bubble">{text}</div>
      </div>
    );
  }

  const isAuditor = type === 'auditor';
  const typeClass = isAuditor ? 'chat-message--auditor' : 'chat-message--user';
  const statusClass = status === 'pass' ? 'chat-message__bubble--pass' : 
                      status === 'fail' ? 'chat-message__bubble--fail' : '';

  return (
    <div className={`chat-message ${typeClass}`}>
      <div className="chat-message__avatar">
        {isAuditor ? '🐕' : '🧑‍💻'}
      </div>
      <div className={`chat-message__bubble ${statusClass}`}>
        {text}
      </div>
    </div>
  );
}

/**
 * TypingIndicator - AI가 응답 중일 때 표시되는 타이핑 인디케이터
 */
export function TypingIndicator() {
  return (
    <div className="chat-message chat-message--auditor">
      <div className="chat-message__avatar">🐕</div>
      <div className="chat-message__bubble">
        <div className="chat-message__typing">
          <span className="chat-message__typing-dot" />
          <span className="chat-message__typing-dot" />
          <span className="chat-message__typing-dot" />
        </div>
      </div>
    </div>
  );
}
