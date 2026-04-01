// ============================================================
// Copilot Chat — Frontend Application Logic
// ============================================================
// Security note:
//   - User messages always use textContent (XSS prevention)
//   - AI replies use innerHTML with md.parse() scoped under .prose
// ============================================================

// ---- Global state ----
let activeThreadId = null;
let selectedModel = 'claude-sonnet-4.5';
let isAuthenticated = false;
let authPollInterval = null;

// ---- Markdown renderer setup (UI-SPEC: Markdown Rendering Contract) ----
// marked.js v17 UMD global: globalThis.marked exposes { Marked } and { parse }
// marked-highlight UMD global: globalThis.markedHighlight exposes { markedHighlight }
const { Marked } = globalThis.marked;
const { markedHighlight } = globalThis.markedHighlight;

const md = new Marked(
  markedHighlight({
    emptyLangClass: 'hljs',
    langPrefix: 'hljs language-',
    highlight(code, lang) {
      const language = hljs.getLanguage(lang) ? lang : 'plaintext';
      return hljs.highlight(code, { language }).value;
    }
  })
);

// ---- DOM init ----
document.addEventListener('DOMContentLoaded', () => {
  const sendBtn = document.getElementById('send-btn');
  const userInput = document.getElementById('user-input');
  const newChatBtn = document.getElementById('new-chat-btn');
  const modelSelect = document.getElementById('model-select');
  const copyCodeBtn = document.getElementById('copy-code-btn');
  const authStatus = document.getElementById('auth-status');

  // Send on button click
  sendBtn.addEventListener('click', sendMessage);

  // Send on Ctrl+Enter or Cmd+Enter; plain Enter inserts a newline
  userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      sendMessage();
    }
  });

  // Auto-grow textarea
  userInput.addEventListener('input', () => {
    userInput.style.height = 'auto';
    userInput.style.height = Math.min(userInput.scrollHeight, 120) + 'px';
  });

  // New Chat
  newChatBtn.addEventListener('click', createNewThread);

  // Model selection
  modelSelect.addEventListener('change', () => {
    selectedModel = modelSelect.value;
  });

  // Copy device code
  copyCodeBtn.addEventListener('click', () => {
    const deviceCode = document.getElementById('device-code').textContent;
    navigator.clipboard.writeText(deviceCode).then(() => {
      copyCodeBtn.textContent = 'Copied \u2713';
      setTimeout(() => {
        copyCodeBtn.textContent = 'Copy';
      }, 2000);
    }).catch(() => {
      // Fallback: select the text
      copyCodeBtn.textContent = 'Copy failed';
      setTimeout(() => {
        copyCodeBtn.textContent = 'Copy';
      }, 2000);
    });
  });

  // Initialize app state
  checkAuthStatus();
  loadThreads();
});

// ---- Auth status check ----
async function checkAuthStatus() {
  try {
    const resp = await fetch('/api/auth/status');
    const data = await resp.json();
    const el = document.getElementById('auth-status');

    if (data.authenticated) {
      isAuthenticated = true;
      // Green dot + "Authenticated" (UI-SPEC: Header)
      el.innerHTML = '<span style="color:#4caf50">&#9679;</span> Authenticated';
      el.className = 'auth-status authenticated';
      el.onclick = null;
      el.style.cursor = 'default';
    } else if (data.expired) {
      isAuthenticated = false;
      // D-04: "Session expired — click to re-auth"
      el.textContent = 'Session expired \u2014 click to re-auth';
      el.className = 'auth-status expired';
      el.style.cursor = 'pointer';
      el.onclick = () => startAuthFlow();
    } else {
      isAuthenticated = false;
      // Unauthenticated: show Login button
      el.textContent = 'Login with GitHub';
      el.className = 'auth-status login-btn';
      el.style.cursor = 'pointer';
      el.onclick = () => startAuthFlow();
    }
  } catch (err) {
    console.error('Failed to check auth status:', err);
  }
}

// ---- Start Device Flow auth ----
async function startAuthFlow() {
  try {
    const resp = await fetch('/api/auth/start', { method: 'POST' });
    const data = await resp.json();

    const authPanel = document.getElementById('auth-panel');
    const authUrl = document.getElementById('auth-url');
    const deviceCode = document.getElementById('device-code');
    const authPollingStatus = document.getElementById('auth-polling-status');

    authUrl.href = data.verification_uri;
    authUrl.textContent = data.verification_uri;
    deviceCode.textContent = data.user_code;

    // Reset polling status display
    authPollingStatus.innerHTML =
      '<span class="spinner"></span><span>Waiting for authentication...</span>';

    // Show the auth panel
    authPanel.style.display = 'flex';

    // Clear any existing polling interval
    if (authPollInterval) {
      clearInterval(authPollInterval);
      authPollInterval = null;
    }

    // Start polling every 5 seconds (D-03)
    authPollInterval = setInterval(pollAuth, 5000);
  } catch (err) {
    console.error('Failed to start auth flow:', err);
  }
}

