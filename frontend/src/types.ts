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
  senderName?: string;  // Phase 17: 討論エージェント名表示用
  // Phase 36 D-22: 添付履歴は additional_kwargs.attachments として HumanMessage に載る
  additional_kwargs?: {
    attachments?: AttachmentMeta[];
  };
}

// --- Phase 36: Attachments ---

export interface AttachmentMeta {
  kind: 'file';
  name: string;
  storage_name: string;
  path: string;
  size: number;
  mime_type: string;
  ext: string;
  modified_at: string;
}

// Phase 36 D-16: モデル一覧 (useModels / Header で消費) — Plan 06 で使うが型は先に定義しておく
export interface ModelInfo {
  id: string;
  name: string;
  vision: boolean;
  vision_limits?: {
    supported_media_types?: string[] | null;
    max_prompt_images?: number | null;
    max_prompt_image_size?: number | null;
  } | null;
  billing_multiplier?: number | null;
}

export interface ThreadMessagesResponse {
  messages: ChatMessage[];
  thread_id: string;
}

export interface AgentInfo {
  name: string;
  description: string;
}

export interface AppDefinition {
  slug: string;
  name: string;
  description: string;
  icon: string;
  agents: string[];
  type?: string;
}

export interface ContextMessage {
  role: 'user' | 'ai';
  content: string;
  sender_name?: string;
}

export interface ChatRequest {
  message: string;
  thread_id: string;
  model: string;
  task_type?: string;
  mode?: 'simple' | 'super';
  agents?: string[];
  app_id?: string;
  gem_id?: string | null;  // Phase 15: Gem association for thread creation
  gem_ids?: string[];
  context_messages?: ContextMessage[];  // 過去の会話コンテキスト（SuperChat用）
  // Phase 17: 討論チャット
  participants?: string[];
  pattern?: string;        // "debate" | "panel" | "chain"
  max_turns?: number;
  current_turn?: number;
  // Phase 36 (D-14): per-turn 新規添付
  attachments?: AttachmentMeta[];
}

// --- Phase 15: Gem + Canvas types ---

export interface GemInfo {
  gem_id: string;
  name: string;
  system_prompt: string;
  description: string;   // Todo 6: Gem カードに表示する説明文
  knowledge: string;     // Todo 7: ナレッジ（system_prompt に結合される）
  type: 'default' | 'canvas';
  is_public: boolean;    // 公開共有フラグ
  is_owner: boolean;     // リクエストユーザーが所有者かどうか
  created_at: string;
  updated_at: string;
}

export interface GemCreate {
  name: string;
  system_prompt: string;
  description: string;   // Todo 6
  knowledge: string;     // Todo 7
  type: 'default' | 'canvas';
  is_public: boolean;    // 公開共有フラグ
}

export interface CanvasAppInfo {
  app_id: string;
  thread_id: string | null;
  name: string;
  thread_label: string | null;
  html: string;
  source: 'canvas' | 'upload' | 'builtin';
  deployed: boolean;
  deployed_at: string | null;
  created_at: string;
}

export interface CanvasDeployResponse {
  url: string;
}

export interface CanvasResult {
  type: 'canvas';
  app_id: string;
  html: string;
}

// --- Phase 27: AskUserQuestion types ---

export interface AUQOption {
  label: string;
  description?: string;
}

export interface AUQQuestion {
  question: string;
  header: string;
  type?: 'single' | 'multi' | 'text';
  options?: AUQOption[];
  allowFreeText?: boolean;
  placeholder?: string;
  optional?: boolean;
}

export interface AskUserQuestionPayload {
  questions: AUQQuestion[];
}
