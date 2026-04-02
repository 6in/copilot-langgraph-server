// frontend/src/components/Header.tsx
// App header: model selector (gpt-4.1 default, per D-07) + avatar + logout.
// Model list copied from static/index.html <select id="model-select">.

import { useEffect, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { getMe } from '../api/client';
import type { UserInfoResponse } from '../types';

interface HeaderProps {
  selectedModel: string;
  onModelChange: (model: string) => void;
}

// Model list from static/index.html — keep in sync if models change.
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

export function Header({ selectedModel, onModelChange }: HeaderProps) {
  const { authState, performLogout } = useAuth();
  const [user, setUser] = useState<UserInfoResponse | null>(null);

  useEffect(() => {
    if (authState === 'authenticated') {
      getMe()
        .then(setUser)
        .catch(() => setUser(null));
    } else {
      setUser(null);
    }
  }, [authState]);

  const handleLogout = async () => {
    if (window.confirm('Are you sure you want to log out?')) {
      await performLogout();
    }
  };

  return (
    <header style={{
      display: 'flex',
      alignItems: 'center',
      padding: '0 1rem',
      height: '48px',
      background: '#24292e',
      color: '#fff',
      gap: '1rem',
      flexShrink: 0,
    }}>
      <span style={{ fontWeight: 'bold', fontSize: '1rem' }}>Copilot Chat</span>

      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <label htmlFor="model-select" style={{ fontSize: '0.85rem', color: '#ccc' }}>
          Model:
        </label>
        <select
          id="model-select"
          value={selectedModel}
          onChange={(e) => onModelChange(e.target.value)}
          style={{
            padding: '0.25rem 0.5rem',
            borderRadius: '4px',
            border: 'none',
            fontSize: '0.85rem',
          }}
        >
          {MODEL_OPTIONS.map((group) => (
            <optgroup key={group.group} label={group.group}>
              {group.models.map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </optgroup>
          ))}
        </select>

        {user && (
          <>
            <img
              src={user.avatar_url}
              alt={user.login}
              title={user.name ?? user.login}
              style={{ width: '28px', height: '28px', borderRadius: '50%', border: '1px solid #444' }}
            />
            <span style={{ fontSize: '0.85rem', color: '#ccc' }}>{user.login}</span>
          </>
        )}

        {authState === 'authenticated' && (
          <button
            onClick={handleLogout}
            style={{
              padding: '0.25rem 0.75rem',
              cursor: 'pointer',
              borderRadius: '4px',
              border: '1px solid #555',
              background: 'transparent',
              color: '#ccc',
              fontSize: '0.85rem',
            }}
          >
            Logout
          </button>
        )}
      </div>
    </header>
  );
}
