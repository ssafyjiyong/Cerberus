import { useState, useCallback } from 'react';
import { GAME_CONFIG } from '../utils/scoring';

/**
 * 게임 상태 관리 커스텀 훅
 * 게임의 전체 상태를 관리합니다.
 * 
 * 상태 흐름: idle → playing → levelClear → playing → ... → allClear / gameOver
 */

// 레벨 정보
const LEVELS = {
  1: {
    title: 'LEVEL 1',
    subtitle: '물리적 보안 / 단말기 보안',
    description: '사무실 보안 및 PC 화면 잠금',
    headName: '첫 번째 머리',
    emoji: '🔥',
  },
  2: {
    title: 'LEVEL 2',
    subtitle: '접근 통제 / 계정 관리',
    description: '관리자 계정 및 비밀번호 관리 정책',
    headName: '두 번째 머리',
    emoji: '💀',
  },
  3: {
    title: 'LEVEL 3',
    subtitle: '네트워크 보안 / 침해사고 대응',
    description: 'DB 접근 제어 및 로그 리뷰',
    headName: '세 번째 머리',
    emoji: '⚡',
  },
};

export function useGameState() {
  // 게임 상태: 'idle' | 'playing' | 'levelClear' | 'allClear' | 'gameOver'
  const [gameState, setGameState] = useState('idle');
  const [currentLevel, setCurrentLevel] = useState(1);
  const [sessionId, setSessionId] = useState(null);
  const [promptCount, setPromptCount] = useState(0);
  const [finalScore, setFinalScore] = useState(null);
  const [finalTimeUsed, setFinalTimeUsed] = useState(null);
  
  // 채팅 히스토리: 전체 레벨 통합
  const [messages, setMessages] = useState([]);
  
  // 로딩 상태
  const [isLoading, setIsLoading] = useState(false);

  // 클리어된 레벨 추적
  const [clearedLevels, setClearedLevels] = useState([]);

  /**
   * 게임 시작
   */
  const startGame = useCallback((newSessionId, firstQuestion) => {
    setGameState('playing');
    setCurrentLevel(1);
    setSessionId(newSessionId);
    setPromptCount(0);
    setFinalScore(null);
    setFinalTimeUsed(null);
    setClearedLevels([]);
    setMessages([
      {
        id: Date.now(),
        type: 'system',
        text: '⚔️ 케르베로스의 첫 번째 머리가 깨어납니다...',
        level: 1,
      },
      {
        id: Date.now() + 1,
        type: 'auditor',
        text: firstQuestion,
        level: 1,
      },
    ]);
  }, []);

  /**
   * 사용자 메시지 추가
   */
  const addUserMessage = useCallback((text) => {
    setMessages((prev) => [
      ...prev,
      {
        id: Date.now(),
        type: 'user',
        text,
        level: currentLevel,
      },
    ]);
    setPromptCount((prev) => prev + 1);
  }, [currentLevel]);

  /**
   * AI 응답 처리
   */
  const handleAIResponse = useCallback((response) => {
    const { status, message, level, is_game_clear, score, prompt_count, time_used } = response;

    // AI 메시지 추가
    setMessages((prev) => [
      ...prev,
      {
        id: Date.now(),
        type: 'auditor',
        text: message,
        level: level || currentLevel,
        status: status,
      },
    ]);

    if (prompt_count !== undefined) {
      setPromptCount(prompt_count);
    }

    if (status === 'pass') {
      if (is_game_clear) {
        // 모든 레벨 클리어!
        setClearedLevels((prev) => [...prev, currentLevel]);
        setFinalScore(score);
        setFinalTimeUsed(time_used);
        setGameState('allClear');
      } else {
        // 다음 레벨로 (백엔드가 이미 다음 레벨 번호를 반환함)
        const nextLevel = level || (currentLevel + 1);
        setClearedLevels((prev) => [...prev, currentLevel]);
        setGameState('levelClear');

        // 2.5초 후 다음 레벨 시작
        setTimeout(() => {
          setCurrentLevel(nextLevel);
          setGameState('playing');
          setMessages((prev) => [
            ...prev,
            {
              id: Date.now(),
              type: 'system',
              text: `⚔️ 케르베로스의 ${LEVELS[nextLevel]?.headName || '머리'}가 깨어납니다...`,
              level: nextLevel,
            },
          ]);
        }, 2500);
      }
    }
    // fail인 경우 계속 playing 상태 유지
  }, [currentLevel]);

  /**
   * 게임 오버 (시간 초과 or 답변 횟수 초과)
   */
  const setGameOver = useCallback((reason = 'timeout') => {
    setGameState('gameOver');
    setMessages((prev) => [
      ...prev,
      {
        id: Date.now(),
        type: 'system',
        text: reason === 'timeout' 
          ? '⏰ 시간이 초과되었습니다!' 
          : '💀 답변 횟수를 초과했습니다!',
      },
    ]);
  }, []);

  /**
   * 게임 리셋 (처음으로)
   */
  const resetGame = useCallback(() => {
    setGameState('idle');
    setCurrentLevel(1);
    setSessionId(null);
    setPromptCount(0);
    setFinalScore(null);
    setFinalTimeUsed(null);
    setMessages([]);
    setClearedLevels([]);
    setIsLoading(false);
  }, []);

  return {
    // 상태
    gameState,
    currentLevel,
    sessionId,
    promptCount,
    messages,
    isLoading,
    clearedLevels,
    finalScore,
    finalTimeUsed,
    
    // 레벨 정보
    levelInfo: LEVELS[currentLevel],
    allLevels: LEVELS,
    maxPrompts: GAME_CONFIG.P_MAX,
    
    // 액션
    startGame,
    addUserMessage,
    handleAIResponse,
    setGameOver,
    resetGame,
    setIsLoading,
    setGameState,
  };
}
