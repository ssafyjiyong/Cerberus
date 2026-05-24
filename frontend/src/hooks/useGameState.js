import { useState, useCallback } from 'react';

/**
 * 게임 상태 관리 커스텀 훅 — 단계별 독립 세션 모델
 *
 * 흐름:
 *   idle
 *     → (Stage 1 세션 시작) playing
 *     → (pass) stageClear
 *       → (다음 단계 세션 시작) playing  ... 반복 ...
 *     → (마지막 단계 pass) allClear
 *     → (timeout / prompt_limit) gameOver
 *
 * 각 단계는 별개의 session_id 를 가지며, 화면(messages)도 단계 진입 시 초기화됩니다.
 * 최종 점수는 단계별 점수의 합으로 계산됩니다.
 */

// 단계별 표시 메타데이터 (UI 라벨 전용 — 실제 도메인 텍스트는 백엔드에서 받음)
const STAGES = {
  1: {
    title: 'STAGE 1',
    headName: '첫 번째 머리',
    emoji: '🔥',
  },
  2: {
    title: 'STAGE 2',
    headName: '두 번째 머리',
    emoji: '💀',
  },
  3: {
    title: 'STAGE 3',
    headName: '세 번째 머리',
    emoji: '⚡',
  },
};

export function useGameState() {
  // 'idle' | 'playing' | 'stageClear' | 'allClear' | 'gameOver'
  const [gameState, setGameState] = useState('idle');
  const [stage, setStage] = useState(1);
  const [sessionId, setSessionId] = useState(null);

  // 현재 단계 채팅 메시지 (단계 전환 시 초기화)
  const [messages, setMessages] = useState([]);

  // 현재 단계 진행 상태
  const [promptCount, setPromptCount] = useState(0);
  const [maxPrompts, setMaxPrompts] = useState(10);
  const [timeLimit, setTimeLimit] = useState(300);
  const [stageDomain, setStageDomain] = useState('');
  const [passLogic, setPassLogic] = useState('AND');

  // 단계 누적 데이터 (리더보드 제출 / 결과 화면용)
  // 각 원소: { level, session_id, score, time_used, prompt_count }
  const [clearedStages, setClearedStages] = useState([]);

  const [isLoading, setIsLoading] = useState(false);

  /**
   * 새 단계 세션이 시작되었을 때 호출.
   * sessionData 는 /api/game/start 응답.
   */
  const beginStage = useCallback((stageNum, sessionData) => {
    setStage(stageNum);
    setSessionId(sessionData.session_id);
    setPromptCount(0);
    setMaxPrompts(sessionData.p_max);
    setTimeLimit(sessionData.time_limit);
    setStageDomain(sessionData.domain || '');
    setPassLogic(sessionData.pass_logic || 'AND');
    setGameState('playing');
    setMessages([
      {
        id: Date.now(),
        type: 'system',
        text: `⚔️ ${STAGES[stageNum]?.headName || '머리'}가 깨어납니다...`,
        level: stageNum,
      },
      {
        id: Date.now() + 1,
        type: 'system',
        text: sessionData.message,
        level: stageNum,
      },
      {
        id: Date.now() + 2,
        type: 'auditor',
        text: sessionData.question,
        level: stageNum,
      },
    ]);
  }, []);

  /**
   * 새 게임 시작 — 누적 상태를 모두 초기화. (실제 세션 시작은 App 이 처리)
   */
  const startNewGame = useCallback(() => {
    setStage(1);
    setSessionId(null);
    setMessages([]);
    setPromptCount(0);
    setClearedStages([]);
    // gameState 는 beginStage 호출 시 'playing' 으로 전환됨
  }, []);

  const addUserMessage = useCallback((text) => {
    setMessages((prev) => [
      ...prev,
      { id: Date.now(), type: 'user', text, level: stage },
    ]);
  }, [stage]);

  /**
   * AI 응답 처리.
   * 백엔드 응답: { status, message, level, is_stage_clear, score, prompt_count, time_used }
   */
  const handleAIResponse = useCallback((response) => {
    const { status, message, score, prompt_count, time_used } = response;

    setMessages((prev) => [
      ...prev,
      {
        id: Date.now(),
        type: 'auditor',
        text: message,
        level: stage,
        status,
      },
    ]);

    if (prompt_count !== undefined) {
      setPromptCount(prompt_count);
    }

    if (status === 'pass') {
      setClearedStages((prev) => [
        ...prev,
        {
          level: stage,
          session_id: response.session_id || sessionId,
          score: score ?? 0,
          time_used: time_used ?? 0,
          prompt_count: prompt_count ?? 0,
        },
      ]);
      if (stage < 3) {
        setGameState('stageClear');
      } else {
        setGameState('allClear');
      }
    }
    // fail 이면 그대로 playing 상태 유지
  }, [stage, sessionId]);

  /**
   * 게임 오버 (타임아웃 / 답변 횟수 초과)
   */
  const setGameOver = useCallback((reason = 'timeout') => {
    setGameState('gameOver');
    setMessages((prev) => [
      ...prev,
      {
        id: Date.now(),
        type: 'system',
        text:
          reason === 'timeout'
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
    setStage(1);
    setSessionId(null);
    setMessages([]);
    setPromptCount(0);
    setMaxPrompts(10);
    setTimeLimit(300);
    setStageDomain('');
    setPassLogic('AND');
    setClearedStages([]);
    setIsLoading(false);
  }, []);

  // ── 파생 계산값 ──
  const totalScore = clearedStages.reduce((sum, c) => sum + (c.score || 0), 0);
  const totalTimeUsed = clearedStages.reduce((sum, c) => sum + (c.time_used || 0), 0);
  const totalPromptCount = clearedStages.reduce((sum, c) => sum + (c.prompt_count || 0), 0);
  const clearedLevels = clearedStages.map((c) => c.level);
  const sessionIds = clearedStages.map((c) => c.session_id).filter(Boolean);

  return {
    // 상태
    gameState,
    stage,
    currentLevel: stage,
    sessionId,
    promptCount,
    messages,
    isLoading,
    maxPrompts,
    timeLimit,
    stageDomain,
    passLogic,

    // 누적값
    clearedStages,
    clearedLevels,
    sessionIds,
    totalScore,
    totalTimeUsed,
    totalPromptCount,

    // 표시 메타
    stageInfo: STAGES[stage],
    levelInfo: STAGES[stage], // 하위 호환
    allStages: STAGES,

    // 액션
    beginStage,
    startNewGame,
    addUserMessage,
    handleAIResponse,
    setGameOver,
    resetGame,
    setIsLoading,
    setGameState,
  };
}
