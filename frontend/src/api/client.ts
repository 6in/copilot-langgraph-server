// frontend/src/api/client.ts
// Typed fetch wrappers for all backend endpoints.
// API_BASE is the URL prefix baked in at build time via VITE_APP_BASE env var (default: '').
//   - No prefix:       API_BASE=''        → paths become /api/...
//   - With prefix:     API_BASE=/orochi   → paths become /orochi/api/...
// In dev, Vite proxy matches ${VITE_APP_BASE}/api and strips the prefix before forwarding.
// Behind nginx, nginx strips the prefix; FastAPI always sees /api/...

const API_BASE = (import.meta.env.VITE_APP_BASE ?? '').replace(/\/$/, '');

import type {
  AgentInfo,
  AppDefinition,
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
  GemInfo,
  GemCreate,
  CanvasAppInfo,
  CanvasDeployResponse,
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
  apiFetch<AuthStatusResponse>(`${API_BASE}/api/auth/status`);

export const startAuthFlow = () =>
  apiFetch<AuthStartResponse>(`${API_BASE}/api/auth/start`, { method: 'POST' });

export const pollAuthFlow = (flowId: string) =>
  apiFetch<AuthPollResponse>(`${API_BASE}/api/auth/poll?flow_id=${encodeURIComponent(flowId)}`);

export const logout = () =>
  apiFetch<AuthLogoutResponse>(`${API_BASE}/api/auth/logout`, { method: 'POST' });

// User info
export const getMe = () => apiFetch<UserInfoResponse>(`${API_BASE}/api/me`);

// Chat
export const postChat = (req: ChatRequest) =>
  apiFetch<ChatAsyncResponse>(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });

export const getJob = (jobId: string) =>
  apiFetch<JobStatusResponse>(`${API_BASE}/api/job/${encodeURIComponent(jobId)}`);

// SSE — returns a native EventSource for the caller to manage lifecycle.
// The URL is a GET so native EventSource works.
export const streamJob = (jobId: string): EventSource =>
  new EventSource(`${API_BASE}/api/chat/${encodeURIComponent(jobId)}/stream`);

// Threads
export const listThreads = (appId?: string, gemId?: string) => {
  const params = new URLSearchParams();
  // gem_id filter takes precedence — filters by gem association directly (handles legacy app_id='chat' threads too)
  if (gemId) params.set('gem_id', gemId);
  else if (appId) params.set('app_id', appId);
  const qs = params.toString();
  return apiFetch<ThreadInfo[]>(`${API_BASE}/api/threads${qs ? `?${qs}` : ''}`);
};

export const createThread = (gemId?: string | null) =>
  apiFetch<{ thread_id: string; label: string }>(`${API_BASE}/api/threads`, {
    method: 'POST',
    headers: gemId ? { 'Content-Type': 'application/json' } : undefined,
    body: gemId ? JSON.stringify({ gem_id: gemId }) : undefined,
  });

export const deleteThread = async (threadId: string): Promise<void> => {
  const resp = await fetch(`${API_BASE}/api/threads/${encodeURIComponent(threadId)}`, {
    method: 'DELETE',
    credentials: 'include',
  });
  if (resp.status !== 204 && !resp.ok) {
    throw new Error(`Delete thread failed: ${resp.status}`);
  }
};

export const renameThread = (threadId: string, label: string) =>
  apiFetch<{ thread_id: string; label: string }>(
    `${API_BASE}/api/threads/${encodeURIComponent(threadId)}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ label }),
    }
  );

export const getThreadMessages = (threadId: string) =>
  apiFetch<ThreadMessagesResponse>(
    `${API_BASE}/api/threads/${encodeURIComponent(threadId)}/messages`
  );

// Convenience: fetch the full message list as ChatMessage[]
export const loadThreadMessages = async (threadId: string): Promise<ChatMessage[]> => {
  const data = await getThreadMessages(threadId);
  return data.messages;
};

// Agents
export const getAgents = () =>
  apiFetch<AgentInfo[]>(`${API_BASE}/api/agents`);

// Apps
export const getApps = () =>
  apiFetch<AppDefinition[]>(`${API_BASE}/api/apps`);

// --- Phase 15: Gems API ---

export const listGems = () =>
  apiFetch<GemInfo[]>(`${API_BASE}/api/gems`);

export const createGemApi = (data: GemCreate) =>
  apiFetch<GemInfo>(`${API_BASE}/api/gems`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

export const updateGemApi = (gemId: string, data: Partial<GemCreate>) =>
  apiFetch<GemInfo>(`${API_BASE}/api/gems/${encodeURIComponent(gemId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

export const deleteGemApi = async (gemId: string): Promise<void> => {
  const resp = await fetch(`${API_BASE}/api/gems/${encodeURIComponent(gemId)}`, {
    method: 'DELETE',
    credentials: 'include',
  });
  if (resp.status !== 204 && !resp.ok) {
    throw new Error(`Delete gem failed: ${resp.status}`);
  }
};

// --- Phase 15: Canvas API ---

export const getCanvasApp = (appId: string) =>
  apiFetch<CanvasAppInfo>(`${API_BASE}/api/canvas/apps/${encodeURIComponent(appId)}`);

export const getCanvasAppByThread = (threadId: string) =>
  apiFetch<CanvasAppInfo[]>(`${API_BASE}/api/canvas/apps?thread_id=${encodeURIComponent(threadId)}`);

export const updateCanvasApp = (appId: string, html: string, name?: string) =>
  apiFetch<CanvasAppInfo>(`${API_BASE}/api/canvas/apps/${encodeURIComponent(appId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ html, ...(name ? { name } : {}) }),
  });

export const deployCanvasApp = (appId: string) =>
  apiFetch<CanvasDeployResponse>(`${API_BASE}/api/canvas/apps/${encodeURIComponent(appId)}/deploy`, {
    method: 'POST',
  });
