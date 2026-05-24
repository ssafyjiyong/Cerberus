import React, { useEffect, useState } from 'react';
import { getSessionExemplars } from '../utils/api';

/**
 * ExemplarPanel — 모범답안 패널 (결과/게임오버 화면 공통)
 *
 * 단계별로 해당 세션의 시나리오·answer_paths·모범답안을 학습용으로 표시합니다.
 * 세션이 종료된 경우에만 백엔드가 응답합니다(미클리어 단계도 포함).
 *
 * Props:
 *   sessions: [{ level, session_id, tier? }, ...]
 *             — clearedStages 또는 그 외 종료 세션의 메타.
 */
export default function ExemplarPanel({ sessions = [] }) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState(null);
  const [error, setError] = useState(null);

  const validSessions = sessions.filter((s) => s && s.session_id);

  useEffect(() => {
    if (!open || items !== null) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all(
      validSessions.map((s) =>
        getSessionExemplars(s.session_id)
          .then((data) => ({ ...data, _stageLevel: s.level, _tier: s.tier || data.final_tier }))
          .catch((err) => ({ _stageLevel: s.level, _error: err.message || String(err) })),
      ),
    )
      .then((results) => {
        if (!cancelled) setItems(results);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, items, validSessions]);

  if (validSessions.length === 0) return null;

  return (
    <div
      style={{
        width: '100%',
        maxWidth: 720,
        margin: '0 auto',
        background: 'rgba(10,10,26,0.55)',
        border: '1px solid var(--border-purple, #4a2a6a)',
        padding: 'var(--space-md, 14px)',
      }}
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="arcade-btn arcade-btn--blue"
        style={{ width: '100%' }}
        id="btn-toggle-exemplars"
      >
        {open ? '🙈 모범답안 숨기기' : '📖 모범답안 보기'}
      </button>

      {open && (
        <div style={{ marginTop: 'var(--space-md, 14px)' }}>
          {loading && <div className="admin-empty">불러오는 중...</div>}
          {error && (
            <div style={{ color: 'var(--color-fire-red, #ff4444)' }}>
              ⚠️ {error}
            </div>
          )}
          {items &&
            items.map((it, idx) => (
              <StageExemplar key={idx} item={it} />
            ))}
        </div>
      )}
    </div>
  );
}

function StageExemplar({ item }) {
  if (item._error) {
    return (
      <div
        style={{
          background: 'rgba(40,10,10,0.5)',
          border: '1px solid var(--color-fire-red, #ff4444)',
          padding: 12,
          marginBottom: 10,
          color: 'var(--color-fire-red, #ff4444)',
          fontSize: 12,
        }}
      >
        STAGE {item._stageLevel} — 조회 실패: {item._error}
      </div>
    );
  }

  return (
    <div
      style={{
        background: 'rgba(0,0,0,0.4)',
        border: '1px solid var(--border-purple, #4a2a6a)',
        padding: 14,
        marginBottom: 12,
        textAlign: 'left',
      }}
    >
      {/* 헤더 */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 8,
          marginBottom: 8,
        }}
      >
        <div
          style={{
            fontFamily: 'var(--font-pixel)',
            fontSize: 13,
            color: 'var(--color-fire-orange, #ffae42)',
            letterSpacing: 1,
          }}
        >
          🎯 STAGE {item._stageLevel} —{' '}
          {item.isms_control_id ? `${item.isms_control_id} ` : ''}
          {item.isms_control_title || ''}
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-secondary, #aaa)' }}>
          {item._tier === 'full'
            ? '★ 만점 통과'
            : item._tier === 'half'
            ? '◇ 절반 통과'
            : '미클리어'}
        </div>
      </div>

      {/* 시나리오 */}
      {item.scenario_context && (
        <div
          style={{
            background: 'rgba(60,30,0,0.35)',
            border: '1px solid rgba(255,174,66,0.35)',
            padding: 10,
            marginBottom: 8,
            fontSize: 12,
            lineHeight: 1.6,
          }}
        >
          🎬 <strong>시나리오:</strong> {item.scenario_context}
        </div>
      )}

      {/* 질문 */}
      <div style={{ marginBottom: 10, fontSize: 13 }}>
        💬 <strong>심사원 질문:</strong> {item.auditor_question}
      </div>

      {/* 모범답안들 */}
      <div style={{ marginTop: 8 }}>
        <div
          style={{
            fontSize: 11,
            color: 'var(--color-neon-green, #00ff88)',
            letterSpacing: 1,
            marginBottom: 6,
          }}
        >
          ★ 모범답안
        </div>
        {(item.answer_paths || []).map((p) => (
          <div
            key={p.id}
            style={{
              borderLeft: `3px solid ${
                p.tier === 'full'
                  ? 'var(--color-neon-green, #00ff88)'
                  : 'var(--color-fire-orange, #ffae42)'
              }`,
              paddingLeft: 10,
              marginBottom: 10,
              fontSize: 12,
              lineHeight: 1.55,
            }}
          >
            <div
              style={{
                fontSize: 10,
                color:
                  p.tier === 'full'
                    ? 'var(--color-neon-green, #00ff88)'
                    : 'var(--color-fire-orange, #ffae42)',
                marginBottom: 4,
                letterSpacing: 1,
              }}
            >
              {p.tier === 'full' ? '★ FULL PASS' : '◇ HALF PASS'} — {p.id}
            </div>
            {p.exemplar_answer ? (
              <div style={{ color: 'var(--text-primary, #e8e8ff)' }}>
                {p.exemplar_answer}
              </div>
            ) : (
              <div style={{ color: 'var(--text-dim, #777)' }}>
                (모범답안이 등록되지 않았습니다)
              </div>
            )}
            {p.tier === 'full' && p.compensating_keywords?.length > 0 && (
              <div
                style={{
                  fontSize: 10,
                  color: 'var(--text-secondary, #aaa)',
                  marginTop: 3,
                }}
              >
                보완통제 키워드: {p.compensating_keywords.join(' · ')}
              </div>
            )}
            {p.tier === 'half' && p.acknowledgment_keywords?.length > 0 && (
              <div
                style={{
                  fontSize: 10,
                  color: 'var(--text-secondary, #aaa)',
                  marginTop: 3,
                }}
              >
                수용 키워드: {p.acknowledgment_keywords.join(' · ')}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
