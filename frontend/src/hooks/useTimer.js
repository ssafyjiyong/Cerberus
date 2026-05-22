import { useState, useEffect, useRef, useCallback } from 'react';
import { GAME_CONFIG } from '../utils/scoring';

/**
 * 타이머 커스텀 훅
 * 300초(5분) 카운트다운을 관리합니다.
 */
export function useTimer() {
  const [timeRemaining, setTimeRemaining] = useState(GAME_CONFIG.TIME_LIMIT);
  const [isRunning, setIsRunning] = useState(false);
  const [startTimestamp, setStartTimestamp] = useState(null);
  const intervalRef = useRef(null);

  const timeUsed = GAME_CONFIG.TIME_LIMIT - timeRemaining;

  const start = useCallback(() => {
    setIsRunning(true);
    setStartTimestamp(Date.now());
  }, []);

  const pause = useCallback(() => {
    setIsRunning(false);
  }, []);

  const reset = useCallback(() => {
    setIsRunning(false);
    setTimeRemaining(GAME_CONFIG.TIME_LIMIT);
    setStartTimestamp(null);
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
  const isWarning = timeRemaining <= 60 && timeRemaining > 0;
  const isDanger = timeRemaining <= 30 && timeRemaining > 0;

  return {
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
