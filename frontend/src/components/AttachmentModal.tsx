// frontend/src/components/AttachmentModal.tsx
// Phase 38 Plan 05-A: 添付ファイル / AI 生成ファイル モーダルプレビュー本体。
//
// 仕様: UI-SPEC §"AttachmentModal" + RESEARCH §Pitfall 7 + PATTERNS.md §"Plan 05-A"
// - createPortal で document.body に dialog を mount
// - role="dialog" + aria-modal="true"、Esc / overlay click / × ボタンで close
// - Tab で focus trap を循環
// - Body scroll lock (document.body.style.overflow = 'hidden')
// - 4 種 renderer (image / markdown / csv / text) + unsupported フォールバック
// - kind ベースの URL 解決: kind === 'generated' → /outputs/、それ以外 → /attachments/
// - size cap: image 10MB / text 系 1MB を fetch 前に attachment.size でガード
//
// 新規 npm パッケージゼロ、新規 CSS 変数ゼロ (UI-SPEC Checker #1 / #2)。

import { lazy, Suspense, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import type { AttachmentMeta } from '../types';

// Lazy import で初期バンドルを圧縮 (react.lazy + Suspense パターン)。
const ImagePreview = lazy(() => import('./preview/ImagePreview'));
const MarkdownPreview = lazy(() => import('./preview/MarkdownPreview'));
const CsvPreview = lazy(() => import('./preview/CsvPreview'));
const TextPreview = lazy(() => import('./preview/TextPreview'));

const IMAGE_CAP_BYTES = 10 * 1024 * 1024; // 10MB (UI-SPEC L272-273)
const TEXT_CAP_BYTES = 1024 * 1024; // 1MB (text/markdown/csv 共通)

const API_BASE = (import.meta.env.VITE_APP_BASE ?? '').replace(/\/$/, '');

interface AttachmentModalProps {
  threadId: string;
  attachment: AttachmentMeta;
  open: boolean;
  onClose: () => void;
}

type PreviewKind = 'image' | 'markdown' | 'csv' | 'text' | 'unsupported';

// kind ベースの URL 切替 (UI-SPEC L485-494 / CONTEXT.md D-05)
// kind === 'generated' → /api/threads/{tid}/outputs/{name}
// kind === 'user_upload' → /api/threads/{tid}/attachments/{storage_name}
export function buildFileUrl(
  threadId: string,
  name: string,
  kind: 'user_upload' | 'generated',
): string {
  const segment = kind === 'generated' ? 'outputs' : 'attachments';
  return `${API_BASE}/api/threads/${encodeURIComponent(threadId)}/${segment}/${encodeURIComponent(name)}`;
}

// ext → PreviewKind (UI-SPEC L418-428)。
// PDF / HTML / その他は 'unsupported'。
export function classify(ext: string): PreviewKind {
  const e = ext.replace(/^\./, '').toLowerCase();
  if (['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(e)) return 'image';
  if (e === 'md' || e === 'markdown') return 'markdown';
  if (e === 'csv' || e === 'tsv') return 'csv';
  if (
    [
      'txt',
      'log',
      'py',
      'js',
      'ts',
      'tsx',
      'jsx',
      'json',
      'yaml',
      'yml',
      'toml',
      'sh',
      'sql',
      'xml',
      'css',
    ].includes(e)
  ) {
    return 'text';
  }
  return 'unsupported';
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function formatTimestamp(modifiedAt: string | undefined): string {
  if (!modifiedAt) return '';
  // modified_at は ISO string or epoch number string。両対応で防御。
  try {
    const d = new Date(modifiedAt);
    if (Number.isNaN(d.getTime())) return modifiedAt;
    return d.toLocaleString('ja-JP', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return modifiedAt;
  }
}

export function AttachmentModal({
  threadId,
  attachment,
  open,
  onClose,
}: AttachmentModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeBtnRef = useRef<HTMLButtonElement>(null);
  const downloadBtnRef = useRef<HTMLAnchorElement>(null);

  // Esc キーで close + body scroll lock
  useEffect(() => {
    if (!open) return;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      } else if (e.key === 'Tab') {
        // Tab で focus trap を循環 (UI-SPEC L471)
        const root = dialogRef.current;
        if (!root) return;
        const focusables = root.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"]), input, textarea, select',
        );
        if (focusables.length === 0) return;
        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        const active = document.activeElement as HTMLElement | null;
        if (e.shiftKey) {
          if (active === first || !root.contains(active)) {
            e.preventDefault();
            last.focus();
          }
        } else {
          if (active === last || !root.contains(active)) {
            e.preventDefault();
            first.focus();
          }
        }
      }
    };
    window.addEventListener('keydown', onKey);
    // 初回 mount で「ダウンロード」CTA に focus (UI-SPEC L472)
    const focusTimer = window.setTimeout(() => {
      downloadBtnRef.current?.focus();
    }, 0);
    return () => {
      window.removeEventListener('keydown', onKey);
      window.clearTimeout(focusTimer);
      document.body.style.overflow = prevOverflow;
    };
  }, [open, onClose]);

  if (!open) return null;

  const kind = attachment.kind;
  // user_upload の identity は storage_name、generated は name (D-05)
  const identityName = kind === 'generated' ? attachment.name : attachment.storage_name || attachment.name;
  const url = buildFileUrl(threadId, identityName, kind);
  const previewKind = classify(attachment.ext);

  // Size cap 判定 — fetch 前に弾く
  const cap =
    previewKind === 'image' ? IMAGE_CAP_BYTES : previewKind === 'unsupported' ? Infinity : TEXT_CAP_BYTES;
  const overSize = attachment.size > cap;

  const kindLabel = kind === 'generated' ? '✨ AI 生成' : '📎 添付';
  const sizeStr = formatSize(attachment.size);
  const tsStr = formatTimestamp(attachment.modified_at);

  return createPortal(
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`${attachment.name} のプレビュー`}
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0, 0, 0, 0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 100,
        padding: 'var(--space-4)',
      }}
    >
      <div
        ref={dialogRef}
        onClick={(e) => e.stopPropagation()}
        style={{
          background: 'var(--color-surface-elevated)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-lg)',
          maxWidth: 'min(1024px, 90vw)',
          width: '100%',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <header
          style={{
            padding: 'var(--space-4)',
            borderBottom: '1px solid var(--color-border)',
            display: 'flex',
            gap: 'var(--space-3)',
            alignItems: 'center',
            flexShrink: 0,
          }}
        >
          <div style={{ flex: 1, minWidth: 0 }}>
            <div
              style={{
                fontSize: '14px',
                fontWeight: 600,
                color: 'var(--color-text)',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}
              title={attachment.name}
            >
              {attachment.name}
            </div>
            <div
              style={{
                fontSize: '12px',
                color: 'var(--color-text-muted)',
                marginTop: 2,
              }}
            >
              {kindLabel} ・ {sizeStr}
              {tsStr ? ` ・ ${tsStr}` : ''}
            </div>
          </div>
          <div
            style={{
              display: 'flex',
              gap: 'var(--space-3)',
              alignItems: 'center',
              flexShrink: 0,
            }}
          >
            <a
              ref={downloadBtnRef}
              className="attachment-modal-download-btn"
              href={url}
              download={attachment.name}
              aria-label={`${attachment.name} をダウンロード`}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                padding: '6px 16px',
                minHeight: 36,
                minWidth: 120,
                justifyContent: 'center',
                borderRadius: 'var(--radius-md)',
                background: 'var(--color-accent)',
                color: 'var(--color-accent-contrast)',
                fontSize: '14px',
                fontWeight: 600,
                textDecoration: 'none',
                cursor: 'pointer',
              }}
            >
              ダウンロード
            </a>
            <button
              ref={closeBtnRef}
              type="button"
              onClick={onClose}
              aria-label="プレビューを閉じる"
              title="閉じる (Esc)"
              style={{
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                color: 'var(--color-text-muted)',
                fontSize: 24,
                lineHeight: 1,
                width: 36,
                height: 36,
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                borderRadius: 'var(--radius-md)',
              }}
            >
              ×
            </button>
          </div>
        </header>

        {/* Body */}
        <div
          style={{
            flex: 1,
            minHeight: 0,
            overflow: 'auto',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {overSize ? (
            <SizeCapBanner
              previewKind={previewKind}
              size={sizeStr}
              cap={previewKind === 'image' ? '10 MB' : '1 MB'}
              downloadUrl={url}
              filename={attachment.name}
            />
          ) : previewKind === 'unsupported' ? (
            <UnsupportedBanner
              ext={attachment.ext}
              kind={kind}
              downloadUrl={url}
              filename={attachment.name}
            />
          ) : (
            <Suspense fallback={<LoadingDots />}>
              {(() => {
                switch (previewKind) {
                  case 'image':
                    return (
                      <div
                        style={{
                          flex: 1,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          padding: 'var(--space-2)',
                          minHeight: 0,
                          overflow: 'auto',
                        }}
                      >
                        <ImagePreview url={url} alt={attachment.name} />
                      </div>
                    );
                  case 'markdown':
                    return <MarkdownPreview url={url} />;
                  case 'csv':
                    return <CsvPreview url={url} />;
                  case 'text':
                    return <TextPreview url={url} ext={attachment.ext} />;
                  default:
                    return null;
                }
              })()}
            </Suspense>
          )}
        </div>
      </div>
    </div>,
    document.body,
  );
}

export default AttachmentModal;

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

function SizeCapBanner({
  previewKind,
  size,
  cap,
  downloadUrl,
  filename,
}: {
  previewKind: PreviewKind;
  size: string;
  cap: string;
  downloadUrl: string;
  filename: string;
}) {
  const heading =
    previewKind === 'image' ? '画像が大きすぎてプレビューできません' : 'ファイルが大きすぎてプレビューできません';
  const body =
    previewKind === 'image'
      ? `この画像は ${size} あります（プレビュー上限 ${cap}）。ダウンロードして開いてください。`
      : `このファイルは ${size} あります（プレビュー上限 ${cap}）。ダウンロードして開いてください。`;
  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        margin: 'var(--space-4)',
        padding: 'var(--space-3) var(--space-4)',
        background: 'var(--color-accent-subtle)',
        borderRadius: 'var(--radius-md)',
        color: 'var(--color-text)',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-2)',
      }}
    >
      <div style={{ fontSize: '14px', fontWeight: 600 }}>{heading}</div>
      <div style={{ fontSize: '14px' }}>{body}</div>
      <div>
        <a
          href={downloadUrl}
          download={filename}
          aria-label={`${filename} をダウンロード`}
          style={{
            display: 'inline-flex',
            padding: '4px 14px',
            borderRadius: 'var(--radius-md)',
            background: 'var(--color-accent)',
            color: 'var(--color-accent-contrast)',
            fontSize: '14px',
            fontWeight: 600,
            textDecoration: 'none',
            cursor: 'pointer',
          }}
        >
          ダウンロード
        </a>
      </div>
    </div>
  );
}

