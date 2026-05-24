import React from 'react';
import './ChatMessage.css';

/**
 * ChatMessage — 채팅 메시지 컴포넌트
 * 타입: system | scenario | auditor | user
 * 평가 등급(tier): full | half | fail
 */
export default function ChatMessage({ message }) {
  const { type, text, status, tier, ismsControl } = message;

  if (type === 'system') {
    return (
      <div className="chat-message chat-message--system">
        <div className="chat-message__bubble">{text}</div>
      </div>
    );
  }

  if (type === 'scenario') {
    return (
      <div className="chat-message chat-message--system">
        <div
          className="chat-message__bubble"
          style={{
            borderColor: 'var(--color-fire-orange, #ffae42)',
            background: 'rgba(60, 30, 0, 0.45)',
            textAlign: 'left',
          }}
        >
          {ismsControl && (
            <div
              style={{
                fontSize: 11,
                letterSpacing: 1,
                marginBottom: 6,
                color: 'var(--color-fire-orange, #ffae42)',
              }}
            >
              📑 근거 항목 — {ismsControl}
            </div>
          )}
          <div style={{ fontSize: 13, lineHeight: 1.55, whiteSpace: 'pre-wrap' }}>
            🎬 {text}
          </div>
        </div>
      </div>
    );
  }

  const isAuditor = type === 'auditor';
  const typeClass = isAuditor ? 'chat-message--auditor' : 'chat-message--user';

  // tier 기반 시각화 — full(녹색)/half(주황)/fail(빨강)
  let statusClass = '';
  if (tier === 'full') statusClass = 'chat-message__bubble--pass';
  else if (tier === 'half') statusClass = 'chat-message__bubble--half';
  else if (tier === 'fail' || status === 'fail') statusClass = 'chat-message__bubble--fail';
  else if (status === 'pass') statusClass = 'chat-message__bubble--pass';

  return (
    <div className={`chat-message ${typeClass}`}>
      <div className="chat-message__avatar">
        {isAuditor ? '🐕' : '🧑‍💻'}
      </div>
      <div className={`chat-message__bubble ${statusClass}`}>
        {tier === 'half' && (
          <div
            style={{
              fontSize: 10,
              letterSpacing: 1,
              marginBottom: 4,
              color: 'var(--color-fire-orange, #ffae42)',
            }}
          >
            ◇ HALF PASS
          </div>
        )}
        {tier === 'full' && (
          <div
            style={{
              fontSize: 10,
              letterSpacing: 1,
              marginBottom: 4,
              color: 'var(--color-neon-green, #00ff88)',
            }}
          >
            ★ FULL PASS
          </div>
        )}
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
