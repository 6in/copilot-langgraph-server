// frontend/src/api/client.ts
// Typed fetch wrappers for all backend endpoints.
// All API paths are RELATIVE (./api/...) so the browser resolves them against
// the current page origin + Vite's `base` path. This means:
//   - Dev: Vite proxy intercepts and forwards to FastAPI
//   - Prod behind nginx: nginx strips the prefix, FastAPI sees /api/...
//   - No hardcoded prefix needed in JS code

import type {
  AuthStartResponse,
  AuthPollResponse,
  AuthStatusResponse,
  AuthLogoutResponse,
  ChatAsyncResponse,
  JobStatusResponse,
  ThreadInfo,
  UserInfoResponse,
  ChatMessage,
  ThreadMessagesResponse,
  ChatRequest,
} from '../types';

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(path, { credentials: 'include', ...init });
  if (!resp.ok) {
    throw new Error(`API error ${resp.status} on ${path}`);
  }
  return resp.json() as Promise<T>;
}

// Auth
export const checkAuthStatus = () =>
  apiFetch<AuthStatusResponse>('./api/auth/status');

export const startAuthFlow = () =>
  apiFetch<AuthStartResponse>('./api/auth/start', { method: 'POST' });

export const pollAuthFlow = (flowId: string) =>
  apiFetch<AuthPollResponse>(`./api/auth/poll?flow_id=${encodeURIComponent(flowId)}`);

export const logout = () =>
  apiFetch<AuthLogoutResponse>('./api/auth/logout', { method: 'POST' });

// User info
export const getMe = () => apiFetch<UserInfoResponse>('./api/me');

// Chat
export const postChat = (req: ChatRequest) =>
  apiFetch<ChatAsyncResponse>('./api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });

export const getJob = (jobId: string) =>
  apiFetch<JobStatusResponse>(`./api/job/${encodeURIComponent(jobId)}`);

// SSE — returns a native EventSource for the caller to manage lifecycle.
// The URL is a GET (./api/chat/{job_id}/stream) so native EventSource works.
export const streamJob = (jobId: string): EventSource =>
  new EventSource(`./api/chat/${encodeURIComponent(jobId)}/stream`);

// Threads
export const listThreads = () => apiFetch<ThreadInfo[]>('./api/threads');

export const createThread = () =>
  apiFetch<{ thread_id: string; label: string }>('./api/threads', { method: 'POST' });

export const deleteThread = async (threadId: string): Promise<void> => {
  const resp = await fetch(`./api/threads/${encodeURIComponent(threadId)}`, {
    method: 'DELETE',
    credentials: 'include',
  });
  if (resp.status !== 204 && !resp.ok) {
    throw new Error(`Delete thread failed: ${resp.status}`);
  }
};

export const renameThread = (threadId: string, label: string) =>
  apiFetch<{ thread_id: string; label: string }>(
    `./api/threads/${encodeURIComponent(threadId)}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ label }),
    }
  );

export const getThreadMessages = (threadId: string) =>
  apiFetch<ThreadMessagesResponse>(
    `./api/threads/${encodeURIComponent(threadId)}/messages`
  );

// Convenience: fetch the full message list as ChatMessage[]
export const loadThreadMessages = async (threadId: string): Promise<ChatMessage[]> => {
  const data = await getThreadMessages(threadId);
  return data.messages;
};
