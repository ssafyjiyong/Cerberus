import { useEffect, useRef, useState } from 'react';

/**
 * useAdminTrigger - 관리자 페이지 진입 트리거 감지 훅
 *
 * 두 가지 방식으로 트리거됩니다 (둘 다 활성):
 *  1. 키보드로 "admin" 5글자를 1.5초 안에 입력 (PC 환경)
 *  2. 케르베로스 캐릭터(로고) 5회 탭/클릭을 3초 안에 (모바일 환경)
 *
 * 트리거 후 어떤 방식이든 setTriggered(true) 가 되며, 호출자에서
 * 비밀번호 모달을 띄워 실제 관리자 인증을 진행합니다.
 *
 * 동작 규칙:
 *  - 키보드: 마지막 5글자만 버퍼링, input/textarea 포커스 시 무시,
 *    1.5초 동안 추가 입력이 없으면 버퍼 자동 초기화
 *  - 클릭: 3초 슬라이딩 윈도우 안에 5회 누적되면 트리거
 *
 * @param {Object} [options]
 * @param {boolean} [options.disabled=false] true 이면 트리거 감지 일시 중지
 * @returns {{ triggered: boolean, handleHeadClick: function, reset: function }}
 */
const ADMIN_WORD = 'admin';
const KEY_BUFFER_TIMEOUT_MS = 1500;
const CLICK_THRESHOLD = 5;
const CLICK_WINDOW_MS = 3000;

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

  /**
   * 케르베로스 로고 클릭/탭 핸들러.
   * StartScreen 의 로고 위 투명 버튼에 연결해 호출됩니다.
   */
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
