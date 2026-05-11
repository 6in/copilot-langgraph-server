// frontend/src/components/MessageArea.tsx
// Message list + InputBar (Phase 35 D-08: chat-input-bar extracted to InputBar.tsx).
// Critical patterns from 07-RESEARCH.md:
// - TypingIndicator is a PROP on MessageList (not a child element)
// - AI messages use type="custom" + Message.CustomContent + MarkdownMessage
// - User messages use type="text" + direction="outgoing"
// Note: chatscope MessageInput replaced with native textarea for multi-line support.
// MessageList is placed directly inside a cs-chat-container wrapper (no ChatContainer component)
// so that the textarea can sit below it as a sibling flex item.
// Phase 35: isDark ternary eliminated — all colors via var(--color-*).

import { useRef, useState, useEffect } from 'react';
import { useCurrentTheme } from '../contexts/ThemeContext';
import { agentBgColor, agentAccentColor } from '../utils/agentColor';
import {
  MessageList,
  Message,
} from '@chatscope/chat-ui-kit-react';
import { MarkdownMessage } from './MarkdownMessage';
import { QuestionPanel } from './QuestionPanel';
import { InputBar } from './InputBar';
import type { AskUserQuestionPayload, AttachmentMeta, ChatMessage, ContextMessage } from '../types';

const ATTACH_API_BASE = (import.meta.env.VITE_APP_BASE ?? '').replace(/\/$/, '');
const IMAGE_EXTS_HISTORY = new Set(['png', 'jpg', 'jpeg', 'webp']);
const HISTORY_THUMB = 48;

interface MessageAreaProps {
  messages: ChatMessage[];
  isThinking: boolean;
  currentTool?: {tool: string; query: string} | null;
  streamPreview?: string;   // ストリーミング中のテキストプレビュー（最大 200 文字）
  onSend: (text: string, contextMessages?: ContextMessage[]) => void;
  onCancel?: () => void;    // AI 応答キャンセル（SSE 中断）
  disabled?: boolean;       // Phase 17: 外部から入力を無効化（討論終了・延長待ち）
  placeholder?: string;     // Phase 17: カスタムプレースホルダー
  enableResend?: boolean;   // 過去メッセージ再送信機能を有効化（SuperChat用）
  pendingQuestion?: AskUserQuestionPayload | null;
  onQuestionSubmit?: (answers: Record<string, string>) => void;
  onAskMe?: (() => void) | null;  // AUQ 起動ハンドラ（AUQ suffix は MessageArea 側で付与）
  // Phase 36: InputBar slots — ChatApp 側で AttachmentButton / AttachmentChips を差し込む
  inputToolbarSlot?: React.ReactNode;
  inputPreviewSlot?: React.ReactNode;
  inputWarningSlot?: React.ReactNode;   // Phase 36 D-17: VisionWarningBanner
  // Phase 36 D-21: bubble 内 AttachmentChipRow が画像サムネ URL を組み立てるのに必要
  activeThreadId?: string | null;
}

// Phase 36 D-21: メッセージバブル内に表示する添付チップ行 (履歴復元用、読み取り専用)。
// 画像 (png/jpg/jpeg/webp) は 48×48 サムネ、それ以外は 📄 pill。
// staging UI の AttachmentChips とは別 component (削除ボタンなし、サーバ URL から img src 直読み)。
function AttachmentChipRow({
  attachments,
  threadId,
}: {
  attachments: AttachmentMeta[];
  threadId: string | null;
}) {
  if (!attachments || attachments.length === 0) return null;
  return (
    <div
      role="group"
      aria-label={`添付ファイル ${attachments.length} 件`}
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: 'var(--space-2)',
        marginTop: 'var(--space-2)',
        paddingTop: 'var(--space-2)',
        borderTop: '1px solid var(--color-border)',
      }}
    >
      {attachments.map((a) => {
        const ext = (a.ext || '').toLowerCase();
        const isImage = IMAGE_EXTS_HISTORY.has(ext);
        if (isImage && threadId && a.storage_name) {
          return (
            <img
              key={a.storage_name}
              src={`${ATTACH_API_BASE}/api/threads/${encodeURIComponent(threadId)}/attachments/${encodeURIComponent(a.storage_name)}`}
              alt={a.name}
              width={HISTORY_THUMB}
              height={HISTORY_THUMB}
              title={`${a.name}（${_formatHistorySize(a.size)}）`}
              style={{
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-border)',
                objectFit: 'cover',
              }}
            />
          );
        }
        return (
          <span
            key={a.storage_name || a.name}
            title={`${a.name}（${_formatHistorySize(a.size)}）`}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 4,
              padding: '2px 8px',
              borderRadius: 'var(--radius-full)',
              border: '1px solid var(--color-border)',
              background: 'var(--color-surface)',
              fontSize: 12,
              color: 'var(--color-text-muted)',
            }}
          >
            📄 {a.name}
          </span>
        );
      })}
    </div>
  );
}

