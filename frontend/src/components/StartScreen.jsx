import React, { useEffect } from 'react';
import './StartScreen.css';
import cerberusLogo from '../assets/cerberus_logo.png';
import gameBackground from '../assets/game_background.png';
import CreditsModal from './CreditsModal';
import { useEasterEggTrigger } from '../hooks/useEasterEggTrigger';
import { useAdminTrigger } from '../hooks/useAdminTrigger';

/**
 * StartScreen - 게임 시작 화면
 * 아케이드 스타일의 타이틀 화면으로, 로고와 시작 버튼을 표시합니다.
 *
 * 숨겨진 트리거:
 *  - "easteregg" 키보드 입력                              → 제작 크레딧 모달
 *  - "admin" 키보드 입력 OR 케르베로스 로고 5회 탭/클릭   → 관리자 페이지
 *    (둘 중 어느 방식이든 발동되며, 발동 후 비밀번호 모달이 뜹니다)
 */
export default function StartScreen({
  onStart,
  onShowLeaderboard,
  isLoading,
  onRequestAdmin,
  adminActive = false,
}) {
  const [showCredits, closeCredits] = useEasterEggTrigger();
  const adminTrigger = useAdminTrigger({ disabled: adminActive });

  useEffect(() => {
    if (adminTrigger.triggered && onRequestAdmin) {
      adminTrigger.reset();
      onRequestAdmin();
    }
  }, [adminTrigger, onRequestAdmin]);

  return (
    <div className="start-screen" id="start-screen">
      {/* 배경 이미지 */}
      <div className="start-screen__bg">
        <img src={gameBackground} alt="Dark underworld background" />
      </div>

      {/* 콘텐츠 */}
      <div className="start-screen__content">
        {/* 로고 — 전체 영역이 관리자 진입용 5회 탭 트리거 (모바일 친화) */}
        <div className="start-screen__logo-wrap">
          <img
            src={cerberusLogo}
            alt="Cerberus: The Dark Auditor"
            className="start-screen__logo"
          />
          <button
            type="button"
            className="start-screen__logo-hit"
            onClick={adminTrigger.handleHeadClick}
            aria-label="관리자 진입 (5회 탭)"
            tabIndex={-1}
          />
        </div>

        {/* 부제 */}
        <div>
          <h1 className="start-screen__title">어둠의 심사원</h1>
          <p className="start-screen__subtitle">
            ISMS 인증 심사의 관문을 통과하라
          </p>
        </div>

        {/* 장식용 LED */}
        <div className="start-screen__decorations">
          <span className="start-screen__led start-screen__led--red" />
          <span className="start-screen__led start-screen__led--orange" />
          <span className="start-screen__led start-screen__led--yellow" />
          <span className="start-screen__led start-screen__led--orange" />
          <span className="start-screen__led start-screen__led--red" />
        </div>

        {/* 시작 버튼 */}
        <button
          className="start-screen__start-btn"
          onClick={onStart}
          disabled={isLoading}
          id="btn-start-game"
        >
          {isLoading ? 'LOADING...' : 'PRESS START'}
        </button>

        {/* INSERT COIN 깜빡이는 텍스트 */}
        {!isLoading && (
          <div className="start-screen__insert-coin">INSERT COIN</div>
        )}

        {/* 게임 설명 */}
        <div className="start-screen__info">
          <div className="start-screen__info-title">★ HOW TO PLAY ★</div>
          <div>AI 심사원 케르베로스와 인터뷰를 진행합니다</div>
          <div>3개의 관문을 5분 안에 통과하세요</div>
          <div>빠르고 정확할수록 높은 점수!</div>
        </div>

        {/* 랭킹 버튼 */}
        <button
          className="start-screen__leaderboard-btn"
          onClick={onShowLeaderboard}
          id="btn-show-leaderboard"
        >
          🏆 TOP 10 RANKING
        </button>
      </div>

      {/* 이스터에그: "easteregg" 키보드 입력 시 크레딧 노출 */}
      {showCredits && <CreditsModal onClose={closeCredits} />}
    </div>
  );
}
