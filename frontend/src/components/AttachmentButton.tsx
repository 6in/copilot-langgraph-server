// frontend/src/components/AttachmentButton.tsx
// Phase 36 D-04/D-05: 📎 button + hidden input[type=file multiple]。
// InputBar.toolbarSlot に差し込まれる想定。click 経路の file 選択を onFilesSelected で通知。

import { useRef, type ChangeEvent } from 'react';

export interface AttachmentButtonProps {
  onFilesSelected: (files: File[]) => void;
  disabled?: boolean;
  acceptedExtensions?: string[];  // HTML accept 属性（.png / .jpg / .webp / text/* / etc）
}

const DEFAULT_ACCEPT = [
  '.png', '.jpg', '.jpeg', '.webp',
  '.txt', '.md', '.json', '.csv', '.py', '.js', '.ts', '.tsx', '.jsx',
  '.html', '.css', '.yaml', '.yml', '.toml', '.xml', '.log', '.sh', '.sql',
  'text/*',
];

export function AttachmentButton({
  onFilesSelected,
  disabled,
  acceptedExtensions,
}: AttachmentButtonProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleClick = () => {
    if (disabled) return;
    fileInputRef.current?.click();
  };

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    if (files.length > 0) onFilesSelected(files);
    // 同名ファイル再添付のため reset
    e.target.value = '';
  };

  return (
    <>
      <button
        type="button"
        onClick={handleClick}
        disabled={disabled}
        aria-label={disabled ? '添付を追加できません（送信中）' : 'ファイルを添付'}
        title="ファイルを添付（最大 100MB / 画像は 10MB × 5 枚まで）"
        className="chat-attach-btn"
        style={{
          width: 36,
          height: 36,
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--color-border)',
          background: 'transparent',
          color: 'var(--color-text-muted)',
          cursor: disabled ? 'not-allowed' : 'pointer',
          opacity: disabled ? 0.5 : 1,
          fontSize: '18px',
          lineHeight: 1,
          flexShrink: 0,
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          position: 'relative',
        }}
      >
        <span aria-hidden="true">📎</span>
        <span style={{
          position: 'absolute',
          width: 1, height: 1, padding: 0, overflow: 'hidden',
          clip: 'rect(0,0,0,0)', whiteSpace: 'nowrap', border: 0,
        }}>ファイルを添付</span>
      </button>
      <input
        ref={fileInputRef}
        type="file"
        multiple
        hidden
        accept={(acceptedExtensions ?? DEFAULT_ACCEPT).join(',')}
        onChange={handleChange}
      />
    </>
  );
}
