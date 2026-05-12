// frontend/src/components/preview/MarkdownPreview.tsx
// Phase 38 Plan 05-C: Modal 内 Markdown プレビュー (UI-SPEC §"MarkdownPreview" L437-441)。
// react-markdown + remark-gfm を **直接** 呼ぶ薄ラッパー — AI 応答描画用のリッチな
// コンポーネントは preview から呼ばない (Monaco code block / Mermaid 等の重い tree を
// 含むため preview には過剰 — RESEARCH.md §Pitfall 7 / UI-SPEC L437-441)
// size cap 1MB は fetch 前に attachment.size を見て弾く (AttachmentModal 側)。
// この component に到達した時点で size cap は通過済の前提。

import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownPreviewProps {
  url: string;
}

type FetchError = 'auth' | 'missing' | 'fetch';

export default function MarkdownPreview({ url }: MarkdownPreviewProps) {
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

  if (error) {
    return <ErrorBanner code={error} />;
  }
  if (text === null) {
    return <LoadingDots />;
  }
  return (
    <div
      className="attachment-modal-md"
      style={{
        padding: 'var(--space-4)',
        color: 'var(--color-text)',
        background: 'var(--color-surface)',
        fontSize: '16px',
        lineHeight: 1.5,
        overflow: 'auto',
        height: '100%',
      }}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
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
