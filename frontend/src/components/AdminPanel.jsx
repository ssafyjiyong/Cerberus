import React, { useEffect, useRef, useState } from 'react';
import './AdminPanel.css';
import { adminApi } from '../utils/adminApi';

// ============================================================
// AdminPanel — 관리자 페이지 (6개 탭 통합)
// ============================================================
export default function AdminPanel({ onClose }) {
  const [tab, setTab] = useState('questions');
  const [toast, setToast] = useState(null);
  const toastTimerRef = useRef(null);

  const showToast = (message, type = 'success') => {
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    setToast({ message, type });
    toastTimerRef.current = setTimeout(() => setToast(null), 3500);
  };

  const handleLogout = async () => {
    try {
      await adminApi.logout();
    } catch {
      /* ignore */
    }
    onClose();
  };

  const tabs = [
    { id: 'questions', label: '질문 관리' },
    { id: 'params', label: '게임 설정' },
    { id: 'analytics', label: '분석·로그' },
    { id: 'sessions', label: '활성 세션' },
    { id: 'leaderboard', label: '리더보드' },
    { id: 'ops', label: '운영' },
  ];

  return (
    <div className="admin-panel" role="dialog" aria-label="관리자 페이지">
      <header className="admin-panel__header">
        <span className="admin-panel__title">🛠 CERBERUS ADMIN</span>
        <span className="admin-panel__spacer" />
        <button className="admin-btn admin-btn--small" onClick={onClose}>
          닫기 ✕
        </button>
      </header>

      <nav className="admin-panel__nav">
        {tabs.map((t) => (
          <button
            key={t.id}
            className={`admin-panel__tab ${
              tab === t.id ? 'admin-panel__tab--active' : ''
            }`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <main className="admin-panel__content">
        {tab === 'questions' && <QuestionsTab showToast={showToast} />}
        {tab === 'params' && <GameParamsTab showToast={showToast} />}
        {tab === 'analytics' && <AnalyticsTab showToast={showToast} />}
        {tab === 'sessions' && <SessionsTab showToast={showToast} />}
        {tab === 'leaderboard' && <LeaderboardTab showToast={showToast} />}
        {tab === 'ops' && (
          <OpsTab showToast={showToast} onLogout={handleLogout} />
        )}
      </main>

      {toast && (
        <div
          className={`admin-toast ${
            toast.type === 'error' ? 'admin-toast--error' : ''
          }`}
        >
          {toast.message}
        </div>
      )}
    </div>
  );
}

// ============================================================
// 질문 관리 탭
// ============================================================
function QuestionsTab({ showToast }) {
  const [levels, setLevels] = useState(null);
  const [loading, setLoading] = useState(true);
  const fileInputRef = useRef(null);

  const load = async () => {
    setLoading(true);
    try {
      const cfg = await adminApi.getConfig();
      setLevels(cfg.level_configs || {});
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleSaveLevel = async (level, payload) => {
    try {
      await adminApi.updateLevel(level, payload);
      showToast(`Level ${level} 저장 완료`);
      load();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const handleExport = () => {
    if (!levels) return;
    const json = JSON.stringify(levels, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cerberus-levels-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('JSON 파일을 다운로드했습니다');
  };

  const handleImport = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      const parsed = JSON.parse(text);
      await adminApi.importLevels(parsed);
      showToast('JSON import 완료');
      await load();
    } catch (err) {
      showToast('Import 실패: ' + err.message, 'error');
    } finally {
      event.target.value = '';
    }
  };

  if (loading) return <div className="admin-empty">불러오는 중...</div>;
  if (!levels) return null;

  return (
    <div>
      <div className="admin-card">
        <h3 className="admin-card__title">JSON Import / Export</h3>
        <div className="admin-card__hint">
          현재 모든 레벨 설정을 JSON 파일로 내보내거나, 백업 파일로부터 일괄 교체할 수 있습니다.
        </div>
        <div className="admin-row-actions">
          <button
            className="admin-btn admin-btn--small"
            onClick={handleExport}
          >
            📤 JSON 내보내기
          </button>
          <button
            className="admin-btn admin-btn--small"
            onClick={() => fileInputRef.current?.click()}
          >
            📥 JSON 가져오기
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json,application/json"
            style={{ display: 'none' }}
            onChange={handleImport}
          />
        </div>
      </div>

      {[1, 2, 3].map((lv) => (
        <LevelEditor
          key={lv}
          level={lv}
          initial={levels[String(lv)] || levels[lv] || {}}
          onSave={(payload) => handleSaveLevel(lv, payload)}
          showToast={showToast}
        />
      ))}
    </div>
  );
}

function LevelEditor({ level, initial, onSave, showToast }) {
  const [domain, setDomain] = useState('');
  const [question, setQuestion] = useState('');
  const [criteria, setCriteria] = useState([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setDomain(initial.domain || '');
    setQuestion(initial.question || '');
    setCriteria([...(initial.pass_criteria || [])]);
  }, [initial]);

  const setCriterion = (i, text) => {
    const next = [...criteria];
    next[i] = text;
    setCriteria(next);
  };
  const addCriterion = () => setCriteria([...criteria, '']);
  const removeCriterion = (i) =>
    setCriteria(criteria.filter((_, idx) => idx !== i));

  const handleSave = async () => {
    if (
      !domain.trim() ||
      !question.trim() ||
      criteria.length === 0 ||
      criteria.some((c) => !c.trim())
    ) {
      showToast('모든 필드를 채우세요 (빈 기준 불가)', 'error');
      return;
    }
    setBusy(true);
    try {
      await onSave({
        domain: domain.trim(),
        question: question.trim(),
        pass_criteria: criteria.map((c) => c.trim()),
      });
    } finally {
      setBusy(false);
    }
  };

  const aiGenerateQuestion = async () => {
    setBusy(true);
    try {
      const data = await adminApi.aiGenerateQuestion(level, domain);
      setQuestion(data.question);
      showToast('AI가 새 질문을 생성했습니다');
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setBusy(false);
    }
  };

  const aiPolishQuestion = async () => {
    if (!question.trim()) return;
    setBusy(true);
    try {
      const data = await adminApi.aiPolish(question, 'question');
      setQuestion(data.text);
      showToast('AI가 질문을 다듬었습니다');
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setBusy(false);
    }
  };

  const aiGenerateCriteria = async () => {
    if (!question.trim()) {
      showToast('먼저 질문을 입력하세요', 'error');
      return;
    }
    setBusy(true);
    try {
      const data = await adminApi.aiGenerateCriteria(question, domain);
      if (Array.isArray(data.criteria) && data.criteria.length > 0) {
        setCriteria(data.criteria);
        showToast(`AI 통과 기준 ${data.criteria.length}개 생성 완료`);
      } else {
        showToast('AI 응답이 비어 있습니다', 'error');
      }
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setBusy(false);
    }
  };

  const aiPolishCriterion = async (i) => {
    const text = criteria[i];
    if (!text || !text.trim()) return;
    setBusy(true);
    try {
      const data = await adminApi.aiPolish(text, 'criterion');
      const next = [...criteria];
      next[i] = data.text;
      setCriteria(next);
      showToast('AI가 기준을 다듬었습니다');
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="admin-card">
      <h3 className="admin-card__title">
        Level {level} {domain && `— ${domain}`}
      </h3>

      <div className="admin-card__row">
        <label className="admin-card__label">심사 영역 (Domain)</label>
        <input
          className="admin-input"
          value={domain}
          onChange={(e) => setDomain(e.target.value)}
          disabled={busy}
        />
      </div>

      <div className="admin-card__row">
        <label className="admin-card__label">심사 질문 (Question)</label>
        <textarea
          className="admin-textarea"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          disabled={busy}
          rows={2}
        />
        <div className="admin-row-actions">
          <button
            className="admin-btn admin-btn--ai admin-btn--small"
            onClick={aiGenerateQuestion}
            disabled={busy}
          >
            🤖 AI 생성
          </button>
          <button
            className="admin-btn admin-btn--ai admin-btn--small"
            onClick={aiPolishQuestion}
            disabled={busy || !question.trim()}
          >
            ✨ AI 다듬기
          </button>
        </div>
      </div>

      <div className="admin-card__row">
        <label className="admin-card__label">통과 기준 (Pass Criteria)</label>
        {criteria.map((c, i) => (
          <div key={i} className="admin-criterion-row">
            <span className="admin-criterion-row__index">{i + 1}.</span>
            <input
              className="admin-input"
              value={c}
              onChange={(e) => setCriterion(i, e.target.value)}
              disabled={busy}
            />
            <button
              className="admin-btn admin-btn--ai admin-btn--small"
              onClick={() => aiPolishCriterion(i)}
              disabled={busy || !c.trim()}
              title="이 기준만 AI로 다듬기"
            >
              ✨
            </button>
            <button
              className="admin-criterion-row__del"
              onClick={() => removeCriterion(i)}
              disabled={busy}
              title="기준 삭제"
            >
              ✕
            </button>
          </div>
        ))}
        <div className="admin-row-actions">
          <button
            className="admin-btn admin-btn--small"
            onClick={addCriterion}
            disabled={busy}
          >
            + 기준 추가
          </button>
          <button
            className="admin-btn admin-btn--ai admin-btn--small"
            onClick={aiGenerateCriteria}
            disabled={busy || !question.trim()}
          >
            🤖 AI 기준 3개 생성
          </button>
        </div>
      </div>

      <div className="admin-row-actions" style={{ marginTop: 'var(--space-md)' }}>
        <button
          className="admin-btn admin-btn--primary"
          onClick={handleSave}
          disabled={busy}
        >
          💾 저장
        </button>
      </div>
    </div>
  );
}

// ============================================================
// 게임 설정 탭
// ============================================================
function GameParamsTab({ showToast }) {
  const [params, setParams] = useState(null);
  const [edited, setEdited] = useState({});
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      const cfg = await adminApi.getConfig();
      const p = cfg.game_params || {};
      setParams(p);
      setEdited(p);
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  useEffect(() => {
    load();
  }, []);

  if (!params) return <div className="admin-empty">불러오는 중...</div>;

  const change = (k, v) => setEdited({ ...edited, [k]: v });

  const handleSave = async () => {
    setBusy(true);
    try {
      const updates = {};
      for (const k of ['TIME_LIMIT', 'P_MAX', 'W_TIME', 'W_PROMPT']) {
        const v = parseInt(edited[k], 10);
        if (Number.isFinite(v)) updates[k] = v;
      }
      if (edited.BEDROCK_MODEL_ID)
        updates.BEDROCK_MODEL_ID = String(edited.BEDROCK_MODEL_ID).trim();
      await adminApi.updateGameParams(updates);
      showToast('게임 파라미터 저장 완료');
      await load();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="admin-card">
      <h3 className="admin-card__title">게임 파라미터</h3>
      <div className="admin-warning">
        ⓘ 변경 내용은 <b>새로 시작하는 게임 세션부터</b> 적용됩니다. 진행 중 세션은 영향받지 않습니다.
      </div>

      <div className="admin-card__row">
        <label className="admin-card__label">TIME_LIMIT — 제한 시간(초)</label>
        <input
          type="number"
          min="30"
          max="3600"
          className="admin-input"
          value={edited.TIME_LIMIT ?? ''}
          onChange={(e) => change('TIME_LIMIT', e.target.value)}
          disabled={busy}
        />
        <span className="admin-card__hint">예: 300 (5분 타임어택)</span>
      </div>

      <div className="admin-card__row">
        <label className="admin-card__label">P_MAX — 최대 답변 횟수</label>
        <input
          type="number"
          min="1"
          max="100"
          className="admin-input"
          value={edited.P_MAX ?? ''}
          onChange={(e) => change('P_MAX', e.target.value)}
          disabled={busy}
        />
        <span className="admin-card__hint">예: 15 (이 횟수를 넘기면 게임 오버)</span>
      </div>

      <div className="admin-card__row">
        <label className="admin-card__label">W_TIME — 시간 가중치</label>
        <input
          type="number"
          min="0"
          className="admin-input"
          value={edited.W_TIME ?? ''}
          onChange={(e) => change('W_TIME', e.target.value)}
          disabled={busy}
        />
        <span className="admin-card__hint">점수 = (남은 시간) × W_TIME + (남은 답변 수) × W_PROMPT</span>
      </div>

      <div className="admin-card__row">
        <label className="admin-card__label">W_PROMPT — 답변 횟수 가중치</label>
        <input
          type="number"
          min="0"
          className="admin-input"
          value={edited.W_PROMPT ?? ''}
          onChange={(e) => change('W_PROMPT', e.target.value)}
          disabled={busy}
        />
      </div>

      <div className="admin-card__row">
        <label className="admin-card__label">BEDROCK_MODEL_ID — AI 모델</label>
        <input
          className="admin-input"
          value={edited.BEDROCK_MODEL_ID ?? ''}
          onChange={(e) => change('BEDROCK_MODEL_ID', e.target.value)}
          disabled={busy}
        />
        <span className="admin-card__hint">
          예: anthropic.claude-3-haiku-20240307-v1:0 — 변경 후 해당 모델의 Bedrock 액세스가 활성화되어 있어야 합니다.
        </span>
      </div>

      <div className="admin-row-actions">
        <button
          className="admin-btn admin-btn--primary"
          onClick={handleSave}
          disabled={busy}
        >
          💾 저장
        </button>
      </div>
    </div>
  );
}

// ============================================================
// 분석·로그 탭
// ============================================================
function AnalyticsTab({ showToast }) {
  const [summary, setSummary] = useState(null);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [s, l] = await Promise.all([
        adminApi.getAnalytics(),
        adminApi.getLogs(100),
      ]);
      setSummary(s);
      setLogs(l.logs || []);
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  if (loading) return <div className="admin-empty">불러오는 중...</div>;

  return (
    <div>
      <div className="admin-card">
        <h3 className="admin-card__title">분석 요약</h3>
        <div className="admin-stat-grid">
          <div className="admin-stat">
            <div className="admin-stat__label">전체 세션</div>
            <div className="admin-stat__value">
              {summary?.total_sessions ?? 0}
            </div>
          </div>
          <div className="admin-stat">
            <div className="admin-stat__label">전체 채팅</div>
            <div className="admin-stat__value">
              {summary?.total_interactions ?? 0}
            </div>
          </div>
          <div className="admin-stat">
            <div className="admin-stat__label">게임 클리어율</div>
            <div className="admin-stat__value">
              {summary?.clear_rate ?? 0}%
            </div>
          </div>
        </div>

        {[1, 2, 3].map((lv) => {
          const data =
            summary?.levels?.[lv] || summary?.levels?.[String(lv)] || null;
          if (!data) {
            return (
              <div
                key={lv}
                className="admin-empty"
                style={{ padding: 'var(--space-sm)' }}
              >
                Level {lv}: 아직 데이터 없음
              </div>
            );
          }
          return (
            <div
              key={lv}
              style={{
                marginTop: 'var(--space-md)',
                paddingTop: 'var(--space-md)',
                borderTop: '1px dashed var(--admin-border)',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: 'var(--space-sm)',
                  alignItems: 'center',
                  marginBottom: 'var(--space-sm)',
                }}
              >
                <strong style={{ color: 'var(--color-fire-orange)' }}>
                  Level {lv} — {data.domain}
                </strong>
                <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                  도달 {data.reached_sessions} · 클리어 {data.cleared_sessions} (
                  {data.clear_rate}%) · 평균 시도 {data.avg_attempts_to_clear ?? '-'}
                  회
                </span>
              </div>
              {data.weak_criteria?.length > 0 ? (
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>취약 기준</th>
                      <th>실패 횟수</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.weak_criteria.map((wc) => (
                      <tr key={wc.index}>
                        <td>{wc.index}</td>
                        <td>{wc.criterion}</td>
                        <td>{wc.fail_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div
                  className="admin-empty"
                  style={{ padding: 'var(--space-sm)' }}
                >
                  실패 데이터 없음
                </div>
              )}
            </div>
          );
        })}

        <div className="admin-row-actions" style={{ marginTop: 'var(--space-md)' }}>
          <button className="admin-btn admin-btn--small" onClick={load}>
            🔄 새로고침
          </button>
        </div>
      </div>

      <div className="admin-card">
        <h3 className="admin-card__title">최근 게임 로그 ({logs.length}건)</h3>
        {logs.length === 0 ? (
          <div className="admin-empty">로그가 아직 없습니다.</div>
        ) : (
          <div style={{ maxHeight: 480, overflow: 'auto' }}>
            <table className="admin-table">
              <thead>
                <tr>
                  <th>시각</th>
                  <th>세션</th>
                  <th>L</th>
                  <th>시도</th>
                  <th>상태</th>
                  <th>누락</th>
                  <th>사용자 답변</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log, i) => (
                  <tr key={`${log.session_id}-${log.log_id || i}`}>
                    <td className="col-mono">
                      {(log.created_at || '').slice(0, 19).replace('T', ' ')}
                    </td>
                    <td className="col-mono">
                      {(log.session_id || '').slice(0, 8)}
                    </td>
                    <td>{log.log_id === 'SUMMARY' ? '–' : log.level}</td>
                    <td>{log.log_id === 'SUMMARY' ? '–' : log.level_attempt}</td>
                    <td
                      style={{
                        color:
                          log.ai_status === 'pass'
                            ? 'var(--color-neon-green)'
                            : log.ai_status === 'fail'
                            ? 'var(--color-fire-red)'
                            : 'var(--text-dim)',
                      }}
                    >
                      {log.ai_status}
                    </td>
                    <td>
                      {Array.isArray(log.missing_criteria)
                        ? log.missing_criteria.join(',')
                        : ''}
                    </td>
                    <td
                      style={{
                        maxWidth: 360,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                      title={log.user_message}
                    >
                      {log.user_message}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================
// 활성 세션 탭 (라이브 모니터링)
// ============================================================
function SessionsTab({ showToast }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const d = await adminApi.getActiveSessions();
        if (!cancelled) setData(d);
      } catch (err) {
        if (!cancelled) showToast(err.message, 'error');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    const id = setInterval(load, 5000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  if (loading) return <div className="admin-empty">불러오는 중...</div>;

  return (
    <div className="admin-card">
      <h3 className="admin-card__title">활성 세션 (5초마다 자동 갱신)</h3>
      <div className="admin-stat-grid">
        <div className="admin-stat">
          <div className="admin-stat__label">현재 진행 중</div>
          <div className="admin-stat__value">{data?.count ?? 0}</div>
        </div>
        {[1, 2, 3].map((lv) => (
          <div key={lv} className="admin-stat">
            <div className="admin-stat__label">Level {lv}</div>
            <div className="admin-stat__value">
              {data?.by_level?.[lv] || data?.by_level?.[String(lv)] || 0}
            </div>
          </div>
        ))}
      </div>

      {data?.sessions?.length > 0 ? (
        <table className="admin-table">
          <thead>
            <tr>
              <th>세션 ID</th>
              <th>레벨</th>
              <th>답변 수</th>
              <th>경과(초)</th>
              <th>제한(초)</th>
              <th>시작 시각 (UTC)</th>
            </tr>
          </thead>
          <tbody>
            {data.sessions.map((s) => (
              <tr key={s.session_id}>
                <td className="col-mono">{s.session_id.slice(0, 12)}…</td>
                <td>{s.current_level}</td>
                <td>{s.prompt_count}</td>
                <td>{s.time_used}</td>
                <td>{s.time_limit}</td>
                <td className="col-mono">
                  {(s.started_at || '').replace('T', ' ').replace('Z', '')}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div className="admin-empty">현재 진행 중인 게임이 없습니다.</div>
      )}
    </div>
  );
}

// ============================================================
// 리더보드 관리 탭
// ============================================================
function LeaderboardTab({ showToast }) {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const d = await adminApi.listLeaderboard();
      setEntries(d.entries || []);
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleDelete = async (id) => {
    if (!id) return;
    if (!window.confirm('이 항목을 삭제할까요?')) return;
    try {
      await adminApi.deleteEntry(id);
      showToast('삭제됨');
      load();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const handleClear = async () => {
    if (!window.confirm('리더보드 전체를 초기화합니다. 정말 진행할까요?'))
      return;
    try {
      const r = await adminApi.clearLeaderboard();
      showToast(`${r.deleted_count}개 항목 제거됨`);
      load();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  if (loading) return <div className="admin-empty">불러오는 중...</div>;

  return (
    <div className="admin-card">
      <h3 className="admin-card__title">
        리더보드 관리 ({entries.length}개 항목)
      </h3>
      <div className="admin-row-actions" style={{ marginBottom: 'var(--space-md)' }}>
        <button className="admin-btn admin-btn--small" onClick={load}>
          🔄 새로고침
        </button>
        <button
          className="admin-btn admin-btn--danger admin-btn--small"
          onClick={handleClear}
          disabled={entries.length === 0}
        >
          🗑 전체 초기화
        </button>
      </div>

      {entries.length === 0 ? (
        <div className="admin-empty">등록된 항목이 없습니다.</div>
      ) : (
        <table className="admin-table">
          <thead>
            <tr>
              <th>이름</th>
              <th>점수</th>
              <th>시간</th>
              <th>등록일</th>
              <th>ID</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {entries.map((e) => (
              <tr key={e.id || `${e.name}-${e.created_at}`}>
                <td>{e.name}</td>
                <td>{e.score}</td>
                <td>{e.time_used}초</td>
                <td className="col-mono">
                  {(e.created_at || '').slice(0, 19).replace('T', ' ')}
                </td>
                <td className="col-mono">
                  {e.id ? e.id.slice(0, 8) : '(mock)'}
                </td>
                <td>
                  <button
                    className="admin-criterion-row__del"
                    onClick={() => handleDelete(e.id)}
                    disabled={!e.id}
                  >
                    삭제
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

// ============================================================
// 운영 탭 (유지보수 모드 / 기본값 복원 / 비밀번호 변경 / 로그아웃)
// ============================================================
function OpsTab({ showToast, onLogout }) {
  const [maintMode, setMaintMode] = useState(false);
  const [resetWithPw, setResetWithPw] = useState(false);
  const [currentPw, setCurrentPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [newPw2, setNewPw2] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const cfg = await adminApi.getConfig();
        setMaintMode(!!cfg.maintenance_mode);
      } catch (err) {
        showToast(err.message, 'error');
      }
    })();
  }, []);

  const toggleMaintenance = async () => {
    if (busy) return;
    const next = !maintMode;
    setBusy(true);
    try {
      await adminApi.setMaintenance(next);
      setMaintMode(next);
      showToast(
        next ? '유지보수 모드 ON — 신규 게임 차단됨' : '유지보수 모드 OFF'
      );
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setBusy(false);
    }
  };

  const handleReset = async () => {
    const confirmed = window.confirm(
      resetWithPw
        ? '모든 설정과 관리자 비밀번호를 코드 기본값으로 되돌립니다. 재로그인이 필요합니다. 계속할까요?'
        : '레벨 설정과 게임 파라미터를 코드 기본값으로 되돌립니다 (비밀번호는 유지). 계속할까요?'
    );
    if (!confirmed) return;
    setBusy(true);
    try {
      const r = await adminApi.resetDefaults(resetWithPw);
      showToast(r.message || '기본값 복원 완료');
      if (resetWithPw) onLogout();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setBusy(false);
    }
  };

  const handleChangePw = async (event) => {
    event.preventDefault();
    if (newPw !== newPw2) {
      showToast('새 비밀번호가 일치하지 않습니다', 'error');
      return;
    }
    if (newPw.length < 4) {
      showToast('새 비밀번호는 4자 이상이어야 합니다', 'error');
      return;
    }
    setBusy(true);
    try {
      await adminApi.changePassword(currentPw, newPw);
      showToast('비밀번호가 변경되었습니다. 다시 로그인하세요.');
      onLogout();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <div className="admin-card">
        <h3 className="admin-card__title">유지보수 모드</h3>
        <div className="admin-warning">
          ⓘ 켜져 있으면 <b>신규 게임 시작이 차단</b>됩니다 (진행 중 세션은 그대로 진행). 점검·배포 시 사용하세요.
        </div>
        <div
          onClick={toggleMaintenance}
          className={`admin-toggle ${maintMode ? 'admin-toggle--on' : ''}`}
          role="switch"
          aria-checked={maintMode}
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              toggleMaintenance();
            }
          }}
        >
          <div className="admin-toggle__track">
            <div className="admin-toggle__thumb" />
          </div>
          <span className="admin-toggle__label">
            {maintMode ? '점검 중 (신규 게임 차단)' : '정상 운영 중'}
          </span>
        </div>
      </div>

      <div className="admin-card">
        <h3 className="admin-card__title">기본값으로 복원</h3>
        <div className="admin-warning">
          ⚠ 레벨 설정과 게임 파라미터를 모두 코드 기본값으로 되돌립니다.
        </div>
        <label
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-sm)',
            margin: 'var(--space-md) 0',
            cursor: 'pointer',
            fontSize: 12,
          }}
        >
          <input
            type="checkbox"
            checked={resetWithPw}
            onChange={(e) => setResetWithPw(e.target.checked)}
            disabled={busy}
          />
          관리자 비밀번호도 <code>mzcadmin</code> 으로 초기화
        </label>
        <button
          className="admin-btn admin-btn--danger admin-btn--small"
          onClick={handleReset}
          disabled={busy}
        >
          🔄 기본값으로 복원
        </button>
      </div>

      <div className="admin-card">
        <h3 className="admin-card__title">관리자 비밀번호 변경</h3>
        <form onSubmit={handleChangePw}>
          <div className="admin-card__row">
            <label className="admin-card__label">현재 비밀번호</label>
            <input
              type="password"
              className="admin-input"
              value={currentPw}
              onChange={(e) => setCurrentPw(e.target.value)}
              disabled={busy}
              autoComplete="current-password"
            />
          </div>
          <div className="admin-card__row">
            <label className="admin-card__label">새 비밀번호 (4자 이상)</label>
            <input
              type="password"
              className="admin-input"
              value={newPw}
              onChange={(e) => setNewPw(e.target.value)}
              disabled={busy}
              autoComplete="new-password"
            />
          </div>
          <div className="admin-card__row">
            <label className="admin-card__label">새 비밀번호 확인</label>
            <input
              type="password"
              className="admin-input"
              value={newPw2}
              onChange={(e) => setNewPw2(e.target.value)}
              disabled={busy}
              autoComplete="new-password"
            />
          </div>
          <button
            type="submit"
            className="admin-btn admin-btn--primary admin-btn--small"
            disabled={busy || !currentPw || !newPw || !newPw2}
          >
            비밀번호 변경
          </button>
        </form>
      </div>

      <div className="admin-card">
        <h3 className="admin-card__title">세션</h3>
        <button className="admin-btn admin-btn--small" onClick={onLogout}>
          🚪 로그아웃
        </button>
      </div>
    </div>
  );
}
