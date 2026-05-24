/**
 * 점수 유틸리티
 *
 * ⚠️ 단계별 독립 세션 모델에서 점수 계산은 **백엔드 권위(authoritative)** 입니다.
 * 프론트엔드는 백엔드가 돌려준 단계별 score 를 합산해 표시만 합니다.
 * 이 파일은 등급 계산 / 시간 포맷터 같은 표시용 헬퍼만 제공합니다.
 */

// 기본 한도 (타이머 초기값 등 화면 폴백 용도로만 사용)
const TIME_LIMIT = 300;
const P_MAX = 10;
const W_TIME = 1;
const W_PROMPT = 10;

/**
 * 초를 MM:SS 형식으로 변환
 */
export function formatTime(seconds) {
  const total = Math.max(0, Math.round(seconds));
  const mins = Math.floor(total / 60);
  const secs = total % 60;
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

/**
 * 합산 점수 기준 등급
 * 3 단계 합산이므로 임계치는 단일 단계 시절보다 높게 설정.
 */
export function getGrade(score) {
  if (score >= 900) return 'S';
  if (score >= 700) return 'A';
  if (score >= 500) return 'B';
  if (score >= 300) return 'C';
  return 'D';
}

export const GAME_CONFIG = {
  TIME_LIMIT,
  P_MAX,
  W_TIME,
  W_PROMPT,
};

// ─── KST 시간 포맷터 ───────────────────────────────
// 백엔드는 ISO 8601(+09:00) 또는 과거 데이터의 경우 'Z'(UTC) 로 보내올 수 있습니다.
// 두 경우 모두 안전하게 한국 시간으로 변환해 표시합니다.

const _kstFormatter = new Intl.DateTimeFormat('ko-KR', {
  timeZone: 'Asia/Seoul',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false,
});

/**
 * ISO 문자열 → "YYYY-MM-DD HH:MM:SS" (KST) 로 변환.
 * 잘못된 입력은 원본 문자열을 그대로 반환합니다.
 */
export function formatKst(isoString) {
  if (!isoString) return '';
  const d = new Date(isoString);
  if (Number.isNaN(d.getTime())) return String(isoString);
  // Intl 출력은 '2026. 05. 25. 14:30:00' 처럼 점/공백이 섞이므로 일관된 포맷으로 정리.
  const parts = _kstFormatter.formatToParts(d);
  const get = (type) => parts.find((p) => p.type === type)?.value || '';
  return `${get('year')}-${get('month')}-${get('day')} ${get('hour')}:${get('minute')}:${get('second')}`;
}

/**
 * 짧은 형식 — "MM-DD HH:MM"
 */
export function formatKstShort(isoString) {
  const full = formatKst(isoString);
  if (!full) return '';
  // "YYYY-MM-DD HH:MM:SS" → "MM-DD HH:MM"
  const m = full.match(/^\d{4}-(\d{2}-\d{2}) (\d{2}:\d{2}):\d{2}$/);
  return m ? `${m[1]} ${m[2]}` : full;
}
