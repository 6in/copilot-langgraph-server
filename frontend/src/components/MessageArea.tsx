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
import {
  MessageList,
  Message,
  TypingIndicator,
} from '@chatscope/chat-ui-kit-react';
import { MarkdownMessage } from './MarkdownMessage';
import type { ChatMessage } from '../types';

interface MessageAreaProps {
  messages: ChatMessage[];
  isThinking: boolean;
  onSend: (text: string) => void;
  disabled?: boolean;       // Phase 17: 外部から入力を無効化（討論終了・延長待ち）
  placeholder?: string;     // Phase 17: カスタムプレースホルダー
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
      const role = m.role === 'user' ? 'User' : 'Assistant';
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

export function MessageArea({ messages, isThinking, onSend, disabled = false, placeholder }: MessageAreaProps) {
  const [inputValue, setInputValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isInputDisabled = isThinking || disabled;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const messageListRef = useRef<any>(null);

  useEffect(() => {
    messageListRef.current?.scrollToBottom('auto');
  }, [messages]);

  const handleSend = () => {
    const text = inputValue.trim();
    if (!text || isInputDisabled) return;
    onSend(text);
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
        typingIndicator={
          isThinking ? <TypingIndicator content="Copilot is thinking..." /> : undefined
        }
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
              >
                <Message.Footer style={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <CopyButton text={msg.content} />
                </Message.Footer>
              </Message>
            );
          }
          // AI message — use type="custom" with MarkdownMessage inside CustomContent
          return (
            <Message
              key={index}
              model={{
                direction: 'incoming',
                position: 'single',
                type: 'custom',
              }}
            >
              <Message.CustomContent>
                <MarkdownMessage content={msg.content} />
              </Message.CustomContent>
              <Message.Footer>
                <CopyButton text={msg.content} />
              </Message.Footer>
            </Message>
          );
        })}
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
