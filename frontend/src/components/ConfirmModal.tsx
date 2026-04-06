// frontend/src/components/ConfirmModal.tsx
// Theme-aware confirmation modal — replaces window.confirm() calls.

import { createPortal } from 'react-dom';

interface ConfirmModalProps {
  isOpen: boolean;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  isDark?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmModal({
  isOpen,
  message,
  confirmLabel = 'OK',
  cancelLabel = 'キャンセル',
  isDark = false,
  onConfirm,
  onCancel,
}: ConfirmModalProps) {
  if (!isOpen) return null;

  const bg = isDark ? '#2a2a3e' : '#ffffff';
  const textColor = isDark ? '#e8e8f0' : '#333333';
  const borderColor = isDark ? '#3a3a52' : '#d1dbe3';

  return createPortal(
    <div
      role="dialog"
      aria-modal="true"
      onClick={onCancel}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.45)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: bg,
          borderRadius: '10px',
          padding: '24px 28px',
          maxWidth: '360px',
          width: '90%',
          boxShadow: '0 8px 32px rgba(0,0,0,0.25)',
          border: `1px solid ${borderColor}`,
        }}
      >
        <p style={{ margin: '0 0 20px', fontSize: '0.95rem', color: textColor, lineHeight: 1.5 }}>
          {message}
        </p>
        <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
          <button
            onClick={onCancel}
            style={{
              padding: '6px 16px',
              border: `1px solid ${borderColor}`,
              borderRadius: '6px',
              background: 'transparent',
              color: textColor,
              cursor: 'pointer',
              fontSize: '0.875rem',
            }}
          >
            {cancelLabel}
          </button>
          <button
            autoFocus
            onClick={onConfirm}
            style={{
              padding: '6px 16px',
              border: 'none',
              borderRadius: '6px',
              background: '#e05252',
              color: '#fff',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.875rem',
            }}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}