// ---- Poll for auth completion ----
async function pollAuth() {
  try {
    const resp = await fetch('/api/auth/poll');
    const data = await resp.json();

    if (data.done === true) {
      // Auth complete
      clearInterval(authPollInterval);
      authPollInterval = null;

      const authPanel = document.getElementById('auth-panel');
      authPanel.style.display = 'none';

      // D-03: auto-refresh on success
      await checkAuthStatus();
      location.reload();
    } else if (data.error && !data.done) {
      // Show error in auth panel but keep polling (unless it's a terminal error)
      const authPollingStatus = document.getElementById('auth-polling-status');
      authPollingStatus.innerHTML =
        '<span class="spinner"></span>' +
        '<span>Waiting for authentication...</span>' +
        '<div class="auth-error-msg">' + data.error + '</div>';
    }
  } catch (err) {
    console.error('Failed to poll auth:', err);
  }
}

// ---- Send message ----
async function sendMessage() {
  const userInput = document.getElementById('user-input');
  const sendBtn = document.getElementById('send-btn');
  const text = userInput.value.trim();

  if (!text) return;

  // Check auth before sending
  if (!isAuthenticated) {
    appendMessage('error', 'You need to log in before sending messages.');
    return;
  }

  // Disable input during response (D-13)
  userInput.disabled = true;
  sendBtn.disabled = true;
  sendBtn.classList.add('disabled');

  // Show user message (textContent — XSS prevention)
  appendMessage('user', text);

  // Clear and reset input
  userInput.value = '';
  userInput.style.height = 'auto';

  // Auto-create a thread if none is active
  if (!activeThreadId) {
    try {
      const threadResp = await fetch('/api/threads', { method: 'POST' });
      const threadData = await threadResp.json();
      activeThreadId = threadData.thread_id;
    } catch (err) {
      console.error('Failed to create thread:', err);
    }
    if (!activeThreadId) {
      hideTyping();
      appendMessage('error', 'Could not create a conversation thread. Please try again.');
      userInput.disabled = false;
      sendBtn.disabled = false;
      sendBtn.classList.remove('disabled');
      userInput.focus();
      return;
    }
  }

  // Show typing indicator (D-12)
  showTyping();

  try {
    const resp = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: text,
        thread_id: activeThreadId,
        model: selectedModel
      })
    });

    if (!resp.ok) {
      hideTyping();
      appendMessage('error', `Server error: ${resp.status} ${resp.statusText}`);
      return;
    }

    const data = await resp.json();

    hideTyping();

    if (data.error === 'auth_expired') {
      // D-04: trigger header update
      await checkAuthStatus();
      appendMessage('error', 'Session expired \u2014 click to re-auth in the header.');
    } else if (data.error) {
      appendMessage('error', data.error);
    } else {
      // Update active thread if server assigned one
      if (data.thread_id && !activeThreadId) {
        activeThreadId = data.thread_id;
        await loadThreads();
      }

      // AI reply uses innerHTML with marked.js output scoped under .prose
      appendMessage('ai', data.reply || '');
    }
  } catch (err) {
    hideTyping();
    appendMessage('error', 'Something went wrong. Check your connection and try again.');
    console.error('Send message error:', err);
  } finally {
    // Re-enable input and refocus
    userInput.disabled = false;
    sendBtn.disabled = false;
    sendBtn.classList.remove('disabled');
    userInput.focus();
  }
}

// ---- Append message to chat ----
function appendMessage(role, content) {
  const messageList = document.getElementById('message-list');

  // Hide empty state
  const emptyState = document.getElementById('empty-state');
  if (emptyState) {
    emptyState.style.display = 'none';
  }

  const messageDiv = document.createElement('div');
  messageDiv.className = 'message ' + role;

  const bubble = document.createElement('div');
  bubble.className = 'bubble';

  if (role === 'user') {
    // User messages: textContent only (XSS prevention)
    bubble.textContent = content;
  } else if (role === 'ai') {
    // AI replies: Markdown rendered via marked.js, scoped under .prose
    bubble.innerHTML = '<div class="prose">' + md.parse(content) + '</div>';
  } else if (role === 'error') {
    // Error messages: textContent only
    bubble.textContent = content;
  }

  messageDiv.appendChild(bubble);
  messageList.appendChild(messageDiv);

  // Scroll to bottom
  messageList.scrollTop = messageList.scrollHeight;
}

