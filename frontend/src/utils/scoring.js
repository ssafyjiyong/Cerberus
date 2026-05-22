/**
 * 점수 계산 유틸리티
 * Total Score = (300 - T_used) * W_time + (P_max - P_used) * W_prompt
 */

const TIME_LIMIT = 300;  // 5분 = 300초
const P_MAX = 15;        // 최대 답변 횟수 (레벨당 5회)
const W_TIME = 1;        // 시간 가중치
const W_PROMPT = 10;     // 답변 효율 가중치

/**
 * 최종 점수 계산
 * @param {number} timeUsed - 사용한 시간 (초)
 * @param {number} promptCount - 사용한 답변 횟수
 * @returns {number} 총점
 */
export function calculateScore(timeUsed, promptCount) {
  const timeScore = Math.max(0, TIME_LIMIT - timeUsed) * W_TIME;
  const promptScore = Math.max(0, P_MAX - promptCount) * W_PROMPT;
  return Math.round(timeScore + promptScore);
}

/**
 * 시간 점수만 계산
 * @param {number} timeUsed - 사용한 시간 (초)
 * @returns {number} 시간 점수
 */
export function getTimeScore(timeUsed) {
  return Math.max(0, Math.round((TIME_LIMIT - timeUsed) * W_TIME));
}

/**
 * 답변 효율 점수만 계산
 * @param {number} promptCount - 사용한 답변 횟수
 * @returns {number} 효율 점수
 */
export function getPromptScore(promptCount) {
  return Math.max(0, (P_MAX - promptCount) * W_PROMPT);
}

/**
 * 초를 MM:SS 형식으로 변환
 * @param {number} seconds - 초
 * @returns {string} MM:SS 형식
 */
export function formatTime(seconds) {
  const mins = Math.floor(Math.max(0, seconds) / 60);
  const secs = Math.max(0, seconds) % 60;
  return `${String(mins).padStart(2, '0')}:${String(Math.floor(secs)).padStart(2, '0')}`;
}

/**
 * 점수에 따른 등급 반환
 * @param {number} score - 점수
 * @returns {string} 등급
 */
export function getGrade(score) {
  if (score >= 350) return 'S';
  if (score >= 280) return 'A';
  if (score >= 200) return 'B';
  if (score >= 120) return 'C';
  return 'D';
}

export const GAME_CONFIG = {
  TIME_LIMIT,
  P_MAX,
  W_TIME,
  W_PROMPT,
};
