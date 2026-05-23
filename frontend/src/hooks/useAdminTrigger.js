import { useEffect, useRef, useState } from 'react';

/**
 * useAdminTrigger - 관리자 페이지 진입 트리거 감지 훅
 *
 * 두 가지 방식으로 트리거됩니다:
 * 1. 키보드로 "admin" 문자열 입력
 * 2. 케르베로스 첫 번째 머리(왼쪽) 영역을 짧은 시간 안에 5번 클릭
 *
 * @param {Object} options
 * @param {boolean} [options.disabled=false] - true 면 트리거 감지 일시 중지
 * @returns {{ triggered: boolean, handleHeadClick: function, reset: function }}
 */
const ADMIN_WORD = 'admin';
const CLICK_THRESHOLD = 5;
const CLICK_WINDOW_MS = 3000;
const KEY_BUFFER_TIMEOUT_MS = 1500;

export function useAdminTrigger({ disabled = false } = {}) {
  const [triggered, setTriggered] = useState(false);
  const keyBufferRef = useRef('');
  const keyTimerRef = useRef(null);
  const clickTimesRef = useRef([]);

  useEffect(() => {
    if (disabled) return undefined;

    const handleKey = (event) => {
      // 문자 한 글자 키만 누적 (Shift/Ctrl 등 무시)
      if (event.key.length !== 1) return;
      // 입력 필드 안에 포커스가 있을 때는 무시 (admin 비밀번호 등 입력 보호)
      const tag = (event.target?.tagName || '').toLowerCase();
      if (tag === 'input' || tag === 'textarea') return;

      keyBufferRef.current = (keyBufferRef.current + event.key.toLowerCase()).slice(
        -ADMIN_WORD.length
      );

      if (keyTimerRef.current) clearTimeout(keyTimerRef.current);
      keyTimerRef.current = setTimeout(() => {
        keyBufferRef.current = '';
      }, KEY_BUFFER_TIMEOUT_MS);

      if (keyBufferRef.current === ADMIN_WORD) {
        keyBufferRef.current = '';
        setTriggered(true);
      }
    };

    window.addEventListener('keydown', handleKey);
    return () => {
      window.removeEventListener('keydown', handleKey);
      if (keyTimerRef.current) clearTimeout(keyTimerRef.current);
    };
  }, [disabled]);

  const handleHeadClick = () => {
    if (disabled) return;
    const now = Date.now();
    clickTimesRef.current = [...clickTimesRef.current, now].filter(
      (t) => now - t <= CLICK_WINDOW_MS
    );
    if (clickTimesRef.current.length >= CLICK_THRESHOLD) {
      clickTimesRef.current = [];
      setTriggered(true);
    }
  };

  const reset = () => setTriggered(false);

  return { triggered, handleHeadClick, reset };
}
