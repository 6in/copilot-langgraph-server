// frontend/src/types.ts
// All types aligned with backend app/api/models.py

export interface AuthStartResponse {
  user_code: string;
  verification_uri: string;
  device_code: string;
  flow_id: string;
}

export interface AuthPollResponse {
  done: boolean;
  error?: string;
  retry_after?: number;
}

export interface AuthStatusResponse {
  authenticated: boolean;
  expired: boolean;
}

export interface AuthLogoutResponse {
  success: boolean;
  message: string;
}

export interface ChatAsyncResponse {
  job_id: string;
  thread_id: string;
}

export interface JobStatusResponse {
  status: 'pending' | 'done';
  result?: string;
}

export interface ThreadInfo {
  thread_id: string;
  updated_at?: string | null;
  label: string;
  app_id?: string;
}

export interface UserInfoResponse {
  login: string;
  name?: string;
  avatar_url: string;
}

export interface ChatMessage {
  role: 'user' | 'ai';
  content: string;
}

export interface ThreadMessagesResponse {
  messages: ChatMessage[];
  thread_id: string;
}

export interface AgentInfo {
  name: string;
  description: string;
}

export interface ChatRequest {
  message: string;
  thread_id: string;
  model: string;
  task_type?: string;
  mode?: 'simple' | 'super';
  agents?: string[];
}
