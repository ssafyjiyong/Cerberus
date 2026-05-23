/**
 * 관리자 API 클라이언트.
 * 모든 호출에 베어러 토큰을 자동 첨부하고, 401 응답 시 토큰을 제거합니다.
 */
import { authHeaders, clearToken, setToken } from './adminAuth';

const BASE = import.meta.env.VITE_API_URL || '';

async function call(method, path, body = null) {
  const headers = { 'Content-Type': 'application/json', ...authHeaders() };
  const opts = { method, headers };
  if (body !== null) opts.body = JSON.stringify(body);

  let res;
  try {
    res = await fetch(`${BASE}${path}`, opts);
  } catch (err) {
    throw new Error('서버에 연결할 수 없습니다. 백엔드가 실행 중인지 확인하세요.');
  }

  let data = {};
  try {
    data = await res.json();
  } catch {
    /* empty body */
  }

  if (!res.ok) {
    if (res.status === 401) clearToken();
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
  return data;
}

export const adminApi = {
  // ── 인증 ──
  login: async (password) => {
    const data = await call('POST', '/api/admin/auth/login', { password });
    setToken(data.token);
    return data;
  },
  logout: async () => {
    try {
      await call('POST', '/api/admin/auth/logout');
    } finally {
      clearToken();
    }
  },
  changePassword: (current_password, new_password) =>
    call('POST', '/api/admin/auth/password', { current_password, new_password }),

  // ── 설정 ──
  getConfig: () => call('GET', '/api/admin/config'),
  updateLevel: (level, updates) =>
    call('PUT', `/api/admin/config/levels/${level}`, updates),
  importLevels: (level_configs) =>
    call('POST', '/api/admin/config/levels/import', { level_configs }),
  updateGameParams: (updates) =>
    call('PUT', '/api/admin/config/game-params', updates),
  setMaintenance: (enabled) =>
    call('PUT', '/api/admin/config/maintenance', { enabled }),
  resetDefaults: (reset_password = false) =>
    call('POST', '/api/admin/config/reset', { reset_password }),

  // ── AI 어시스트 ──
  aiGenerateQuestion: (level, hint = '') =>
    call('POST', '/api/admin/ai/generate-question', { level, hint }),
  aiGenerateCriteria: (question, domain = '') =>
    call('POST', '/api/admin/ai/generate-criteria', { question, domain }),
  aiPolish: (text, kind = 'question') =>
    call('POST', '/api/admin/ai/polish', { text, kind }),

  // ── 분석 / 모니터링 ──
  getAnalytics: () => call('GET', '/api/admin/analytics/summary'),
  getLogs: (limit = 100) =>
    call('GET', `/api/admin/analytics/logs?limit=${limit}`),
  getActiveSessions: () => call('GET', '/api/admin/sessions/active'),

  // ── 리더보드 관리 ──
  listLeaderboard: () => call('GET', '/api/admin/leaderboard'),
  deleteEntry: (id) =>
    call('DELETE', `/api/admin/leaderboard/${encodeURIComponent(id)}`),
  clearLeaderboard: () => call('POST', '/api/admin/leaderboard/clear'),
};
