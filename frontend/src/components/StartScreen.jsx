import React from 'react';
import './StartScreen.css';
import cerberusLogo from '../assets/cerberus_logo.png';
import gameBackground from '../assets/game_background.png';
import CreditsModal from './CreditsModal';
import { useKonamiCode } from '../hooks/useKonamiCode';

/**
 * StartScreen - 게임 시작 화면
 * 아케이드 스타일의 타이틀 화면으로, 로고와 시작 버튼을 표시합니다.
 *
 * 숨겨진 이스터에그: 코나미 코드(↑↑↓↓←→←→BA)를 입력하면
 * 제작 크레딧(CreditsModal)이 노출됩니다.
 */
export default function StartScreen({ onStart, onShowLeaderboard, isLoading }) {
  const [showCredits, closeCredits] = useKonamiCode();

  return (
    <div className="start-screen" id="start-screen">
      {/* 배경 이미지 */}
      <div className="start-screen__bg">
        <img src={gameBackground} alt="Dark underworld background" />
      </div>

      {/* 콘텐츠 */}
      <div className="start-screen__content">
        {/* 로고 */}
        <img
          src={cerberusLogo}
          alt="Cerberus: The Dark Auditor"
          className="start-screen__logo"
        />

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

      {/* 이스터에그: 코나미 코드(↑↑↓↓←→←→BA) 입력 시 크레딧 노출 */}
      {showCredits && <CreditsModal onClose={closeCredits} />}
    </div>
  );
}
