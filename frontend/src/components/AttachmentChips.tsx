// frontend/src/components/AttachmentChips.tsx
// Phase 36 D-05: staging chip 描画 (画像 48×48 サムネ / text pill / × 削除 / uploading spinner / error)

import type { StagingItem } from '../hooks/useAttachments';

const API_BASE = (import.meta.env.VITE_APP_BASE ?? '').replace(/\/$/, '');
const IMAGE_EXTS = new Set(['png', 'jpg', 'jpeg', 'webp']);
const THUMB_SIZE = 48;

interface AttachmentChipsProps {
  items: StagingItem[];
  onRemove: (localId: string) => void;
}

export function AttachmentChips({ items, onRemove }: AttachmentChipsProps) {
  if (items.length === 0) return null;
  return (
    <div role="list" style={{
      display: 'flex',
      flexWrap: 'wrap',
      gap: 'var(--space-2)',
      alignItems: 'center',
    }}>
      {items.map((item) => {
        const isImage = IMAGE_EXTS.has(item.ext.toLowerCase());
        return isImage
          ? <ImageChip key={item.localId} item={item} onRemove={onRemove} />
          : <FileChip key={item.localId} item={item} onRemove={onRemove} />;
      })}
    </div>
  );
}

function ImageChip({ item, onRemove }: { item: StagingItem; onRemove: (id: string) => void }) {
  const url = item.threadId && item.storage_name
    ? `${API_BASE}/api/threads/${encodeURIComponent(item.threadId)}/attachments/${encodeURIComponent(item.storage_name)}`
    : null;
  return (
    <div
      role="listitem"
      aria-label={`画像: ${item.name}（${_formatSize(item.size)}）。削除ボタン付き。`}
      aria-busy={item.status === 'uploading'}
      style={{
        position: 'relative',
        width: THUMB_SIZE,
        height: THUMB_SIZE,
        borderRadius: 'var(--radius-md)',
        border: item.status === 'error'
          ? '1px solid var(--color-destructive)'
          : '1px solid var(--color-border)',
        overflow: 'hidden',
        opacity: item.status === 'uploading' ? 0.5 : 1,
        flexShrink: 0,
      }}
    >
      {item.status === 'done' && url && (
        <img src={url} alt={item.name}
             width={THUMB_SIZE} height={THUMB_SIZE}
             style={{ objectFit: 'cover' }} />
      )}
      {item.status === 'uploading' && (
        <div style={{
          display: 'flex', justifyContent: 'center', alignItems: 'center',
          width: '100%', height: '100%',
        }}>
          <span className="typing-dot" />
        </div>
      )}
      {item.status === 'error' && (
        <div style={{
          display: 'flex', justifyContent: 'center', alignItems: 'center',
          width: '100%', height: '100%', fontSize: 20, color: 'var(--color-text-muted)',
        }}>🖼</div>
      )}
      <button
        onClick={() => onRemove(item.localId)}
        aria-label={`${item.name} を添付から削除`}
        className="chat-attach-remove-btn"
        style={{
          position: 'absolute', top: 2, right: 2,
          width: 20, height: 20, borderRadius: '50%',
          border: 'none', background: 'rgba(0,0,0,0.5)',
          color: 'white', cursor: 'pointer', fontSize: '12px',
          lineHeight: 1, padding: 0,
        }}
      >×</button>
    </div>
  );
}

function FileChip({ item, onRemove }: { item: StagingItem; onRemove: (id: string) => void }) {
  return (
    <div
      role="listitem"
      aria-label={`ファイル: ${item.name}（${_formatSize(item.size)}）。削除ボタン付き。`}
      aria-busy={item.status === 'uploading'}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 'var(--space-1)',
        height: 28,
        padding: '0 var(--space-2)',
        borderRadius: 'var(--radius-full)',
        border: item.status === 'error'
          ? '1px solid var(--color-destructive)'
          : '1px solid var(--color-border)',
        background: 'var(--color-surface)',
        color: 'var(--color-text)',
        fontSize: '14px',
        maxWidth: 240,
        opacity: item.status === 'uploading' ? 0.5 : 1,
      }}
    >
      <span aria-hidden="true">
        {item.status === 'error' ? '⚠' : '📄'}
      </span>
      <span style={{
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
      }}>
        {item.name}
      </span>
      <span style={{
        color: 'var(--color-text-muted)',
        fontSize: '12px',
      }}>
        {_formatSize(item.size)}
      </span>
      {item.status === 'uploading' && <span className="typing-dot" style={{ marginLeft: 2 }} />}
      <button
        onClick={() => onRemove(item.localId)}
        aria-label={`${item.name} を添付から削除`}
        className="chat-attach-remove-btn"
        style={{
          border: 'none',
          background: 'transparent',
          color: 'var(--color-text-muted)',
          cursor: 'pointer',
          padding: 0,
          fontSize: '16px',
          lineHeight: 1,
          marginLeft: 'var(--space-1)',
        }}
      >×</button>
    </div>
  );
}

function _formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}