function UnsupportedBanner({
  ext,
  kind,
  downloadUrl,
  filename,
}: {
  ext: string;
  kind: 'user_upload' | 'generated';
  downloadUrl: string;
  filename: string;
}) {
  const cleanExt = ext.replace(/^\./, '').toUpperCase() || '不明な';
  const heading = 'この形式はプレビューできません';
  const sourceLabel = kind === 'generated' ? 'AI が生成しました' : '添付されました';
  const body = `${cleanExt} 形式はプレビュー非対応です（${sourceLabel}）。ダウンロードして閲覧してください。`;
  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        margin: 'var(--space-4)',
        padding: 'var(--space-3) var(--space-4)',
        background: 'var(--color-accent-subtle)',
        borderRadius: 'var(--radius-md)',
        color: 'var(--color-text)',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-2)',
      }}
    >
      <div style={{ fontSize: '14px', fontWeight: 600 }}>{heading}</div>
      <div style={{ fontSize: '14px' }}>{body}</div>
      <div>
        <a
          href={downloadUrl}
          download={filename}
          aria-label={`${filename} をダウンロード`}
          style={{
            display: 'inline-flex',
            padding: '4px 14px',
            borderRadius: 'var(--radius-md)',
            background: 'var(--color-accent)',
            color: 'var(--color-accent-contrast)',
            fontSize: '14px',
            fontWeight: 600,
            textDecoration: 'none',
            cursor: 'pointer',
          }}
        >
          ダウンロード
        </a>
      </div>
    </div>
  );
}
