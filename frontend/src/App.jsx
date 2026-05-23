import React, { useState, useCallback, useEffect } from 'react';
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
 * 게임의 전체 흐름을 관리하는 최상위 컴포넌트입니다.
 */
export default function App() {
  const game = useGameState();
  const timer = useTimer();
  const [showLeaderboard, setShowLeaderboard] = useState(false);
  const [error, setError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  // 관리자 모드: null | 'login' | 'panel'
  const [adminMode, setAdminMode] = useState(null);

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

  // 타임아웃 감지
  useEffect(() => {
    if (timer.isTimedOut && game.gameState === 'playing') {
      game.setGameOver('timeout');
    }
  }, [timer.isTimedOut, game.gameState]);

  // 에러 자동 해제
  useEffect(() => {
    if (error) {
      const timeout = setTimeout(() => setError(null), 5000);
      return () => clearTimeout(timeout);
    }
  }, [error]);

  /**
   * 게임 시작 핸들러
   */
  const handleStartGame = useCallback(async () => {
    game.setIsLoading(true);
    setError(null);
    try {
      const response = await apiStartGame();
      game.startGame(response.session_id, response.question);
      timer.reset();
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

      // 프롬프트 수 초과 체크
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
   * 점수 제출 핸들러
   */
  const handleSubmitScore = useCallback(async (name) => {
    if (!game.sessionId) return;
    setIsSubmitting(true);
    try {
      await submitScore(game.sessionId, name);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  }, [game.sessionId]);

  /**
   * 재시작 핸들러
   */
  const handlePlayAgain = useCallback(() => {
    timer.reset();
    game.resetGame();
    setShowLeaderboard(false);
  }, [game, timer]);

  /**
   * 리더보드 표시 핸들러
   */
  const handleShowLeaderboard = useCallback(() => {
    setShowLeaderboard(true);
  }, []);

  const handleBackFromLeaderboard = useCallback(() => {
    setShowLeaderboard(false);
  }, []);

  // 현재 표시할 화면 결정
  const renderScreen = () => {
    // 리더보드 오버레이
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
      case 'levelClear':
        return (
          <GameScreen
            messages={game.messages}
            currentLevel={game.currentLevel}
            clearedLevels={game.clearedLevels}
            promptCount={game.promptCount}
            maxPrompts={game.maxPrompts}
            timeRemaining={timer.timeRemaining}
            isWarning={timer.isWarning}
            isDanger={timer.isDanger}
            isLoading={game.isLoading}
            gameState={game.gameState}
            levelInfo={game.levelInfo}
            onSendMessage={handleSendMessage}
          />
        );

      case 'allClear':
        return (
          <ResultScreen
            score={game.finalScore}
            timeUsed={game.finalTimeUsed}
            promptCount={game.promptCount}
            onSubmitScore={handleSubmitScore}
            onPlayAgain={handlePlayAgain}
            onShowLeaderboard={handleShowLeaderboard}
            isSubmitting={isSubmitting}
          />
        );

      case 'gameOver':
        return (
          <GameOverScreen
            currentLevel={game.currentLevel}
            promptCount={game.promptCount}
            clearedLevels={game.clearedLevels}
            onPlayAgain={handlePlayAgain}
          />
        );

      default:
        return null;
    }
  };

  return (
    <div className="app" id="app-root">
      {/* CRT 스캔라인 오버레이 */}
      <div className="crt-overlay" />

      {/* 아케이드 프레임 */}
      <div className="arcade-frame">
        <div className="app__screen">
          {renderScreen()}
        </div>
      </div>

      {/* 에러 토스트 */}
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

      {/* 관리자 페이지 (이스터에그 트리거로 진입) */}
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
