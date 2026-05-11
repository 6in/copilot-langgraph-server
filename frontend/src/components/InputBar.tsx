// frontend/src/components/InputBar.tsx
// Phase 35 (D-08): controlled input bar extracted from MessageArea.tsx.
// Reserves toolbarSlot / previewSlot for Phase 36 attachment UI (FIN-01/02).
// NO isDark ternary — all colors via var(--color-*).

import { useRef, type KeyboardEvent, type ReactNode } from 'react';
import type { ContextMessage } from '../types';

export interface InputBarProps {
  // 送信系
  value: string;
  onChange: (next: string) => void;
  onSend: (text: string, contextMessages?: ContextMessage[]) => void;
  onCancel?: () => void;          // thinking 中のみ有効
  onAskMe?: () => void;           // AUQ 起動（opaque callback、suffix は知らない）

  // 状態
  disabled?: boolean;
  isThinking?: boolean;           // true なら Send → Cancel 切替
  placeholder?: string;

  // スロット (Phase 36 で埋まる)
  toolbarSlot?: ReactNode;        // textarea 左の横並び toolbar (📎 / ModelSelector 等)
  previewSlot?: ReactNode;        // textarea 上の添付チップ・画像サムネ帯
  warningSlot?: ReactNode;        // Phase 36 D-17: previewSlot のさらに上に VisionWarningBanner を描画する named slot

  // UX 補助
  copyAllSlot?: ReactNode;        // 既存の CopyAllButton を差し込む枠
}

export function InputBar({
  value,
  onChange,
  onSend,
  onCancel,
  onAskMe,
  disabled,
  isThinking,
  placeholder,
  toolbarSlot,
  previewSlot,
  warningSlot,
  copyAllSlot,
}: InputBarProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isInputDisabled = (isThinking ?? false) || (disabled ?? false);

  const handleSend = () => {
    const text = value.trim();
    if (!text || isInputDisabled) return;
    onSend(text);
    onChange('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };

  const handleAskMe = () => {
    if (!onAskMe) return;
    const text = value.trim();
    if (!text || isInputDisabled) return;
    onAskMe();
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
  };

  const canSend = !!value.trim() && !isInputDisabled;

  return (
    <div
      className="chat-input-bar"
      style={{
        borderTop: '1px solid var(--color-border)',
        background: 'var(--color-surface)',
        flexShrink: 0,
      }}
    >
      {/* warningSlot: 空なら帯を出さない。Phase 36 D-17 の VisionWarningBanner を差し込む */}
      {warningSlot && (
        <div style={{ borderBottom: '1px solid var(--color-border)' }}>
          {warningSlot}
        </div>
      )}

      {/* copyAllSlot: 空なら帯を出さない (UI-SPEC §InputBar Contract L322) */}
      {copyAllSlot && (
        <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '2px 8px 0' }}>
          {copyAllSlot}
        </div>
      )}

      {/* previewSlot: 空なら帯を出さない。Phase 36 で添付チップ・画像サムネを差し込む */}
      {previewSlot && (
        <div
          className="chat-input-preview"
          style={{ padding: '8px 12px', maxHeight: '120px', overflowY: 'auto' }}
        >
          {previewSlot}
        </div>
      )}

      {/* メイン行: [toolbarSlot] [textarea] [AskMe] [Send/Cancel] */}
      <div
        className="chat-input-row"
        style={{
          display: 'flex',
          alignItems: 'flex-end',
          gap: 'var(--space-2)',
          padding: 'var(--space-3)',
        }}
      >
        {/* toolbarSlot: 空なら帯を出さない。Phase 36 で 📎 / ModelSelector を差し込む */}
        {toolbarSlot && (
          <div
            className="chat-input-toolbar"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-1)',
              flexShrink: 0,
            }}
          >
            {toolbarSlot}
          </div>
        )}

        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          placeholder={placeholder ?? 'Copilot に何でも聞いてみてください... (Ctrl+Enter で送信)'}
          disabled={isInputDisabled}
          rows={1}
          className="chat-textarea"
          style={{
            flex: 1,
            resize: 'none',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-md)',
            padding: '0.5rem 0.75rem',
            fontSize: '0.95rem',
            fontFamily: 'inherit',
            lineHeight: '1.5',
            outline: 'none',
            overflowY: 'auto',
            maxHeight: '160px',
            background: 'var(--color-surface)',
            color: 'var(--color-text)',
          }}
        />

        {/* AskMe ボタン: onAskMe prop が渡された時かつ thinking でない時のみ描画 */}
        {onAskMe && !isThinking && (
          <button
            onClick={handleAskMe}
            disabled={!canSend}
            title="AUQプロトコルで回答を要求"
            className="chat-askme-btn"
            style={{
              padding: '0.5rem 0.75rem',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--color-success)',
              background: 'transparent',
              color: 'var(--color-success)',
              fontWeight: 'bold',
              fontSize: '0.8rem',
              height: '36px',
              flexShrink: 0,
              alignSelf: 'flex-end',
              cursor: canSend ? 'pointer' : 'not-allowed',
              opacity: canSend ? 1 : 0.5,
            }}
          >
            AskMe
          </button>
        )}

        {/* Send / Cancel 排他切替 (UI-SPEC L307): thinking 中は Cancel を表示 */}
        {isThinking && onCancel ? (
          <button
            onClick={onCancel}
            className="chat-cancel-btn"
            style={{
              padding: '0.5rem 1rem',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--color-border)',
              background: 'transparent',
              color: 'var(--color-text-muted)',
              fontWeight: 'bold',
              fontSize: '0.9rem',
              height: '36px',
              flexShrink: 0,
              alignSelf: 'flex-end',
              cursor: 'pointer',
            }}
          >
            キャンセル
          </button>
        ) : (
          <button
            onClick={handleSend}
            disabled={!canSend}
            className="chat-send-btn"
            style={{
              padding: '0.5rem 1rem',
              borderRadius: 'var(--radius-md)',
              border: 'none',
              background: 'var(--color-accent)',
              color: 'var(--color-accent-contrast)',
              fontWeight: 'bold',
              fontSize: '0.9rem',
              height: '36px',
              flexShrink: 0,
              alignSelf: 'flex-end',
              cursor: canSend ? 'pointer' : 'not-allowed',
              opacity: canSend ? 1 : 0.5,
            }}
          >
            送信
          </button>
        )}
      </div>
    </div>
  );
}
