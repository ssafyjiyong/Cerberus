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
// 질문 관리 탭 (v2 — 풀 기반)
// ============================================================
function QuestionsTab({ showToast }) {
  const [stages, setStages] = useState(null);
  const [loading, setLoading] = useState(true);
  const fileInputRef = useRef(null);

  const load = async () => {
    setLoading(true);
    try {
      const cfg = await adminApi.getConfig();
      setStages(cfg.level_configs || {});
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleExport = () => {
    if (!stages) return;
    const json = JSON.stringify(stages, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cerberus-stages-${Date.now()}.json`;
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
  if (!stages) return null;

  return (
    <div>
      <div className="admin-card">
        <h3 className="admin-card__title">JSON Import / Export</h3>
        <div className="admin-card__hint">
          모든 스테이지 설정과 질문 풀을 JSON 으로 백업/복원할 수 있습니다.
        </div>
        <div className="admin-row-actions">
          <button className="admin-btn admin-btn--small" onClick={handleExport}>
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

      {[1, 2, 3].map((stage) => (
        <StageQuestionPool
          key={stage}
          stage={stage}
          stageData={stages[String(stage)] || stages[stage] || {}}
          showToast={showToast}
          onChanged={load}
        />
      ))}
    </div>
  );
}

// ─── 스테이지 = 메타 + 질문 풀 (목록 + CRUD) ───
function StageQuestionPool({ stage, stageData, showToast, onChanged }) {
  const [meta, setMeta] = useState({
    title: '',
    subtitle: '',
    time_limit: '',
    p_max: '',
    base_score: '',
  });
  const [busy, setBusy] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    setMeta({
      title: stageData.title || '',
      subtitle: stageData.subtitle || '',
      time_limit: stageData.time_limit ? String(stageData.time_limit) : '',
      p_max: stageData.p_max ? String(stageData.p_max) : '',
      base_score: stageData.base_score ? String(stageData.base_score) : '',
    });
  }, [stageData]);

  const questions = Array.isArray(stageData.questions) ? stageData.questions : [];

  const saveMeta = async () => {
    const tl = meta.time_limit === '' ? 0 : parseInt(meta.time_limit, 10);
    const pm = meta.p_max === '' ? 0 : parseInt(meta.p_max, 10);
    const bs = meta.base_score === '' ? 0 : parseInt(meta.base_score, 10);
    if (!Number.isFinite(tl) || tl < 0 || tl > 3600) {
      showToast('time_limit 은 0~3600 사이여야 합니다.', 'error');
      return;
    }
    if (!Number.isFinite(pm) || pm < 0 || pm > 100) {
      showToast('p_max 는 0~100 사이여야 합니다.', 'error');
      return;
    }
    if (!Number.isFinite(bs) || bs < 0) {
      showToast('base_score 가 올바르지 않습니다.', 'error');
      return;
    }
    setBusy(true);
    try {
      await adminApi.updateStageMeta(stage, {
        title: meta.title.trim() || undefined,
        subtitle: meta.subtitle.trim() || undefined,
        time_limit: tl,
        p_max: pm,
        base_score: bs,
      });
      showToast(`Stage ${stage} 메타 저장 완료`);
      onChanged();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (qid) => {
    if (questions.length <= 1) {
      showToast('스테이지에 질문이 최소 1개는 있어야 합니다.', 'error');
      return;
    }
    if (!window.confirm('이 질문을 삭제할까요?')) return;
    try {
      await adminApi.deleteQuestion(stage, qid);
      showToast('삭제 완료');
      onChanged();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  return (
    <div className="admin-card">
      <h3 className="admin-card__title">
        Stage {stage} — {stageData.title || '(제목 없음)'}
      </h3>

      {/* ── 메타 편집 ── */}
      <div
        className="admin-card__row"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: 'var(--space-md)',
        }}
      >
        <div>
          <label className="admin-card__label">제목 (Title)</label>
          <input
            className="admin-input"
            value={meta.title}
            onChange={(e) => setMeta({ ...meta, title: e.target.value })}
            disabled={busy}
          />
        </div>
        <div>
          <label className="admin-card__label">부제 (Subtitle)</label>
          <input
            className="admin-input"
            value={meta.subtitle}
            onChange={(e) => setMeta({ ...meta, subtitle: e.target.value })}
            disabled={busy}
          />
        </div>
        <div>
          <label className="admin-card__label">제한 시간 (초)</label>
          <input
            type="number"
            min="0"
            max="3600"
            className="admin-input"
            placeholder="0 = 전역값 사용"
            value={meta.time_limit}
            onChange={(e) => setMeta({ ...meta, time_limit: e.target.value })}
            disabled={busy}
          />
        </div>
        <div>
          <label className="admin-card__label">최대 답변 (P_MAX)</label>
          <input
            type="number"
            min="0"
            max="100"
            className="admin-input"
            placeholder="0 = 전역값 사용"
            value={meta.p_max}
            onChange={(e) => setMeta({ ...meta, p_max: e.target.value })}
            disabled={busy}
          />
        </div>
        <div>
          <label className="admin-card__label">만점 기준 (Base Score)</label>
          <input
            type="number"
            min="0"
            className="admin-input"
            value={meta.base_score}
            onChange={(e) => setMeta({ ...meta, base_score: e.target.value })}
            disabled={busy}
          />
          <span className="admin-card__hint">half 통과 시 ×0.5</span>
        </div>
      </div>
      <div className="admin-row-actions" style={{ marginTop: 'var(--space-md)' }}>
        <button
          className="admin-btn admin-btn--primary admin-btn--small"
          onClick={saveMeta}
          disabled={busy}
        >
          💾 메타 저장
        </button>
      </div>

      {/* ── 질문 목록 ── */}
      <div
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
            alignItems: 'center',
            marginBottom: 'var(--space-sm)',
          }}
        >
          <strong style={{ color: 'var(--color-fire-orange)' }}>
            질문 풀 ({questions.length}건) — 세션 시작 시 랜덤 1문제 출제
          </strong>
          <button
            className="admin-btn admin-btn--small"
            onClick={() => {
              setEditingId(null);
              setCreating(true);
            }}
            disabled={busy || creating || editingId !== null}
          >
            + 질문 추가
          </button>
        </div>

        {questions.length === 0 && !creating && (
          <div className="admin-empty">질문이 없습니다. 추가해 주세요.</div>
        )}

        {questions.map((q) =>
          editingId === q.id ? (
            <QuestionEditor
              key={q.id}
              stage={stage}
              initial={q}
              onCancel={() => setEditingId(null)}
              onSaved={() => {
                setEditingId(null);
                onChanged();
              }}
              showToast={showToast}
            />
          ) : (
            <div
              key={q.id}
              style={{
                background: 'rgba(10,10,26,0.5)',
                border: '1px solid var(--admin-border)',
                padding: 'var(--space-md)',
                marginBottom: 'var(--space-sm)',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  gap: 'var(--space-sm)',
                  flexWrap: 'wrap',
                }}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div
                    style={{
                      fontFamily: 'var(--font-pixel)',
                      fontSize: 11,
                      color: 'var(--color-fire-orange)',
                      marginBottom: 4,
                    }}
                  >
                    {q.isms_control_id || '(ID 없음)'} {q.isms_control_title || ''}
                  </div>
                  <div style={{ fontSize: 13, marginBottom: 6 }}>
                    💬 {q.auditor_question}
                  </div>
                  <div
                    style={{
                      fontSize: 11,
                      color: 'var(--text-secondary)',
                      marginBottom: 6,
                    }}
                  >
                    🎬 {(q.scenario_context || '').slice(0, 120)}
                    {(q.scenario_context || '').length > 120 ? '...' : ''}
                  </div>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {(q.answer_paths || []).map((p) => (
                      <span
                        key={p.id}
                        style={{
                          fontSize: 10,
                          padding: '2px 6px',
                          background:
                            p.tier === 'full'
                              ? 'rgba(0, 255, 136, 0.15)'
                              : 'rgba(255, 174, 66, 0.15)',
                          color:
                            p.tier === 'full'
                              ? 'var(--color-neon-green)'
                              : 'var(--color-fire-orange)',
                          border: '1px solid currentColor',
                        }}
                        title={p.description || ''}
                      >
                        {p.tier} · {p.id}
                      </span>
                    ))}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 4, alignItems: 'flex-start' }}>
                  <button
                    className="admin-btn admin-btn--small"
                    onClick={() => {
                      setCreating(false);
                      setEditingId(q.id);
                    }}
                    disabled={busy || creating || editingId !== null}
                  >
                    ✏️ 편집
                  </button>
                  <button
                    className="admin-criterion-row__del"
                    onClick={() => handleDelete(q.id)}
                    disabled={busy || questions.length <= 1}
                    title={
                      questions.length <= 1
                        ? '풀에 최소 1개 질문이 필요합니다'
                        : '삭제'
                    }
                  >
                    ✕
                  </button>
                </div>
              </div>
            </div>
          ),
        )}

        {creating && (
          <QuestionEditor
            stage={stage}
            initial={null}
            onCancel={() => setCreating(false)}
            onSaved={() => {
              setCreating(false);
              onChanged();
            }}
            showToast={showToast}
          />
        )}
      </div>
    </div>
  );
}

// ─── 질문 1건 편집 폼 (신규/수정 공용) ───
function QuestionEditor({ stage, initial, onCancel, onSaved, showToast }) {
  const isNew = !initial;
  const [ismsId, setIsmsId] = useState('');
  const [ismsTitle, setIsmsTitle] = useState('');
  const [scenario, setScenario] = useState('');
  const [question, setQuestion] = useState('');
  const [defaultRebuttal, setDefaultRebuttal] = useState('');
  const [paths, setPaths] = useState([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setIsmsId(initial?.isms_control_id || '');
    setIsmsTitle(initial?.isms_control_title || '');
    setScenario(initial?.scenario_context || '');
    setQuestion(initial?.auditor_question || '');
    setDefaultRebuttal(initial?.default_rebuttal || '');
    setPaths(
      Array.isArray(initial?.answer_paths)
        ? initial.answer_paths.map((p) => ({ ...p }))
        : [],
    );
  }, [initial]);

  const updatePath = (idx, patch) => {
    setPaths((prev) => prev.map((p, i) => (i === idx ? { ...p, ...patch } : p)));
  };

  const addPath = (tier) => {
    setPaths((prev) => [
      ...prev,
      {
        id: `${tier}-${Date.now().toString(36)}`,
        tier,
        description: '',
        trigger_keywords: [],
        exemplar_answer: '',
        ...(tier === 'half'
          ? { rebuttal: '', acknowledgment_keywords: [] }
          : { follow_up: '', compensating_keywords: [] }),
      },
    ]);
  };

  const removePath = (idx) => {
    setPaths((prev) => prev.filter((_, i) => i !== idx));
  };

  const aiGenerateScenario = async () => {
    if (!ismsId && !ismsTitle) {
      showToast('ISMS-P 항목 ID 또는 제목을 먼저 입력하세요', 'error');
      return;
    }
    setBusy(true);
    try {
      const data = await adminApi.aiGenerateScenario(ismsId, ismsTitle);
      setScenario(data.scenario);
      showToast('AI 시나리오 생성 완료');
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setBusy(false);
    }
  };

  const aiGenerateQuestion = async () => {
    if (!scenario.trim()) {
      showToast('시나리오를 먼저 입력하세요', 'error');
      return;
    }
    setBusy(true);
    try {
      const data = await adminApi.aiGenerateAuditorQuestion(scenario, ismsTitle);
      setQuestion(data.question);
      showToast('AI 질문 생성 완료');
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setBusy(false);
    }
  };

  const aiGeneratePaths = async () => {
    if (!scenario.trim() || !question.trim()) {
      showToast('시나리오와 질문을 먼저 입력하세요', 'error');
      return;
    }
    setBusy(true);
    try {
      const data = await adminApi.aiGenerateAnswerPaths(scenario, question, ismsTitle);
      if (Array.isArray(data.answer_paths) && data.answer_paths.length > 0) {
        setPaths(data.answer_paths);
        showToast(`AI answer_paths ${data.answer_paths.length}개 생성 완료`);
      } else {
        showToast('AI 응답이 비어 있습니다', 'error');
      }
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setBusy(false);
    }
  };

  const handleSave = async () => {
    if (!question.trim()) {
      showToast('심사 질문은 필수입니다', 'error');
      return;
    }
    if (paths.length === 0) {
      showToast('answer_paths 가 최소 1개 이상 필요합니다', 'error');
      return;
    }
    const payload = {
      isms_control_id: ismsId.trim(),
      isms_control_title: ismsTitle.trim(),
      scenario_context: scenario.trim(),
      auditor_question: question.trim(),
      default_rebuttal: defaultRebuttal.trim(),
      answer_paths: paths.map((p) => ({
        id: p.id || `${p.tier}-${Date.now().toString(36)}`,
        tier: p.tier,
        description: p.description || '',
        trigger_keywords: Array.isArray(p.trigger_keywords)
          ? p.trigger_keywords
          : String(p.trigger_keywords || '')
              .split(',')
              .map((s) => s.trim())
              .filter(Boolean),
        rebuttal: p.rebuttal || '',
        acknowledgment_keywords: Array.isArray(p.acknowledgment_keywords)
          ? p.acknowledgment_keywords
          : String(p.acknowledgment_keywords || '')
              .split(',')
              .map((s) => s.trim())
              .filter(Boolean),
        follow_up: p.follow_up || '',
        compensating_keywords: Array.isArray(p.compensating_keywords)
          ? p.compensating_keywords
          : String(p.compensating_keywords || '')
              .split(',')
              .map((s) => s.trim())
              .filter(Boolean),
        exemplar_answer: p.exemplar_answer || '',
      })),
    };

    setBusy(true);
    try {
      if (isNew) {
        await adminApi.addQuestion(stage, payload);
        showToast('질문 추가 완료');
      } else {
        await adminApi.updateQuestion(stage, initial.id, payload);
        showToast('질문 저장 완료');
      }
      onSaved();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      style={{
        background: 'rgba(20,10,30,0.6)',
        border: '1px solid var(--color-fire-orange)',
        padding: 'var(--space-md)',
        marginBottom: 'var(--space-sm)',
      }}
    >
      <div
        style={{
          fontFamily: 'var(--font-pixel)',
          fontSize: 13,
          color: 'var(--color-fire-orange)',
          marginBottom: 'var(--space-sm)',
        }}
      >
        {isNew ? '+ 새 질문 추가' : `✏️ 질문 편집 — ${initial?.id}`}
      </div>

      <div
        className="admin-card__row"
        style={{
          display: 'grid',
          gridTemplateColumns: '120px 1fr',
          gap: 'var(--space-sm)',
        }}
      >
        <div>
          <label className="admin-card__label">ISMS-P ID</label>
          <input
            className="admin-input"
            value={ismsId}
            onChange={(e) => setIsmsId(e.target.value)}
            placeholder="2.6.2"
            disabled={busy}
          />
        </div>
        <div>
          <label className="admin-card__label">ISMS-P 항목 이름</label>
          <input
            className="admin-input"
            value={ismsTitle}
            onChange={(e) => setIsmsTitle(e.target.value)}
            placeholder="정보시스템 접근"
            disabled={busy}
          />
        </div>
      </div>

      <div className="admin-card__row">
        <label className="admin-card__label">시나리오 컨텍스트</label>
        <textarea
          className="admin-textarea"
          value={scenario}
          onChange={(e) => setScenario(e.target.value)}
          disabled={busy}
          rows={3}
          placeholder="(왜 이게 심사 지적이 되었는지의 상황 설명. 한 문단)"
        />
        <div className="admin-row-actions">
          <button
            className="admin-btn admin-btn--ai admin-btn--small"
            onClick={aiGenerateScenario}
            disabled={busy}
          >
            🤖 AI 시나리오 생성
          </button>
        </div>
      </div>

      <div className="admin-card__row">
        <label className="admin-card__label">심사원 질문 (한 줄)</label>
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
            disabled={busy || !scenario.trim()}
          >
            🤖 AI 질문 생성
          </button>
        </div>
      </div>

      <div className="admin-card__row">
        <label className="admin-card__label">기본 반박 멘트 (어떤 경로에도 안 걸릴 때)</label>
        <input
          className="admin-input"
          value={defaultRebuttal}
          onChange={(e) => setDefaultRebuttal(e.target.value)}
          placeholder="근거가 부족합니다.."
          disabled={busy}
        />
      </div>

      {/* answer_paths */}
      <div
        style={{
          marginTop: 'var(--space-md)',
          paddingTop: 'var(--space-sm)',
          borderTop: '1px dashed var(--admin-border)',
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            marginBottom: 'var(--space-sm)',
          }}
        >
          <strong style={{ color: 'var(--color-fire-orange)' }}>
            Answer Paths ({paths.length})
          </strong>
          <div style={{ display: 'flex', gap: 4 }}>
            <button
              className="admin-btn admin-btn--small"
              onClick={() => addPath('half')}
              disabled={busy}
            >
              + half 경로
            </button>
            <button
              className="admin-btn admin-btn--small"
              onClick={() => addPath('full')}
              disabled={busy}
            >
              + full 경로
            </button>
            <button
              className="admin-btn admin-btn--ai admin-btn--small"
              onClick={aiGeneratePaths}
              disabled={busy || !scenario.trim() || !question.trim()}
            >
              🤖 AI 경로 2개 생성
            </button>
          </div>
        </div>

        {paths.map((p, idx) => (
          <AnswerPathEditor
            key={idx}
            path={p}
            onChange={(patch) => updatePath(idx, patch)}
            onRemove={() => removePath(idx)}
            disabled={busy}
          />
        ))}
      </div>

      <div className="admin-row-actions" style={{ marginTop: 'var(--space-md)' }}>
        <button
          className="admin-btn admin-btn--primary"
          onClick={handleSave}
          disabled={busy}
        >
          💾 저장
        </button>
        <button className="admin-btn admin-btn--small" onClick={onCancel} disabled={busy}>
          취소
        </button>
      </div>
    </div>
  );
}

// ─── answer_path 1건 편집 폼 ───
function AnswerPathEditor({ path, onChange, onRemove, disabled }) {
  const isHalf = path.tier === 'half';
  const isFull = path.tier === 'full';

  const kwToString = (kws) =>
    Array.isArray(kws) ? kws.join(', ') : String(kws || '');

  return (
    <div
      style={{
        background: 'rgba(0,0,0,0.35)',
        border: `1px solid ${
          isFull
            ? 'var(--color-neon-green, #00ff88)'
            : isHalf
            ? 'var(--color-fire-orange, #ffae42)'
            : 'var(--admin-border)'
        }`,
        padding: 'var(--space-sm)',
        marginBottom: 'var(--space-sm)',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          gap: 'var(--space-sm)',
          marginBottom: 6,
        }}
      >
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <select
            className="admin-input"
            style={{ width: 90 }}
            value={path.tier}
            onChange={(e) => onChange({ tier: e.target.value })}
            disabled={disabled}
          >
            <option value="full">full</option>
            <option value="half">half</option>
          </select>
          <input
            className="admin-input"
            style={{ width: 200 }}
            value={path.id || ''}
            onChange={(e) => onChange({ id: e.target.value })}
            placeholder="path id (예: full-api-sync)"
            disabled={disabled}
          />
        </div>
        <button
          className="admin-criterion-row__del"
          onClick={onRemove}
          disabled={disabled}
        >
          ✕
        </button>
      </div>

      <div className="admin-card__row">
        <label className="admin-card__label">설명</label>
        <input
          className="admin-input"
          value={path.description || ''}
          onChange={(e) => onChange({ description: e.target.value })}
          disabled={disabled}
        />
      </div>

      <div className="admin-card__row">
        <label className="admin-card__label">
          Trigger Keywords (쉼표로 구분)
        </label>
        <input
          className="admin-input"
          value={kwToString(path.trigger_keywords)}
          onChange={(e) =>
            onChange({
              trigger_keywords: e.target.value
                .split(',')
                .map((s) => s.trim())
                .filter(Boolean),
            })
          }
          placeholder="패치, 패키지 업데이트"
          disabled={disabled}
        />
      </div>

      {isHalf && (
        <>
          <div className="admin-card__row">
            <label className="admin-card__label">Rebuttal (반박 멘트)</label>
            <textarea
              className="admin-textarea"
              rows={2}
              value={path.rebuttal || ''}
              onChange={(e) => onChange({ rebuttal: e.target.value })}
              disabled={disabled}
            />
          </div>
          <div className="admin-card__row">
            <label className="admin-card__label">
              Acknowledgment Keywords (쉼표) — 1개 이상 충족 시 half 확정
            </label>
            <input
              className="admin-input"
              value={kwToString(path.acknowledgment_keywords)}
              onChange={(e) =>
                onChange({
                  acknowledgment_keywords: e.target.value
                    .split(',')
                    .map((s) => s.trim())
                    .filter(Boolean),
                })
              }
              placeholder="반영, 검토하겠습니다, 개선"
              disabled={disabled}
            />
          </div>
        </>
      )}

      {isFull && (
        <>
          <div className="admin-card__row">
            <label className="admin-card__label">Follow-up (후속 질문)</label>
            <textarea
              className="admin-textarea"
              rows={2}
              value={path.follow_up || ''}
              onChange={(e) => onChange({ follow_up: e.target.value })}
              disabled={disabled}
            />
          </div>
          <div className="admin-card__row">
            <label className="admin-card__label">
              Compensating Keywords (쉼표) — 모두 충족해야 full 확정
            </label>
            <input
              className="admin-input"
              value={kwToString(path.compensating_keywords)}
              onChange={(e) =>
                onChange({
                  compensating_keywords: e.target.value
                    .split(',')
                    .map((s) => s.trim())
                    .filter(Boolean),
                })
              }
              placeholder="위험평가, 경영진 승인"
              disabled={disabled}
            />
          </div>
        </>
      )}

      {/* 모든 tier 공통 — 모범답안 */}
      <div className="admin-card__row">
        <label className="admin-card__label">
          ★ 모범답안 (Exemplar Answer) — 결과 화면에서 학습용으로 노출됨
        </label>
        <textarea
          className="admin-textarea"
          rows={3}
          value={path.exemplar_answer || ''}
          onChange={(e) => onChange({ exemplar_answer: e.target.value })}
          disabled={disabled}
          placeholder="이 경로로 통과하는 모범 답변(1~3문장). 키워드와 보완통제를 자연스럽게 포함."
        />
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
