import React, { useEffect } from 'react';
import './CreditsModal.css';

/**
 * CreditsModal - 숨겨진 스태프 크레딧 화면 (이스터에그).
 *
 * StartScreen에서 코나미 코드(↑↑↓↓←→←→BA)를 입력하면 노출됩니다.
 * 레트로 아케이드 네온 스타일로 제작 크레딧을 표시합니다.
 *
 * @param {function} onClose - 모달을 닫는 콜백
 */
export default function CreditsModal({ onClose }) {
  // ESC 키로 닫기
  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  return (
    <div
      className="credits-modal"
      id="credits-modal"
      role="dialog"
      aria-modal="true"
      aria-label="스태프 크레딧"
      onClick={onClose}
    >
      <div
        className="credits-modal__cabinet"
        onClick={(event) => event.stopPropagation()}
      >
        {/* 패널 내부를 가로지르는 스캔라인 */}
        <div className="credits-modal__scanline" />

        {/* 코나미 코드 해제 배지 */}
        <div className="credits-modal__badge">
          ▲ ▲ ▼ ▼ ◀ ▶ ◀ ▶ B A — UNLOCKED
        </div>

        {/* 케르베로스의 세 머리 */}
        <div className="credits-modal__heads">
          <span className="credits-modal__head">🐺</span>
          <span className="credits-modal__head">🐺</span>
          <span className="credits-modal__head">🐺</span>
        </div>

        <h2 className="credits-modal__title">STAFF CREDITS</h2>

        {/* 크레딧 본문 */}
        <div className="credits-modal__roll">
          <div className="credits-modal__label">제작 · PRODUCED BY</div>
          <div className="credits-modal__name">제프리킴</div>
          <div className="credits-modal__name-sub">JEFFREY KIM</div>
        </div>

        <div className="credits-modal__divider">★ ━━━━━━━━━━━━━ ★</div>

        <div className="credits-modal__game">
          CERBERUS<span> : THE DARK AUDITOR</span>
        </div>
        <div className="credits-modal__thanks">THANK YOU FOR PLAYING</div>

        <button
          className="credits-modal__close"
          onClick={onClose}
          id="btn-close-credits"
        >
          ▸ PRESS ESC TO RETURN ◂
        </button>
      </div>
    </div>
  );
}