function _formatHistorySize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <button
      onClick={handleCopy}
      title="Copy message"
      className="chat-copy-btn"
      style={{
        background: 'none',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-sm)',
        cursor: 'pointer',
        fontSize: '0.75rem',
        color: 'var(--color-text-muted)',
        padding: '2px 6px',
        marginTop: '2px',
      }}
    >
      {copied ? '✓ Copied' : '⎘ Copy'}
    </button>
  );
}

function CopyAllButton({ messages }: { messages: ChatMessage[] }) {
  const [copied, setCopied] = useState(false);

  const handleCopyAll = async () => {
    const header = '| Role | Message |\n|------|---------|';
    const rows = messages.map((m) => {
      const role = m.role === 'user' ? 'User' : (m.senderName ?? 'Assistant');
      // Defense-in-depth: m.content is typed as string but old DB threads may
      // yield non-string values; stringify defensively so .replace() never throws.
      const rawContent = typeof m.content === 'string'
        ? m.content
        : (() => { try { return JSON.stringify(m.content); } catch { return String(m.content); } })();
      const content = rawContent.replace(/\|/g, '\\|').replace(/\n/g, '<br>');
      return `| ${role} | ${content} |`;
    });
    await navigator.clipboard.writeText([header, ...rows].join('\n'));
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <button
      onClick={handleCopyAll}
      title="Copy entire conversation as Markdown table"
      className="chat-copy-btn"
      style={{
        background: 'none',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-sm)',
        cursor: 'pointer',
        fontSize: '0.75rem',
        color: 'var(--color-text-muted)',
        padding: '3px 8px',
        alignSelf: 'flex-end',
      }}
    >
      {copied ? '✓ Copied' : '⎘ Copy all'}
    </button>
  );
}

function useElapsedSeconds(active: boolean): number {
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef(0);

  useEffect(() => {
    if (!active) {
      setElapsed(0);
      return;
    }
    startRef.current = Date.now();
    setElapsed(0);
    const id = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startRef.current) / 1000));
    }, 1000);
    return () => clearInterval(id);
  }, [active]);

  return elapsed;
}

