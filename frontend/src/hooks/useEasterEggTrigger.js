import { useEffect, useRef, useState } from 'react';

/**
 * useEasterEggTrigger - 스태프 크레딧(이스터에그) 진입 트리거 감지 훅.
 *
 * 키보드로 "easteregg" 문자열을 입력하면 unlocked 가 true 가 됩니다.
 * (이전 버전의 코나미 코드 ↑↑↓↓←→←→BA 시퀀스 트리거는 제거되었습니다.)
 *
 * 동작 규칙:
 *  - 마지막 9글자만 버퍼링하며 "easteregg" 와 정확히 일치할 때 트리거
 *  - input/textarea 에 포커스가 있을 때는 무시 (게임 입력란 보호)
 *  - 2초 동안 추가 입력이 없으면 버퍼 자동 초기화
 *
 * @returns {[boolean, function]} [unlocked, reset]
 */
const EASTER_EGG_WORD = 'easteregg';
const KEY_BUFFER_TIMEOUT_MS = 2000;

export function useEasterEggTrigger() {
  const [unlocked, setUnlocked] = useState(false);
  const keyBufferRef = useRef('');
  const keyTimerRef = useRef(null);

  useEffect(() => {
    const handleKey = (event) => {
      if (event.key.length !== 1) return;
      const tag = (event.target?.tagName || '').toLowerCase();
      if (tag === 'input' || tag === 'textarea') return;

      keyBufferRef.current = (keyBufferRef.current + event.key.toLowerCase()).slice(
        -EASTER_EGG_WORD.length
      );

      if (keyTimerRef.current) clearTimeout(keyTimerRef.current);
      keyTimerRef.current = setTimeout(() => {
        keyBufferRef.current = '';
      }, KEY_BUFFER_TIMEOUT_MS);

      if (keyBufferRef.current === EASTER_EGG_WORD) {
        keyBufferRef.current = '';
        setUnlocked(true);
      }
    };

    window.addEventListener('keydown', handleKey);
    return () => {
      window.removeEventListener('keydown', handleKey);
      if (keyTimerRef.current) clearTimeout(keyTimerRef.current);
    };
  }, []);

  const reset = () => setUnlocked(false);

  return [unlocked, reset];
}
