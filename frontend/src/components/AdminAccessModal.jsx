import React, { useEffect, useRef, useState } from 'react';
import './AdminPanel.css';
import { adminApi } from '../utils/adminApi';

/**
 * AdminAccessModal - 관리자 비밀번호 입력 모달.
 * 인증 성공 시 onSuccess() 를 호출합니다.
 */
export default function AdminAccessModal({ onClose, onSuccess }) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => {
    inputRef.current?.focus();
    const handleEsc = (event) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [onClose]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!password || loading) return;
    setLoading(true);
    setError('');
    try {
      await adminApi.login(password);
      onSuccess();
    } catch (err) {
      setError(err.message || '로그인 실패');
      setPassword('');
      inputRef.current?.focus();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="admin-modal"
      role="dialog"
      aria-modal="true"
      aria-label="관리자 비밀번호 입력"
      onClick={onClose}
    >
      <div
        className="admin-modal__panel"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="admin-modal__header">
          <span className="admin-modal__icon">🔐</span>
          ADMIN ACCESS
        </div>

        <form onSubmit={handleSubmit} className="admin-modal__form">
          <label htmlFor="admin-pw" className="admin-modal__label">
            관리자 비밀번호
          </label>
          <input
            id="admin-pw"
            ref={inputRef}
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="admin-modal__input"
            placeholder="비밀번호 입력"
            disabled={loading}
            autoComplete="current-password"
          />

          {error && <div className="admin-modal__error">⚠️ {error}</div>}

          <div className="admin-modal__actions">
            <button
              type="button"
              className="admin-modal__btn"
              onClick={onClose}
              disabled={loading}
            >
              취소 (ESC)
            </button>
            <button
              type="submit"
              className="admin-modal__btn admin-modal__btn--primary"
              disabled={loading || !password}
            >
              {loading ? '확인 중...' : '확인'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
