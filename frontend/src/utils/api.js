/**
 * API 통신 유틸리티
 * FastAPI 백엔드와의 통신을 담당합니다.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

/**
 * API 요청 헬퍼 함수
 */
async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const config = {
    headers: {
      'Content-Type': 'application/json',
    },
    ...options,
  };

  try {
    const response = await fetch(url, config);
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP Error: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      throw new Error('서버에 연결할 수 없습니다. 백엔드 서버가 실행 중인지 확인해주세요.');
    }
    throw error;
  }
}

/**
 * 게임 시작 - 새 세션 생성
 * @returns {Promise<{session_id: string, level: number, question: string, message: string}>}
 */
export async function startGame() {
  return apiRequest('/api/game/start', {
    method: 'POST',
  });
}

/**
 * 채팅 메시지 전송 - AI 심사원에게 답변
 * @param {string} sessionId - 세션 ID
 * @param {string} message - 사용자 메시지
 * @returns {Promise<{status: string, message: string, level: number, is_game_clear: boolean, score?: number, prompt_count: number, time_used: number}>}
 */
export async function sendChat(sessionId, message) {
  return apiRequest('/api/game/chat', {
    method: 'POST',
    body: JSON.stringify({
      session_id: sessionId,
      message: message,
    }),
  });
}

/**
 * 리더보드 조회 - Top 10
 * @returns {Promise<Array<{rank: number, name: string, score: number, time_used: number, created_at: string}>>}
 */
export async function getLeaderboard() {
  return apiRequest('/api/leaderboard', {
    method: 'GET',
  });
}

/**
 * 리더보드 점수 등록
 * @param {string} sessionId - 세션 ID
 * @param {string} name - 플레이어 이름
 * @returns {Promise<{success: boolean, rank: number}>}
 */
export async function submitScore(sessionId, name) {
  return apiRequest('/api/leaderboard', {
    method: 'POST',
    body: JSON.stringify({
      session_id: sessionId,
      name: name,
    }),
  });
}

/**
 * 서버 헬스 체크
 * @returns {Promise<{status: string}>}
 */
export async function healthCheck() {
  return apiRequest('/api/health', {
    method: 'GET',
  });
}
