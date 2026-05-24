import { useState, useEffect, useRef, useCallback } from 'react';
import { GAME_CONFIG } from '../utils/scoring';

/**
 * 타이머 커스텀 훅
 * 단계마다 다른 제한 시간을 사용할 수 있도록 `reset(newLimit)` 에서 한도를 갱신합니다.
 */
export function useTimer() {
  const [timeLimit, setTimeLimit] = useState(GAME_CONFIG.TIME_LIMIT);
  const [timeRemaining, setTimeRemaining] = useState(GAME_CONFIG.TIME_LIMIT);
  const [isRunning, setIsRunning] = useState(false);
  const intervalRef = useRef(null);

  const timeUsed = timeLimit - timeRemaining;

  const start = useCallback(() => {
    setIsRunning(true);
  }, []);

  const pause = useCallback(() => {
    setIsRunning(false);
  }, []);

  /**
   * 타이머 초기화. newLimit 을 넘기면 그 시간으로 재설정합니다.
   */
  const reset = useCallback((newLimit) => {
    setIsRunning(false);
    const limit = Number.isFinite(newLimit) && newLimit > 0
      ? newLimit
      : GAME_CONFIG.TIME_LIMIT;
    setTimeLimit(limit);
    setTimeRemaining(limit);
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (isRunning && timeRemaining > 0) {
      intervalRef.current = setInterval(() => {
        setTimeRemaining((prev) => {
          const next = prev - 1;
          if (next <= 0) {
            setIsRunning(false);
            clearInterval(intervalRef.current);
            return 0;
          }
          return next;
        });
      }, 1000);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [isRunning]);

  const isTimedOut = timeRemaining <= 0;
  // 경고/위험 임계값: 전체 한도의 비율 기반
  const isWarning = timeRemaining <= Math.max(60, Math.round(timeLimit * 0.25)) && timeRemaining > 0;
  const isDanger = timeRemaining <= Math.max(30, Math.round(timeLimit * 0.1)) && timeRemaining > 0;

  return {
    timeLimit,
    timeRemaining,
    timeUsed,
    isRunning,
    isTimedOut,
    isWarning,
    isDanger,
    start,
    pause,
    reset,
  };
}
