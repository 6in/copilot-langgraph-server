// frontend/src/components/Header.tsx
// App header: model selector (gpt-4.1 default, per D-07) + avatar + logout.
// Phase 36 D-16: useModels hook で /api/models を fetch し、vision 対応モデルに 🖼 を付ける。
// API 失敗時 (apiModels === null) は MODEL_OPTIONS ハードコード fallback を使う。

import { useEffect, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { getMe } from '../api/client';
import { useModels } from '../hooks/useModels';
import { ConfirmModal } from './ConfirmModal';
import type { ModelInfo, UserInfoResponse } from '../types';

interface HeaderProps {
  selectedModel: string;
  onModelChange: (model: string) => void;
  theme: 'light' | 'dark';
  onToggleTheme: () => void;
  onBackToMenu?: () => void;
  appName?: string;
}

// Available Copilot models and their display labels.
const MODEL_OPTIONS = [
  { group: 'Claude', models: [
    { value: 'claude-sonnet-4.5', label: 'Claude Sonnet 4.5 (1x)' },
    { value: 'claude-sonnet-4.6', label: 'Claude Sonnet 4.6 (1x)' },
    { value: 'claude-haiku-4.5', label: 'Claude Haiku 4.5 (0.33x)' },
    { value: 'claude-opus-4.5', label: 'Claude Opus 4.5 (3x)' },
    { value: 'claude-opus-4.6', label: 'Claude Opus 4.6 (3x)' },
    { value: 'claude-opus-4.6-fast', label: 'Claude Opus 4.6 fast (30x)' },
    { value: 'claude-sonnet-4', label: 'Claude Sonnet 4 (1x)' },
  ]},
  { group: 'GPT', models: [
    { value: 'gpt-5.4', label: 'GPT-5.4 (1x)' },
    { value: 'gpt-5.3-codex', label: 'GPT-5.3-Codex (1x)' },
    { value: 'gpt-5.2-codex', label: 'GPT-5.2-Codex (1x)' },
    { value: 'gpt-5.2', label: 'GPT-5.2 (1x)' },
    { value: 'gpt-5.1-codex-max', label: 'GPT-5.1-Codex-Max (1x)' },
    { value: 'gpt-5.1-codex', label: 'GPT-5.1-Codex (1x)' },
    { value: 'gpt-5.1', label: 'GPT-5.1 (1x)' },
    { value: 'gpt-5.4-mini', label: 'GPT-5.4 mini (0.33x)' },
    { value: 'gpt-5.1-codex-mini', label: 'GPT-5.1-Codex-Mini (0.33x)' },
    { value: 'gpt-5-mini', label: 'GPT-5 mini (free)' },
    { value: 'gpt-4.1', label: 'GPT-4.1 (free)' },
  ]},
];

export function Header({ selectedModel, onModelChange, theme, onToggleTheme, onBackToMenu, appName }: HeaderProps) {
  const { authState, performLogout } = useAuth();
  const [user, setUser] = useState<UserInfoResponse | null>(null);
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);

  // Phase 36 D-16: API 由来のモデル一覧 (未取得時は null → fallback MODEL_OPTIONS を使う)
  const { models: apiModels } = useModels();
  const useApiModels = apiModels !== null && apiModels.length > 0;

  useEffect(() => {
    if (authState === 'authenticated') {
      getMe()
        .then(setUser)
        .catch(() => setUser(null));
    } else {
      setUser(null);
    }
  }, [authState]);

  const handleLogout = () => {
    setShowLogoutConfirm(true);
  };

  return (
    <header style={{
      display: 'flex',
      alignItems: 'center',
      padding: '0 var(--space-4)',
      height: '48px',
      background: 'var(--color-header-bg)',
      color: 'var(--color-header-text)',
      gap: 'var(--space-4)',
      flexShrink: 0,
      borderBottom: '1px solid var(--color-border)',
      position: 'relative',
    }}>
      {onBackToMenu && (
        <button
          onClick={onBackToMenu}
          style={{
            padding: '0.25rem 0.75rem',
            cursor: 'pointer',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--color-border)',
            background: 'transparent',
            color: 'var(--color-header-text)',
            fontSize: '0.85rem',
            flexShrink: 0,
          }}
        >
          ‹ メニュー
        </button>
      )}
      <span style={{
        fontFamily: "'Rajdhani', sans-serif",
        fontWeight: 700,
        fontSize: '1.25rem',
        letterSpacing: '0.08em',
        background: 'var(--gradient-title)',
        WebkitBackgroundClip: 'text',
        WebkitTextFillColor: 'transparent',
        backgroundClip: 'text',
      }}>Orochi Chat</span>
      {appName && (
        <span style={{
          fontSize: '0.85rem',
          fontWeight: 400,
          color: 'var(--color-text-muted)',
          marginLeft: '0.5rem',
          maxWidth: '160px',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}>
          &middot; {appName}
        </span>
      )}

      <div className="header-desktop-actions" style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <label htmlFor="model-select" className="header-model-label" style={{ fontSize: '0.85rem', color: 'var(--color-header-text)' }}>
          モデル:
        </label>
        <select
          id="model-select"
          value={selectedModel}
          aria-label={_buildModelAriaLabel(selectedModel, apiModels)}
          onChange={(e) => onModelChange(e.target.value)}
          style={{
            padding: '0.25rem 0.5rem',
            borderRadius: 'var(--radius-sm)',
            border: 'none',
            fontSize: '0.85rem',
          }}
        >
          {useApiModels ? (
            // Phase 36 D-16: API 由来。vision 対応モデルには 🖼 を付ける。
            apiModels!.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}{m.vision ? ' 🖼' : ''}
              </option>
            ))
          ) : (
            // Fallback: API 未取得 / 失敗時はハードコード (Phase 35 までの動作と同じ)
            MODEL_OPTIONS.map((group) => (
              <optgroup key={group.group} label={group.group}>
                {group.models.map((m) => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </optgroup>
            ))
          )}
        </select>

        {user && (
          <>
            <img
              src={user.avatar_url}
              alt={user.login}
              title={user.name ?? user.login}
              style={{ width: '28px', height: '28px', borderRadius: '50%', border: '1px solid var(--color-border)' }}
            />
            <span className="header-user-login" style={{ fontSize: '0.85rem', color: 'var(--color-header-text)' }}>{user.login}</span>
          </>
        )}

        {authState === 'authenticated' && (
          <button
            onClick={handleLogout}
            style={{
              padding: '0.25rem 0.75rem',
              cursor: 'pointer',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--color-border)',
              background: 'transparent',
              color: 'var(--color-header-text)',
              fontSize: '0.85rem',
            }}
          >
            ログアウト
          </button>
        )}

        <button
          onClick={onToggleTheme}
          title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          aria-label="ライトモード / ダークモードを切り替え"
          style={{
            background: 'transparent',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-md)',
            color: 'var(--color-header-text)',
            cursor: 'pointer',
            fontSize: '16px',
            lineHeight: 1,
            padding: '4px 8px',
            flexShrink: 0,
          }}
        >
          {theme === 'dark' ? '☀️' : '🌙'}
        </button>
      </div>

      {/* hamburger menu: display 制御は Plan 06 の @media で行う (desktop では display: none) */}
      <details className="header-hamburger" style={{ position: 'relative', marginLeft: 'auto' }}>
        <summary
          aria-label="メニューを開く"
          style={{
            listStyle: 'none',
            cursor: 'pointer',
            padding: 'var(--space-1) var(--space-2)',
            fontSize: '1.25rem',
            color: 'var(--color-header-text)',
          }}
        >
          ☰
        </summary>
        <div
          role="menu"
          style={{
            position: 'absolute',
            right: 0,
            top: '100%',
            background: 'var(--color-surface)',
            color: 'var(--color-text)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-md)',
            padding: 'var(--space-2)',
            minWidth: '200px',
            zIndex: 40,
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-1)',
            marginTop: 'var(--space-1)',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
          }}
        >
          {/* Phase 35: Logout / Theme toggle を縦に並べる。Plan 06 で display 制御。Mobile 幅 (≤767px) でのみ表示。 */}
          {authState === 'authenticated' && (
            <button
              role="menuitem"
              onClick={handleLogout}
              style={{
                padding: 'var(--space-2)',
                background: 'transparent',
                border: 'none',
                color: 'var(--color-text)',
                cursor: 'pointer',
                textAlign: 'left',
                borderRadius: 'var(--radius-sm)',
              }}
            >
              ログアウト
            </button>
          )}
          <button
            role="menuitem"
            onClick={onToggleTheme}
            aria-label="ライトモード / ダークモードを切り替え"
            style={{
              padding: 'var(--space-2)',
              background: 'transparent',
              border: 'none',
              color: 'var(--color-text)',
              cursor: 'pointer',
              textAlign: 'left',
              borderRadius: 'var(--radius-sm)',
            }}
          >
            {theme === 'dark' ? '☀️ ライトモード' : '🌙 ダークモード'}
          </button>
        </div>
      </details>

      <ConfirmModal
        isOpen={showLogoutConfirm}
        message="ログアウトしますか？"
        confirmLabel="ログアウト"
        isDark={theme === 'dark'}
        onConfirm={async () => {
          setShowLogoutConfirm(false);
          await performLogout();
        }}
        onCancel={() => setShowLogoutConfirm(false)}
      />
    </header>
  );
}

// Phase 36 D-16: aria-label を「モデル選択（現在: {name}、画像対応/非対応）」形式で生成。
// API 未取得時は静的ラベルにフォールバック。
function _buildModelAriaLabel(currentId: string, models: ModelInfo[] | null): string {
  if (!models) return 'モデル選択';
  const m = models.find((x) => x.id === currentId);
  if (!m) return 'モデル選択';
  const visionPart = m.vision ? '、画像対応' : '、画像非対応';
  return `モデル選択（現在: ${m.name}${visionPart}）`;
}
