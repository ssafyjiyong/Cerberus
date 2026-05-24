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
 * 게임 시작 - 새 세션 생성 (단계 단위 독립 세션, v2 응답)
 *
 * @param {number} level - 시작할 레벨 (1~3). 단계 전환마다 새로 호출하세요.
 * @returns {Promise<{
 *   session_id: string,
 *   level: number,
 *   title: string,
 *   subtitle: string,
 *   isms_control_id: string,
 *   isms_control_title: string,
 *   scenario_context: string,
 *   question: string,
 *   message: string,
 *   time_limit: number,
 *   p_max: number,
 *   domain: string,
 * }>}
 */
export async function startGame(level = 1) {
  return apiRequest('/api/game/start', {
    method: 'POST',
    body: JSON.stringify({ level }),
  });
}

/**
 * 채팅 메시지 전송 - AI 심사원에게 답변
 * @param {string} sessionId - 세션 ID
 * @param {string} message - 사용자 메시지
 * @returns {Promise<{
 *   status: 'pass'|'fail',
 *   tier: 'full'|'half'|'fail',
 *   matched_path_id: string,
 *   message: string,
 *   level: number,
 *   is_stage_clear: boolean,
 *   score: number|null,
 *   prompt_count: number,
 *   time_used: number
 * }>}
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
 * 리더보드 점수 등록 — 클리어한 단계들의 점수 합산 (v2)
 *
 * 게임오버여도 1점 이상 누적이면 등록 가능. 백엔드가 미클리어 세션은 무시합니다.
 *
 * @param {string[]} sessionIds - 클리어한 단계들의 세션 ID 목록 (1개 이상)
 * @param {string} name - 플레이어 이름
 * @returns {Promise<{success: boolean, message: string, score: number, time_used: number, cleared_levels: number[]}>}
 */
export async function submitScore(sessionIds, name) {
  return apiRequest('/api/leaderboard', {
    method: 'POST',
    body: JSON.stringify({
      session_ids: sessionIds,
      name: name,
    }),
  });
}

/**
 * 모범답안 조회 — 세션 종료 후에만 호출 가능 (진행 중이면 403).
 *
 * @param {string} sessionId
 * @returns {Promise<{
 *   session_id: string,
 *   level: number,
 *   is_cleared: boolean,
 *   final_tier: string|null,
 *   final_score: number|null,
 *   isms_control_id: string,
 *   isms_control_title: string,
 *   scenario_context: string,
 *   auditor_question: string,
 *   default_rebuttal: string,
 *   answer_paths: Array<{
 *     id: string, tier: string, description: string,
 *     trigger_keywords: string[], rebuttal: string, follow_up: string,
 *     acknowledgment_keywords: string[], compensating_keywords: string[],
 *     exemplar_answer: string,
 *   }>
 * }>}
 */
export async function getSessionExemplars(sessionId) {
  return apiRequest(`/api/game/session/${encodeURIComponent(sessionId)}/exemplars`, {
    method: 'GET',
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