export function MessageArea({
  messages,
  isThinking,
  currentTool,
  streamPreview,
  onSend,
  onCancel,
  disabled = false,
  placeholder,
  enableResend = false,
  pendingQuestion,
  onQuestionSubmit,
  onAskMe,
  inputToolbarSlot,
  inputPreviewSlot,
  inputWarningSlot,
  activeThreadId = null,
}: MessageAreaProps) {
  // theme は agentBgColor に渡すために保持（isDark 変数は使用しない — D-01）
  const theme = useCurrentTheme();
  const [inputValue, setInputValue] = useState('');
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const messageListRef = useRef<any>(null);
  const elapsed = useElapsedSeconds(isThinking);

  // Context inclusion: track which messages to exclude (default = all included)
  // Pitfall 8: excludedIndices は MessageArea 側に残す（InputBar に持ち込まない）
  const [excludedIndices, setExcludedIndices] = useState<Set<number>>(new Set());

  // Pitfall 4: AUQ suffix 付与ロジックは MessageArea 側の責務
  const AUQ_SUFFIX = '\n\n[回答はAUQプロトコル（<ask_user_question>フォーマット）で返してください]';

  const toggleMsgInclusion = (index: number) => {
    setExcludedIndices((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  useEffect(() => {
    messageListRef.current?.scrollToBottom('auto');
  }, [messages, isThinking]);

  // contextMessages 組み立ては MessageArea に残す（InputBar に渡さない — Pitfall 8）
  const handleSendWrapped = (text: string) => {
    if (enableResend && messages.length > 0) {
      const ctxMsgs: ContextMessage[] = messages
        .filter((_, i) => !excludedIndices.has(i))
        .map((m) => ({
          role: m.role,
          content: m.content,
          ...(m.senderName ? { sender_name: m.senderName } : {}),
        }));
      onSend(text, ctxMsgs.length > 0 ? ctxMsgs : undefined);
    } else {
      onSend(text);
    }
  };

  // AUQ suffix 付与は MessageArea 側の責務（Pitfall 4）
  // InputBar の onAskMe は opaque callback として受け取る
  const handleAskMeWrapped = onAskMe
    ? () => {
        const text = inputValue.trim();
        if (!text) return;
        handleSendWrapped(text + AUQ_SUFFIX);
        setInputValue('');
      }
    : undefined;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minWidth: 0, minHeight: 0 }}>
    {/* cs-chat-container: gives flex-grow:1 and flex-direction:column from chatscope CSS.
        height:initial overrides the default height:100% so the textarea row can sit below. */}
    <div className="cs-chat-container" style={{ height: 'initial', flex: 1, minHeight: 0 }}>
      {/* typingIndicator is a PROP, not a JSX child — per 07-RESEARCH.md Pitfall section */}
      <MessageList
        ref={messageListRef}
      >
        {messages.length === 0 && !isThinking && (
          <MessageList.Content style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            flexDirection: 'column',
            gap: '0.5rem',
          }}>
            <div className="chat-empty-state" style={{ textAlign: 'center' }}>
              <h3 style={{ margin: '0 0 0.5rem' }}>New conversation</h3>
              <p style={{ margin: 0 }}>Ask Copilot anything to get started.</p>
            </div>
          </MessageList.Content>
        )}

        {messages.map((msg, index) => {
          const isIncluded = enableResend && !excludedIndices.has(index);
          if (msg.role === 'user') {
            // Phase 36 D-21: 添付がある場合は type:'custom' に切替えて CustomContent 内で
            // テキスト + AttachmentChipRow を並列描画する。添付がなければ既存の type:'text' を維持
            // (chatscope の outgoing 装飾が一番安定するため)。
            const userAttachments = msg.additional_kwargs?.attachments;
            const hasAttachments = !!(userAttachments && userAttachments.length > 0);
            return (
              <Message
                key={index}
                model={hasAttachments ? {
                  direction: 'outgoing',
                  position: 'single',
                  type: 'custom',
                } : {
                  direction: 'outgoing',
                  position: 'single',
                  type: 'text',
                  message: msg.content,
                }}
                style={enableResend ? {
                  opacity: isIncluded ? 1 : 0.45,
                  transition: 'opacity 0.15s',
                } : undefined}
              >
                {hasAttachments && (
                  <Message.CustomContent>
                    <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                    <AttachmentChipRow
                      attachments={userAttachments!}
                      threadId={activeThreadId}
                    />
                  </Message.CustomContent>
                )}
                <Message.Footer style={{ display: 'flex', justifyContent: 'flex-end', gap: '4px', alignItems: 'center' }}>
                  {enableResend && (
                    <label style={{
                      display: 'flex', alignItems: 'center', gap: '3px',
                      fontSize: '0.72rem',
                      color: 'var(--color-text-muted)',
                      cursor: 'pointer', marginLeft: 'auto',
                    }}>
                      <input
                        type="checkbox"
                        checked={isIncluded}
                        onChange={() => toggleMsgInclusion(index)}
                        style={{ margin: 0, cursor: 'pointer', accentColor: 'var(--color-accent)' }}
                      />
                      送信に含める
                    </label>
                  )}
                  <CopyButton text={msg.content} />
                </Message.Footer>
              </Message>
            );
          }
          // AI message
          return (
            <Message
              key={index}
              model={{
                direction: 'incoming',
                position: 'single',
                type: 'custom',
              }}
              style={enableResend ? {
                opacity: isIncluded ? 1 : 0.45,
                transition: 'opacity 0.15s',
              } : undefined}
              >
              <Message.CustomContent>
                <div style={msg.senderName ? {
                  background: agentBgColor(msg.senderName, theme),
                  margin: '-8px -12px',
                  padding: '8px 12px',
                  borderRadius: '6px',
                } : undefined}>
                  {msg.senderName && (
                    <div style={{ marginBottom: '6px' }}>
                      <span style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        fontSize: '0.72rem',
                        fontWeight: 600,
                        color: agentAccentColor(msg.senderName),
                        border: `1px solid ${agentAccentColor(msg.senderName)}`,
                        borderRadius: '10px',
                        padding: '1px 8px',
                        letterSpacing: '0.02em',
                        background: `${agentAccentColor(msg.senderName)}18`,
                      }}>
                        {msg.senderName}
                      </span>
                    </div>
                  )}
                  <MarkdownMessage content={msg.content} />
                  {/* Phase 36 D-21: AI 側にも additional_kwargs.attachments があれば履歴表示
                      (現状は HumanMessage 側にのみ載るが将来 AI 添付が来ても破綻しないよう描画) */}
                  {msg.additional_kwargs?.attachments && msg.additional_kwargs.attachments.length > 0 && (
                    <AttachmentChipRow
                      attachments={msg.additional_kwargs.attachments}
                      threadId={activeThreadId}
                    />
                  )}
                </div>
              </Message.CustomContent>
              <Message.Footer style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                <CopyButton text={msg.content} />
                {enableResend && (
                  <label style={{
                    display: 'flex', alignItems: 'center', gap: '3px',
                    fontSize: '0.72rem',
                    color: 'var(--color-text-muted)',
                    cursor: 'pointer', marginLeft: 'auto',
                  }}>
                    <input
                      type="checkbox"
                      checked={isIncluded}
                      onChange={() => toggleMsgInclusion(index)}
                      style={{ margin: 0, cursor: 'pointer', accentColor: 'var(--color-accent)' }}
                    />
                    送信に含める
                  </label>
                )}
              </Message.Footer>
            </Message>
          );
        })}

        {/* Inline typing indicator — rendered below the last message in the scroll flow */}
        {isThinking && (
          <Message
            model={{ direction: 'incoming', position: 'single', type: 'custom' }}
          >
            <Message.CustomContent>
              <div style={{ display: 'flex', gap: '5px', alignItems: 'center', padding: '2px 0' }}>
                <span className="typing-dot" />
                <span className="typing-dot" />
                <span className="typing-dot" />
                {elapsed > 0 && (
                  <span style={{
                    fontSize: '0.75rem',
                    color: 'var(--color-text-muted)',
                    marginLeft: 8,
                    fontVariantNumeric: 'tabular-nums',
                  }}>
                    {elapsed}s
                  </span>
                )}
                {onCancel && (
                  <button
                    onClick={onCancel}
                    title="応答をキャンセル"
                    style={{
                      background: 'none',
                      border: '1px solid var(--color-border)',
                      borderRadius: 'var(--radius-sm)',
                      cursor: 'pointer',
                      fontSize: '0.72rem',
                      color: 'var(--color-text-muted)',
                      padding: '1px 6px',
                      marginLeft: 8,
                    }}
                  >
                    ✕ キャンセル
                  </button>
                )}
              </div>
              {currentTool && (
                <div style={{ fontSize: '0.8em', color: 'var(--color-text-muted)', padding: '4px 8px' }}>
                  {`🔍 ${currentTool.tool} を実行中${currentTool.query ? `: "${currentTool.query}"` : '...'}`}
                </div>
              )}
              {streamPreview && streamPreview.split('\n')[0] && (
                <div style={{
                  fontSize: '0.83em',
                  color: 'var(--color-text-muted)',
                  marginTop: '6px',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  lineHeight: '1.5',
                  opacity: 0.85,
                }}>
                  {streamPreview.split('\n')[0]}
                </div>
              )}
            </Message.CustomContent>
          </Message>
        )}
      </MessageList>

      {/* Input area: QuestionPanel (pendingQuestion あり) または InputBar */}
      {pendingQuestion ? (
        <div
          className="chat-input-bar"
          style={{
            padding: '0.75rem',
            background: 'var(--color-surface)',
            borderTop: '1px solid var(--color-border)',
          }}
        >
          <div style={{
            fontSize: '11px',
            color: 'var(--color-text-muted)',
            marginBottom: '8px',
          }}>
            質問に回答してください
          </div>
          <QuestionPanel
            questions={pendingQuestion.questions}
            onSubmit={onQuestionSubmit!}
          />
        </div>
      ) : (
        <InputBar
          value={inputValue}
          onChange={setInputValue}
          onSend={handleSendWrapped}
          onCancel={onCancel}
          onAskMe={handleAskMeWrapped}
          isThinking={isThinking}
          disabled={disabled}
          placeholder={placeholder}
          copyAllSlot={messages.length > 0 ? <CopyAllButton messages={messages} /> : undefined}
          // Phase 36: ChatApp が AttachmentButton / AttachmentChips を name 付きで差し込む
          toolbarSlot={inputToolbarSlot}
          previewSlot={inputPreviewSlot}
          warningSlot={inputWarningSlot}
        />
      )}
    </div>
    </div>
  );
}
