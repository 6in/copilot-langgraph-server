// frontend/src/components/ChatApp.tsx
// MainContainer layout root: Sidebar (left) + ChatContainer (main).
// CRITICAL: outer div must have height: 100vh (Pitfall 1 in 07-RESEARCH.md).
// Header is rendered ABOVE the MainContainer in App.tsx, not inside it.

import { MainContainer } from '@chatscope/chat-ui-kit-react';
import { ThreadSidebar } from './ThreadSidebar';
import { MessageArea } from './MessageArea';
import { useThreads } from '../hooks/useThreads';
import { useChat } from '../hooks/useChat';

interface ChatAppProps {
  selectedModel: string;
}

export function ChatApp({ selectedModel }: ChatAppProps) {
  const {
    threads,
    activeThreadId,
    messages,
    isLoadingMessages,
    switchThread,
    createNewThread,
    removeThread,
    setMessages,
    refreshThreads,
  } = useThreads();

  const handleNewChat = async () => {
    await createNewThread();
    // Thread list refreshes on next message send
  };

  const handleSelectThread = async (threadId: string) => {
    await switchThread(threadId);
  };

  const { isThinking, sendMessage } = useChat({
    activeThreadId,
    selectedModel,
    setMessages,
    refreshThreads,
  });

  const handleSend = async (text: string) => {
    // If no thread is active, create one first
    let threadId = activeThreadId;
    if (!threadId) {
      threadId = await createNewThread();
    }
    await sendMessage(text);
    // Refresh thread list to show new thread in sidebar
    await refreshThreads();
  };

  return (
    // CRITICAL: This div must have an explicit height.
    // chatscope MainContainer/ChatContainer use height: 100% internally.
    // Without this, the entire chat UI collapses to 0px.
    // Per Pitfall 1 in 07-RESEARCH.md.
    <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
      <MainContainer>
        <ThreadSidebar
          threads={threads}
          activeThreadId={activeThreadId}
          onSelectThread={handleSelectThread}
          onNewChat={handleNewChat}
          onDeleteThread={removeThread}
        />
        {isLoadingMessages ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 1 }}>
            <p>Loading messages...</p>
          </div>
        ) : (
          <MessageArea
            messages={messages}
            isThinking={isThinking}
            onSend={handleSend}
          />
        )}
      </MainContainer>
    </div>
  );
}
