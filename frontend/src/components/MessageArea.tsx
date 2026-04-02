// frontend/src/components/MessageArea.tsx
// ChatContainer with MessageList + MessageInput.
// Critical patterns from 07-RESEARCH.md:
// - TypingIndicator is a PROP on MessageList (not a child element)
// - AI messages use type="custom" + Message.CustomContent + MarkdownMessage
// - User messages use type="text" + direction="outgoing"

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

      <MessageInput
        placeholder="Ask Copilot anything... (Enter to send)"
        onSend={onSend}
        attachButton={false}
        sendButton={true}
      />
    </ChatContainer>
  );
}
