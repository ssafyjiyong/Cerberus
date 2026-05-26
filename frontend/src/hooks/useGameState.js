import { useState, useCallback } from 'react';

/**
 * 게임 상태 관리 커스텀 훅 — 단계별 독립 세션 모델 (v2 — tier 기반)
 *
 * 흐름:
 *   idle
 *     → (Stage 1 세션 시작) playing
 *     → (full or half) stageClear     ← 두 tier 모두 단계 클리어
 *       → (다음 단계 세션 시작) playing  ... 반복 ...
 *     → (마지막 단계 통과) allClear
 *     → (timeout / prompt_limit) gameOver
 *
 * 각 단계는 별개의 session_id 를 가지며, 화면(messages)도 단계 진입 시 초기화됩니다.
 * 최종 점수는 단계별 점수의 합으로 계산됩니다. half 통과는 절반 점수로 누적됩니다.
 *
 * 게임오버여도 클리어한 단계가 1개 이상이면 리더보드 등록이 가능합니다.
 */

const STAGES = {
  1: { title: 'STAGE 1', headName: '첫 번째 머리', emoji: '🔥' },
  2: { title: 'STAGE 2', headName: '두 번째 머리', emoji: '💀' },
  3: { title: 'STAGE 3', headName: '세 번째 머리', emoji: '⚡' },
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

  // 현재 단계 출제 정보
  const [stageTitle, setStageTitle] = useState('');
  const [stageSubtitle, setStageSubtitle] = useState('');
  const [ismsControlId, setIsmsControlId] = useState('');
  const [ismsControlTitle, setIsmsControlTitle] = useState('');
  const [scenarioContext, setScenarioContext] = useState('');

  // 단계 누적 데이터
  // 각 원소: { level, session_id, score, tier, time_used, prompt_count, isms_control_id }
  const [clearedStages, setClearedStages] = useState([]);

  // 같은 게임 안에서 이미 출제된 질문 ID — 다음 단계 /start 호출 시 exclude 로 전달
  const [usedQuestionIds, setUsedQuestionIds] = useState([]);
  const [currentQuestionId, setCurrentQuestionId] = useState(null);

  const [isLoading, setIsLoading] = useState(false);

  /**
   * 새 단계 세션이 시작되었을 때 호출.
   * sessionData 는 /api/game/start 응답 (v2 스키마).
   */
  const beginStage = useCallback((stageNum, sessionData) => {
    setStage(stageNum);
    setSessionId(sessionData.session_id);
    setPromptCount(0);
    setMaxPrompts(sessionData.p_max);
    setTimeLimit(sessionData.time_limit);
    setStageTitle(sessionData.title || `STAGE ${stageNum}`);
    setStageSubtitle(sessionData.subtitle || sessionData.domain || '');
    setIsmsControlId(sessionData.isms_control_id || '');
    setIsmsControlTitle(sessionData.isms_control_title || '');
    setScenarioContext(sessionData.scenario_context || '');
    // 출제된 질문 ID 추적
    const qid = sessionData.question_id || '';
    setCurrentQuestionId(qid || null);
    if (qid) {
      setUsedQuestionIds((prev) => (prev.includes(qid) ? prev : [...prev, qid]));
    }
    setGameState('playing');

    const initialMessages = [
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
    ];
    if (sessionData.scenario_context) {
      initialMessages.push({
        id: Date.now() + 2,
        type: 'scenario',
        text: sessionData.scenario_context,
        level: stageNum,
        ismsControl: sessionData.isms_control_id
          ? `${sessionData.isms_control_id} ${sessionData.isms_control_title || ''}`.trim()
          : '',
      });
    }
    initialMessages.push({
      id: Date.now() + 3,
      type: 'auditor',
      text: sessionData.question,
      level: stageNum,
    });
    setMessages(initialMessages);
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
    setIsmsControlId('');
    setIsmsControlTitle('');
    setScenarioContext('');
    setUsedQuestionIds([]);
    setCurrentQuestionId(null);
  }, []);

  const addUserMessage = useCallback((text) => {
    setMessages((prev) => [
      ...prev,
      { id: Date.now(), type: 'user', text, level: stage },
    ]);
  }, [stage]);

  /**
   * AI 응답 처리.
   * 백엔드 응답 (v2): { status, tier, matched_path_id, message, level,
   *                    is_stage_clear, score, prompt_count, time_used }
   */
  const handleAIResponse = useCallback((response) => {
    const {
      status,
      tier = 'fail',
      message,
      score,
      prompt_count,
      time_used,
      is_stage_clear,
    } = response;

    setMessages((prev) => [
      ...prev,
      {
        id: Date.now(),
        type: 'auditor',
        text: message,
        level: stage,
        status,
        tier,
      },
    ]);

    if (prompt_count !== undefined) {
      setPromptCount(prompt_count);
    }

    if (is_stage_clear || tier === 'full' || tier === 'half') {
      setClearedStages((prev) => [
        ...prev,
        {
          level: stage,
          session_id: sessionId,
          score: score ?? 0,
          tier,
          time_used: time_used ?? 0,
          prompt_count: prompt_count ?? 0,
          isms_control_id: ismsControlId,
          isms_control_title: ismsControlTitle,
        },
      ]);
      if (stage < 3) {
        setGameState('stageClear');
      } else {
        setGameState('allClear');
      }
    }
  }, [stage, sessionId, ismsControlId, ismsControlTitle]);

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
    setStageTitle('');
    setStageSubtitle('');
    setIsmsControlId('');
    setIsmsControlTitle('');
    setScenarioContext('');
    setClearedStages([]);
    setUsedQuestionIds([]);
    setCurrentQuestionId(null);
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

    // 단계 출제 정보
    stageTitle,
    stageSubtitle,
    stageDomain: stageSubtitle, // legacy alias
    ismsControlId,
    ismsControlTitle,
    scenarioContext,

    // 누적값
    clearedStages,
    clearedLevels,
    sessionIds,
    totalScore,
    totalTimeUsed,
    totalPromptCount,
    usedQuestionIds,
    currentQuestionId,

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
