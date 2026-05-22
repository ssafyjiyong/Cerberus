import { useEffect, useRef, useState } from 'react';

/**
 * useKonamiCode - 코나미 코드(↑↑↓↓←→←→BA) 입력을 감지하는 훅.
 *
 * 시퀀스를 끝까지 정확히 입력하면 unlocked가 true가 됩니다.
 * 중간에 틀린 키를 누르면 진행도가 초기화됩니다.
 *
 * @returns {[boolean, function]} [unlocked, reset]
 */
const KONAMI_SEQUENCE = [
  'ArrowUp',
  'ArrowUp',
  'ArrowDown',
  'ArrowDown',
  'ArrowLeft',
  'ArrowRight',
  'ArrowLeft',
  'ArrowRight',
  'b',
  'a',
];

export function useKonamiCode() {
  const [unlocked, setUnlocked] = useState(false);
  const progressRef = useRef(0);

  useEffect(() => {
    const handleKeyDown = (event) => {
      // 문자키(b, a)는 대소문자를 무시하고, 방향키는 event.key를 그대로 사용
      const key =
        event.key.length === 1 ? event.key.toLowerCase() : event.key;

      if (key === KONAMI_SEQUENCE[progressRef.current]) {
        progressRef.current += 1;
        if (progressRef.current === KONAMI_SEQUENCE.length) {
          progressRef.current = 0;
          setUnlocked(true);
        }
      } else {
        // 틀린 키: 그 키가 시퀀스 첫 글자면 진행도 1, 아니면 0으로 초기화
        progressRef.current = key === KONAMI_SEQUENCE[0] ? 1 : 0;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const reset = () => setUnlocked(false);

  return [unlocked, reset];
}
