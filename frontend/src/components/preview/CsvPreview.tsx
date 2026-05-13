// frontend/src/components/preview/CsvPreview.tsx
// Phase 38 Plan 05-D: Modal 内 CSV プレビュー (UI-SPEC §"CsvPreview" L443-447)。
// fetch text → 簡易 CSV パース → MarkdownTableData 形 → ChatAgGridTable 流用。
// papaparse 不要 (RESEARCH.md §Standard Stack §6)。
// 行数 1000 行 cap、超過時は preview 上部にバナー表示。
// size cap 1MB は fetch 前に AttachmentModal 側で弾く (この component に到達した時点で通過済)。

import { lazy, Suspense, useEffect, useState } from 'react';
import { useCurrentTheme } from '../../contexts/ThemeContext';
import type { MarkdownTableData } from '../../utils/markdownTable';

// ChatAgGridTable は ~400KB の lazy bundle (MarkdownMessage.tsx と同じ pattern)
const ChatAgGridTable = lazy(() => import('../ChatAgGridTable'));

interface CsvPreviewProps {
  url: string;
}

type FetchError = 'auth' | 'missing' | 'fetch';

const MAX_PREVIEW_ROWS = 1000;

// 簡易 CSV パース:
// - "..."  で囲まれたフィールドは内側 "" を " にエスケープ
// - quote 内の `,` / 改行は保持
// - quote 外の `,` のみセパレータとして扱う
// papaparse 等の重量級ライブラリ不要 (RESEARCH §6)。
function parseCsv(text: string): { data: MarkdownTableData; totalRows: number } {
  const allRows: string[][] = [];
  let field = '';
  let row: string[] = [];
  let inQuotes = false;
  let i = 0;
  const n = text.length;
  while (i < n) {
    const ch = text[i];
    if (inQuotes) {
      if (ch === '"') {
        if (i + 1 < n && text[i + 1] === '"') {
          field += '"';
          i += 2;
          continue;
        }
        inQuotes = false;
        i++;
        continue;
      }
      field += ch;
      i++;
      continue;
    }
    // not in quotes
    if (ch === '"') {
      inQuotes = true;
      i++;
      continue;
    }
    if (ch === ',') {
      row.push(field);
      field = '';
      i++;
      continue;
    }
    if (ch === '\r') {
      // skip — CRLF を LF と同等に扱う
      i++;
      continue;
    }
    if (ch === '\n') {
      row.push(field);
      field = '';
      // 空行は skip (末尾改行のみは無視)
      if (row.length > 1 || (row.length === 1 && row[0] !== '')) {
        allRows.push(row);
      }
      row = [];
      i++;
      continue;
    }
    field += ch;
    i++;
  }
  // 最終フィールド (改行なしで終わった場合)
  if (field !== '' || row.length > 0) {
    row.push(field);
    if (row.length > 1 || (row.length === 1 && row[0] !== '')) {
      allRows.push(row);
    }
  }

  if (allRows.length === 0) return { data: { headers: [], rows: [] }, totalRows: 0 };
  const headers = allRows[0];
  const dataRows = allRows.slice(1);
  const truncated = dataRows.slice(0, MAX_PREVIEW_ROWS);
  return {
    data: { headers, rows: truncated },
    totalRows: dataRows.length,
  };
}

export default function CsvPreview({ url }: CsvPreviewProps) {
  const theme = useCurrentTheme();
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

  let parsed: { data: MarkdownTableData; totalRows: number };
  try {
    parsed = parseCsv(text);
  } catch {
    return <DecodeError />;
  }

  const truncated = parsed.totalRows > MAX_PREVIEW_ROWS;

  return (
    <div
      style={{
        padding: 'var(--space-3)',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-2)',
        height: '100%',
        overflow: 'auto',
      }}
    >
      {truncated && (
        <div
          role="status"
          style={{
            padding: 'var(--space-2) var(--space-3)',
            borderRadius: 'var(--radius-md)',
            background: 'var(--color-accent-subtle)',
            color: 'var(--color-text)',
            fontSize: '14px',
          }}
        >
          先頭 {MAX_PREVIEW_ROWS} 行のみ表示しています（全 {parsed.totalRows} 行）。全データはダウンロードしてください。
        </div>
      )}
      <Suspense fallback={<LoadingDots />}>
        <ChatAgGridTable data={parsed.data} theme={theme} />
      </Suspense>
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

function DecodeError() {
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
        プレビューを表示できませんでした
      </div>
      <div>CSV の解析に失敗しました。ダウンロードして開いてください。</div>
    </div>
  );
}
