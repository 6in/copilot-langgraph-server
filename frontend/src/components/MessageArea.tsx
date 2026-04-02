// frontend/src/components/MessageArea.tsx
// Message list + custom textarea input.
// Critical patterns from 07-RESEARCH.md:
// - TypingIndicator is a PROP on MessageList (not a child element)
// - AI messages use type="custom" + Message.CustomContent + MarkdownMessage
// - User messages use type="text" + direction="outgoing"
// Note: chatscope MessageInput replaced with native textarea for multi-line support.
// MessageList is placed directly inside a cs-chat-container wrapper (no ChatContainer component)
// so that the textarea can sit below it as a sibling flex item.

import { useRef, useState, KeyboardEvent } from 'react';
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
}

export function MessageArea({ messages, isThinking, onSend }: MessageAreaProps) {
  const [inputValue, setInputValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const text = inputValue.trim();
    if (!text || isThinking) return;
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
    // cs-chat-container: gives flex-grow:1 and flex-direction:column from chatscope CSS.
    // height:initial overrides the default height:100% so the textarea row can sit below.
    <div className="cs-chat-container" style={{ height: 'initial', flex: 1 }}>
      {/* typingIndicator is a PROP, not a JSX child — per 07-RESEARCH.md Pitfall section */}
      <MessageList
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
            color: '#888',
            flexDirection: 'column',
            gap: '0.5rem',
          }}>
            <h3 style={{ margin: 0 }}>New conversation</h3>
            <p style={{ margin: 0 }}>Ask Copilot anything to get started.</p>
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
              />
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
            </Message>
          );
        })}
      </MessageList>

      {/* Custom textarea input — replaces chatscope MessageInput for multi-line support */}
      <div style={{
        display: 'flex',
        alignItems: 'flex-end',
        gap: '0.5rem',
        padding: '0.6rem 0.75rem',
        borderTop: '1px solid #d1dbe3',
        background: '#fff',
        flexShrink: 0,
      }}>
        <textarea
          ref={textareaRef}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          placeholder="Ask Copilot anything... (Ctrl+Enter to send)"
          disabled={isThinking}
          rows={1}
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
          disabled={!inputValue.trim() || isThinking}
          style={{
            padding: '0.5rem 1rem',
            borderRadius: '6px',
            border: 'none',
            background: '#0366d6',
            color: '#fff',
            fontWeight: 'bold',
            cursor: inputValue.trim() && !isThinking ? 'pointer' : 'not-allowed',
            opacity: inputValue.trim() && !isThinking ? 1 : 0.5,
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
  );
}
