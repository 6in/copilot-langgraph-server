// frontend/src/components/MessageArea.tsx
// Message list + custom textarea input.
// Critical patterns from 07-RESEARCH.md:
// - TypingIndicator is a PROP on MessageList (not a child element)
// - AI messages use type="custom" + Message.CustomContent + MarkdownMessage
// - User messages use type="text" + direction="outgoing"
// Note: chatscope MessageInput replaced with native textarea for multi-line support.
// MessageList is placed directly inside a cs-chat-container wrapper (no ChatContainer component)
// so that the textarea can sit below it as a sibling flex item.

import { useRef, useState, useEffect } from 'react';
import type { KeyboardEvent } from 'react';
import { useCurrentTheme } from '../contexts/ThemeContext';
import { agentBgColor, agentAccentColor } from '../utils/agentColor';
import {
  MessageList,
  Message,
} from '@chatscope/chat-ui-kit-react';
import { MarkdownMessage } from './MarkdownMessage';
import type { ChatMessage, ContextMessage } from '../types';

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
        border: '1px solid #d1dbe3',
        borderRadius: '4px',
        cursor: 'pointer',
        fontSize: '0.75rem',
        color: '#666',
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
      const content = m.content.replace(/\|/g, '\\|').replace(/\n/g, '<br>');
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
        border: '1px solid #d1dbe3',
        borderRadius: '4px',
        cursor: 'pointer',
        fontSize: '0.75rem',
        color: '#666',
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

export function MessageArea({ messages, isThinking, currentTool, streamPreview, onSend, onCancel, disabled = false, placeholder, enableResend = false }: MessageAreaProps) {
  const theme = useCurrentTheme();
  const isDark = theme === 'dark';
  const [inputValue, setInputValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isInputDisabled = isThinking || disabled;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const messageListRef = useRef<any>(null);
  const elapsed = useElapsedSeconds(isThinking);

  // Context inclusion: track which messages to exclude (default = all included)
  const [excludedIndices, setExcludedIndices] = useState<Set<number>>(new Set());

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

  const handleSend = () => {
    const text = inputValue.trim();
    if (!text || isInputDisabled) return;

    if (enableResend && messages.length > 0) {
      // Build context messages from included messages (all except excluded)
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

    setInputValue('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
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
            return (
              <Message
                key={index}
                model={{
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
                <Message.Footer style={{ display: 'flex', justifyContent: 'flex-end', gap: '4px', alignItems: 'center' }}>
                  {enableResend && (
                    <label style={{ display: 'flex', alignItems: 'center', gap: '3px', fontSize: '0.72rem', color: isDark ? '#9090a8' : '#888', cursor: 'pointer', marginLeft: 'auto' }}>
                      <input
                        type="checkbox"
                        checked={isIncluded}
                        onChange={() => toggleMsgInclusion(index)}
                        style={{ margin: 0, cursor: 'pointer', accentColor: '#0366d6' }}
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
                  background: agentBgColor(msg.senderName, isDark),
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
                </div>
              </Message.CustomContent>
              <Message.Footer style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                <CopyButton text={msg.content} />
                {enableResend && (
                  <label style={{ display: 'flex', alignItems: 'center', gap: '3px', fontSize: '0.72rem', color: isDark ? '#9090a8' : '#888', cursor: 'pointer', marginLeft: 'auto' }}>
                    <input
                      type="checkbox"
                      checked={isIncluded}
                      onChange={() => toggleMsgInclusion(index)}
                      style={{ margin: 0, cursor: 'pointer', accentColor: '#0366d6' }}
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
                    color: isDark ? '#9090a8' : '#888',
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
                      border: `1px solid ${isDark ? '#3a3a52' : '#d1dbe3'}`,
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontSize: '0.72rem',
                      color: isDark ? '#9090a8' : '#888',
                      padding: '1px 6px',
                      marginLeft: 8,
                    }}
                  >
                    ✕ キャンセル
                  </button>
                )}
              </div>
              {currentTool && (
                <div style={{ fontSize: '0.8em', color: '#888', padding: '4px 8px' }}>
                  {`🔍 ${currentTool.tool} を実行中${currentTool.query ? `: "${currentTool.query}"` : '...'}`}
                </div>
              )}
              {streamPreview && streamPreview.split('\n')[0] && (
                <div style={{
                  fontSize: '0.83em',
                  color: '#777',
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

      {/* Custom textarea input — replaces chatscope MessageInput for multi-line support */}
      <div className="chat-input-bar" style={{
        borderTop: '1px solid #d1dbe3',
        background: '#fff',
        flexShrink: 0,
      }}>
        {messages.length > 0 && (
          <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '2px 8px 0' }}>
            <CopyAllButton messages={messages} />
          </div>
        )}
        <div style={{
          display: 'flex',
          alignItems: 'flex-end',
          gap: '0.5rem',
          padding: '0.6rem 0.75rem',
        }}>
          <textarea
            ref={textareaRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            onInput={handleInput}
            placeholder={placeholder ?? 'Ask Copilot anything... (Ctrl+Enter to send)'}
            disabled={isInputDisabled}
            rows={1}
            className="chat-textarea"
            style={{
              flex: 1,
              resize: 'none',
              border: '1px solid #d1dbe3',
              borderRadius: '6px',
              padding: '0.5rem 0.75rem',
              fontSize: '0.95rem',
              fontFamily: 'inherit',
              lineHeight: '1.5',
              outline: 'none',
              overflowY: 'auto',
              maxHeight: '160px',
            }}
          />
          <button
            onClick={handleSend}
            disabled={!inputValue.trim() || isInputDisabled}
            className="chat-send-btn"
            style={{
              padding: '0.5rem 1rem',
              borderRadius: '6px',
              border: 'none',
              background: '#0366d6',
              color: '#fff',
              fontWeight: 'bold',
              cursor: inputValue.trim() && !isInputDisabled ? 'pointer' : 'not-allowed',
              opacity: inputValue.trim() && !isInputDisabled ? 1 : 0.5,
              fontSize: '0.9rem',
              flexShrink: 0,
              alignSelf: 'flex-end',
              height: '36px',
            }}
          >
            Send
          </button>
        </div>
      </div>
    </div>
    </div>
  );
}
