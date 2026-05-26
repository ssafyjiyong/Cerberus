import React, { useState, useCallback, useEffect, useRef } from 'react';
import './App.css';
import { useGameState } from './hooks/useGameState';
import { useTimer } from './hooks/useTimer';
import { startGame as apiStartGame, sendChat, submitScore } from './utils/api';

import StartScreen from './components/StartScreen';
import GameScreen from './components/GameScreen';
import ResultScreen from './components/ResultScreen';
import GameOverScreen from './components/GameOverScreen';
import Leaderboard from './components/Leaderboard';
import AdminAccessModal from './components/AdminAccessModal';
import AdminPanel from './components/AdminPanel';
import { hasToken } from './utils/adminAuth';

/**
 * App - 케르베로스: 어둠의 심사원 메인 앱
 *
 * 단계별 독립 세션 모델:
 * - 각 단계마다 새 세션을 백엔드에서 받아 시작
 * - 단계 통과 시 화면(messages)과 타이머가 초기화되고 다음 단계로 진입
 * - 모든 단계 통과 시 누적 점수로 리더보드 등록
 */
export default function App() {
  const game = useGameState();
  const timer = useTimer();
  const [showLeaderboard, setShowLeaderboard] = useState(false);
  const [error, setError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  // 관리자 모드: null | 'login' | 'panel'
  const [adminMode, setAdminMode] = useState(null);

  // stageClear → 다음 단계 전환 중복 방지용 가드
  const advancingRef = useRef(false);

  // 관리자 진입 요청: 기존 토큰이 있으면 바로 패널, 없으면 로그인 모달
  const handleRequestAdmin = useCallback(() => {
    setAdminMode(hasToken() ? 'panel' : 'login');
  }, []);

  const handleAdminLoginSuccess = useCallback(() => {
    setAdminMode('panel');
  }, []);

  const handleAdminClose = useCallback(() => {
    setAdminMode(null);
  }, []);

  // 타임아웃 감지 (현재 단계 한정)
  useEffect(() => {
    if (timer.isTimedOut && game.gameState === 'playing') {
      game.setGameOver('timeout');
    }
  }, [timer.isTimedOut, game.gameState]);

  // 에러 자동 해제
  useEffect(() => {
    if (error) {
      const t = setTimeout(() => setError(null), 5000);
      return () => clearTimeout(t);
    }
  }, [error]);

  /**
   * 게임 시작 핸들러 — Stage 1 세션 생성
   */
  const handleStartGame = useCallback(async () => {
    game.startNewGame();
    game.setIsLoading(true);
    setError(null);
    try {
      // 새 게임 시작 — 출제 이력 없음
      const response = await apiStartGame(1, []);
      game.beginStage(1, response);
      timer.reset(response.time_limit);
      timer.start();
    } catch (err) {
      setError(err.message);
    } finally {
      game.setIsLoading(false);
    }
  }, [game, timer]);

  /**
   * 메시지 전송 핸들러
   */
  const handleSendMessage = useCallback(async (text) => {
    if (!game.sessionId) return;

    game.addUserMessage(text);
    game.setIsLoading(true);
    setError(null);

    try {
      const response = await sendChat(game.sessionId, text);
      game.handleAIResponse(response);

      // 프롬프트 한도 초과 (현재 단계 한정)
      if (response.prompt_count >= game.maxPrompts && response.status !== 'pass') {
        game.setGameOver('prompt_limit');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      game.setIsLoading(false);
    }
  }, [game]);

  /**
   * stageClear → 다음 단계 세션 시작 (2.5초 후 자동 진행)
   */
  useEffect(() => {
    if (game.gameState !== 'stageClear') return;
    if (advancingRef.current) return;
    advancingRef.current = true;

    const nextLevel = game.stage + 1;
    timer.pause();

    const t = setTimeout(async () => {
      try {
        // 같은 게임 안에서 이미 출제된 질문은 제외 (전체 풀 랜덤 + 중복 방지)
        const response = await apiStartGame(nextLevel, game.usedQuestionIds || []);
        game.beginStage(nextLevel, response);
        timer.reset(response.time_limit);
        timer.start();
      } catch (err) {
        setError(err.message);
      } finally {
        advancingRef.current = false;
      }
    }, 2500);

    return () => {
      clearTimeout(t);
      advancingRef.current = false;
    };
  }, [game.gameState, game.stage, game.beginStage, timer]);

  /**
   * 점수 제출 — 클리어한 모든 단계의 세션 ID 를 합산 제출
   */
  const handleSubmitScore = useCallback(async (name) => {
    if (!game.sessionIds || game.sessionIds.length === 0) return;
    setIsSubmitting(true);
    try {
      await submitScore(game.sessionIds, name);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  }, [game.sessionIds]);

  /**
   * 재시작 핸들러
   */
  const handlePlayAgain = useCallback(() => {
    timer.reset();
    game.resetGame();
    setShowLeaderboard(false);
  }, [game, timer]);

  /**
   * 리더보드 표시
   */
  const handleShowLeaderboard = useCallback(() => {
    setShowLeaderboard(true);
  }, []);

  const handleBackFromLeaderboard = useCallback(() => {
    setShowLeaderboard(false);
  }, []);

  const renderScreen = () => {
    if (showLeaderboard) {
      return <Leaderboard onBack={handleBackFromLeaderboard} />;
    }

    switch (game.gameState) {
      case 'idle':
        return (
          <StartScreen
            onStart={handleStartGame}
            onShowLeaderboard={handleShowLeaderboard}
            isLoading={game.isLoading}
            onRequestAdmin={handleRequestAdmin}
            adminActive={!!adminMode}
          />
        );

      case 'playing':
      case 'stageClear':
        return (
          <GameScreen
            messages={game.messages}
            currentLevel={game.stage}
            clearedLevels={game.clearedLevels}
            promptCount={game.promptCount}
            maxPrompts={game.maxPrompts}
            timeRemaining={timer.timeRemaining}
            isWarning={timer.isWarning}
            isDanger={timer.isDanger}
            isLoading={game.isLoading}
            gameState={game.gameState}
            levelInfo={game.stageInfo}
            stageDomain={game.stageSubtitle}
            stageTitle={game.stageTitle}
            ismsControlId={game.ismsControlId}
            ismsControlTitle={game.ismsControlTitle}
            onSendMessage={handleSendMessage}
          />
        );

      case 'allClear':
        return (
          <ResultScreen
            score={game.totalScore}
            timeUsed={game.totalTimeUsed}
            promptCount={game.totalPromptCount}
            clearedStages={game.clearedStages}
            onSubmitScore={handleSubmitScore}
            onPlayAgain={handlePlayAgain}
            onShowLeaderboard={handleShowLeaderboard}
            isSubmitting={isSubmitting}
          />
        );

      case 'gameOver':
        return (
          <GameOverScreen
            currentLevel={game.stage}
            promptCount={game.promptCount}
            clearedLevels={game.clearedLevels}
            clearedStages={game.clearedStages}
            totalScore={game.totalScore}
            totalTimeUsed={game.totalTimeUsed}
            failedSessionId={game.sessionId}
            onPlayAgain={handlePlayAgain}
            onSubmitScore={handleSubmitScore}
            onShowLeaderboard={handleShowLeaderboard}
            isSubmitting={isSubmitting}
          />
        );

      default:
        return null;
    }
  };

  return (
    <div className="app" id="app-root">
      <div className="crt-overlay" />

      <div className="arcade-frame">
        <div className="app__screen">
          {renderScreen()}
        </div>
      </div>

      {error && (
        <div className="app__error-toast">
          ⚠️ {error}
          <button
            className="app__error-close"
            onClick={() => setError(null)}
          >
            ✕
          </button>
        </div>
      )}

      {adminMode === 'login' && (
        <AdminAccessModal
          onClose={handleAdminClose}
          onSuccess={handleAdminLoginSuccess}
        />
      )}
      {adminMode === 'panel' && (
        <AdminPanel onClose={handleAdminClose} />
      )}
    </div>
  );
}
