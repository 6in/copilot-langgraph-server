// frontend/src/components/MessageArea.tsx
// ChatContainer with MessageList + MessageInput.
// Critical patterns from 07-RESEARCH.md:
// - TypingIndicator is a PROP on MessageList (not a child element)
// - AI messages use type="custom" + Message.CustomContent + MarkdownMessage
// - User messages use type="text" + direction="outgoing"

import { useState } from 'react';
import {
  ChatContainer,
  MessageList,
  Message,
  MessageInput,
  TypingIndicator,
} from '@chatscope/chat-ui-kit-react';
import { MarkdownMessage } from './MarkdownMessage';
import type { ChatMessage } from '../types';

interface MessageAreaProps {
  messages: ChatMessage[];
  isThinking: boolean;
  onSend: (text: string) => void;
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

export function MessageArea({ messages, isThinking, onSend }: MessageAreaProps) {
  return (
    <ChatContainer>
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

        {messages.length > 0 && (
          <MessageList.Content style={{ display: 'flex', justifyContent: 'flex-end', padding: '4px 8px 0' }}>
            <CopyAllButton messages={messages} />
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

      <MessageInput
        placeholder="Ask Copilot anything... (Enter to send)"
        onSend={onSend}
        attachButton={false}
        sendButton={true}
      />
    </ChatContainer>
  );
}
