// frontend/src/components/preview/TextPreview.tsx
// Phase 38 Plan 05-E: Modal 内 プレーンテキスト プレビュー (UI-SPEC §"MonacoPreview" L449-454)。
// Monaco read-only Editor で表示、ext から language ID にマップ。
// LANG_ALIASES は MarkdownMessage.tsx と独立に保持 (export 化は本 plan の scope 外、UI-SPEC L737-742 planner 判断)。
// size cap 1MB は fetch 前に AttachmentModal 側で弾く (この component に到達した時点で通過済)。

import { useEffect, useState } from 'react';
import Editor from '@monaco-editor/react';
import { useCurrentTheme } from '../../contexts/ThemeContext';

interface TextPreviewProps {
  url: string;
  ext: string;
}

type FetchError = 'auth' | 'missing' | 'fetch';

// ext → Monaco language ID マッピング。
// MarkdownMessage.tsx の LANG_ALIASES から複製 + Phase 38 で扱う ext 群を追加。
const LANG_ALIASES: Record<string, string> = {
  js: 'javascript',
  ts: 'typescript',
  jsx: 'javascript',
  tsx: 'typescript',
  py: 'python',
  rb: 'ruby',
  sh: 'shell',
  bash: 'shell',
  zsh: 'shell',
  yml: 'yaml',
  yaml: 'yaml',
  md: 'markdown',
  json: 'json',
  toml: 'plaintext', // Monaco 標準では toml は無いので plaintext へ縮退
  xml: 'xml',
  html: 'html',
  css: 'css',
  sql: 'sql',
  log: 'plaintext',
  txt: 'plaintext',
};

function resolveLanguage(ext: string): string {
  const e = ext.replace(/^\./, '').toLowerCase();
  return LANG_ALIASES[e] ?? e ?? 'plaintext';
}

export default function TextPreview({ url, ext }: TextPreviewProps) {
  const theme = useCurrentTheme();
  const monacoTheme = theme === 'dark' ? 'vs-dark' : 'vs';
  const language = resolveLanguage(ext);
  const [text, setText] = useState<string | null>(null);
  const [error, setError] = useState<FetchError | null>(null);

  useEffect(() => {
    let canceled = false;
    setText(null);
    setError(null);
    fetch(url, { credentials: 'include' })
      .then(async (r) => {
        if (!r.ok) {
          if (r.status === 401 || r.status === 403) throw new Error('auth');
          if (r.status === 404) throw new Error('missing');
          throw new Error('fetch');
        }
        return r.text();
      })
      .then((t) => {
        if (!canceled) setText(t);
      })
      .catch((e: Error) => {
        if (!canceled) {
          const code = (e.message || 'fetch') as FetchError;
          setError(code === 'auth' || code === 'missing' ? code : 'fetch');
        }
      });
    return () => {
      canceled = true;
    };
  }, [url]);

  if (error) return <ErrorBanner code={error} />;
  if (text === null) return <LoadingDots />;

  return (
    <div
      style={{
        height: '100%',
        width: '100%',
        border: '1px solid var(--color-border)',
      }}
    >
      <Editor
        value={text}
        language={language}
        theme={monacoTheme}
        options={{
          readOnly: true,
          minimap: { enabled: false },
          scrollBeyondLastLine: false,
          fontSize: 13,
          wordWrap: 'on',
          renderLineHighlight: 'none',
          contextmenu: false,
          automaticLayout: true,
        }}
        height="calc(90vh - 120px)"
      />
    </div>
  );
}

function LoadingDots() {
  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        display: 'flex',
        gap: 'var(--space-2)',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 'var(--space-4)',
        color: 'var(--color-text-muted)',
      }}
    >
      <span className="typing-dot" />
      <span className="typing-dot" />
      <span className="typing-dot" />
      <span style={{ marginLeft: 'var(--space-2)' }}>読み込み中...</span>
    </div>
  );
}

function ErrorBanner({ code }: { code: FetchError }) {
  const msg =
    code === 'auth'
      ? 'このファイルにはアクセスできません。再ログインしてからお試しください。'
      : code === 'missing'
        ? 'このファイルは削除されたか、ストレージから取得できません。'
        : 'ネットワークエラーで読み込めませんでした。時間を置いて再度お試しください。';
  return (
    <div
      role="alert"
      style={{
        margin: 'var(--space-4)',
        padding: 'var(--space-3) var(--space-4)',
        border: '1px solid var(--color-destructive)',
        borderRadius: 'var(--radius-md)',
        background: 'var(--color-surface)',
        color: 'var(--color-text)',
        fontSize: '14px',
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: 'var(--space-1)' }}>
        プレビューを取得できませんでした
      </div>
      <div>{msg}</div>
    </div>
  );
}