// ---- Typing indicator (D-12) ----
function showTyping() {
  const bubble = document.createElement('div');
  bubble.id = 'typing-indicator';
  bubble.className = 'message ai typing';
  bubble.innerHTML = '<div class="bubble"><span class="dot"></span><span class="dot"></span><span class="dot"></span></div>';
  document.getElementById('message-list').appendChild(bubble);
  bubble.scrollIntoView({ behavior: 'smooth' });
}

function hideTyping() {
  document.getElementById('typing-indicator')?.remove();
}

// ---- Create new thread (CHAT-04) ----
async function createNewThread() {
  try {
    const resp = await fetch('/api/threads', { method: 'POST' });
    const data = await resp.json();

    activeThreadId = data.thread_id;

    // Clear message list and show empty state
    const messageList = document.getElementById('message-list');
    messageList.innerHTML = '';

    const emptyState = document.createElement('div');
    emptyState.id = 'empty-state';
    emptyState.className = 'empty-state';
    emptyState.innerHTML = '<h2>New conversation</h2><p>Ask Copilot anything to get started.</p>';
    messageList.appendChild(emptyState);

    // Refresh thread list sidebar
    await loadThreads();
  } catch (err) {
    console.error('Failed to create new thread:', err);
  }
}

// ---- Load threads into sidebar ----
async function loadThreads() {
  try {
    const resp = await fetch('/api/threads');
    const threads = await resp.json();

    const threadList = document.getElementById('thread-list');
    threadList.innerHTML = '';

    if (!threads || threads.length === 0) {
      return;
    }

    threads.forEach((thread) => {
      const item = document.createElement('div');
      item.className = 'thread-item';
      item.dataset.threadId = thread.thread_id;

      // Mark active thread
      if (thread.thread_id === activeThreadId) {
        item.classList.add('active');
      }

      const label = document.createElement('span');
      label.className = 'thread-label';
      label.textContent = thread.label || thread.thread_id;
      label.title = thread.label || thread.thread_id;
      item.appendChild(label);

      const deleteBtn = document.createElement('button');
      deleteBtn.className = 'thread-delete-btn';
      deleteBtn.textContent = '\u00d7';
      deleteBtn.title = 'Delete thread';
      deleteBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        deleteThread(thread.thread_id);
      });
      item.appendChild(deleteBtn);

      item.addEventListener('click', () => {
        switchThread(thread.thread_id);
      });

      threadList.appendChild(item);
    });
  } catch (err) {
    console.error('Failed to load threads:', err);
  }
}

// ---- Delete a thread ----
async function deleteThread(threadId) {
  try {
    await fetch('/api/threads/' + threadId, { method: 'DELETE' });
  } catch (err) {
    console.error('Failed to delete thread:', err);
  }

  // If the deleted thread was active, reset to a blank chat
  if (activeThreadId === threadId) {
    activeThreadId = null;
    const messageList = document.getElementById('message-list');
    messageList.innerHTML = '';
    const emptyState = document.createElement('div');
    emptyState.id = 'empty-state';
    emptyState.className = 'empty-state';
    emptyState.innerHTML = '<h2>New conversation</h2><p>Ask Copilot anything to get started.</p>';
    messageList.appendChild(emptyState);
  }

  await loadThreads();
}

// ---- Switch to a thread ----
async function switchThread(threadId) {
  activeThreadId = threadId;

  // Update active class in sidebar
  document.querySelectorAll('.thread-item').forEach((item) => {
    if (item.dataset.threadId === threadId) {
      item.classList.add('active');
    } else {
      item.classList.remove('active');
    }
  });

  const messageList = document.getElementById('message-list');
  messageList.innerHTML = '';

  try {
    const resp = await fetch('/api/threads/' + threadId + '/messages');
    const data = await resp.json();

    const messages = data.messages || [];

    if (messages.length === 0) {
      // Show empty state
      const emptyState = document.createElement('div');
      emptyState.id = 'empty-state';
      emptyState.className = 'empty-state';
      emptyState.innerHTML = '<h2>New conversation</h2><p>Ask Copilot anything to get started.</p>';
      messageList.appendChild(emptyState);
    } else {
      messages.forEach((msg) => {
        appendMessage(msg.role, msg.content);
      });
    }
  } catch (err) {
    console.error('Failed to load thread messages:', err);
    appendMessage('error', 'Something went wrong. Check your connection and try again.');
  }
}
