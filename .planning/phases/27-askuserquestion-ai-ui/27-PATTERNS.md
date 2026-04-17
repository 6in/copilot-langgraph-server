# Phase 27: AskUserQuestion の実装 - Pattern Map

**Mapped:** 2026-04-17
**Files analyzed:** 9 (新規 1 + 変更 8)
**Analogs found:** 9 / 9

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `frontend/src/components/QuestionPanel.tsx` | component | request-response | `work/uaw/AskUserQuestion.jsx` | exact (TypeScript 変換) |
| `frontend/src/hooks/useChat.ts` | hook | event-driven | 自己参照（既存ファイル変更） | exact |
| `frontend/src/components/MessageArea.tsx` | component | request-response | 自己参照（既存ファイル変更） | exact |
| `frontend/src/types.ts` | type-definition | — | 自己参照（既存ファイル変更） | exact |
| `frontend/src/components/ChatApp.tsx` | component | request-response | 自己参照（既存ファイル変更） | exact |
| `frontend/src/components/SuperChatApp.tsx` | component | request-response | `frontend/src/components/ChatApp.tsx` | role-match |
| `frontend/src/components/GemChatApp.tsx` | component | request-response | `frontend/src/components/ChatApp.tsx` | role-match |
| `app/jobs/handlers/langgraph_handler.py` | handler | request-response | 自己参照（既存ファイル変更） | exact |
| `app/utils/system_prompt.py` | utility | — | 自己参照（既存ファイル変更） | exact |

---

## Pattern Assignments

### `frontend/src/components/QuestionPanel.tsx` (component, request-response)

**Analog:** `work/uaw/AskUserQuestion.jsx`

**作業:** JSX をそのまま TypeScript に変換。`locked`/`lockedAnswers` props は D-07 によりスコープ外なので省略可（optional として残してよい）。

**インポートパターン** (lines 1):
```typescript
import { useState } from 'react';
```

**型定義パターン** — RESEARCH.md Code Examples セクションより:
```typescript
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
```

**コアコンポーネントシグネチャ** (work/uaw/AskUserQuestion.jsx lines 18):
```typescript
// D-07: locked/lockedAnswers は不要だが optional として残してよい
export function QuestionPanel({
  questions,
  onSubmit,
}: {
  questions: AUQQuestion[];
  onSubmit: (answers: Record<string, string>) => void;
}) { ... }
```

**状態管理パターン** (work/uaw/AskUserQuestion.jsx lines 19-68):
```typescript
const [answers, setAnswers] = useState<Record<string, { selected?: string | string[] | null; freeText?: string; text?: string }>>({});

function toggleOption(qid: string, label: string, type: string) { ... }
function setFreeOther(qid: string, text: string) { ... }
function setText(qid: string, text: string) { ... }
function isAnswered(q: AUQQuestion): boolean { ... }
const canSubmit = questions.every(isAnswered);
```

**TypeScript 変換の注意点 (Pitfall 5)** — `optionIndicator` 関数プロパティを独立したヘルパーに取り出す:
```typescript
// work/uaw/AskUserQuestion.jsx lines 219-225 の S.optionIndicator を独立関数に:
function getOptionIndicatorStyle(
  type: string,
  selected: boolean,
  locked: boolean
): React.CSSProperties {
  return {
    width: 12, height: 12,
    borderRadius: type === 'multi' ? 3 : '50%',
    border: `1.5px solid ${selected ? '#22c55e' : locked ? '#2a2a35' : '#3a3a48'}`,
    background: selected ? '#22c55e' : 'transparent',
    flexShrink: 0, transition: 'all 0.15s',
  };
}
```

**送信ハンドラパターン** (work/uaw/AskUserQuestion.jsx lines 65-68):
```typescript
function handleSubmit() {
  const result: Record<string, string> = {};
  questions.forEach((q) => { result[q.question] = getDisplayValue(q); });
  onSubmit(result);
}
```

---

### `frontend/src/hooks/useChat.ts` (hook, event-driven)

**Analog:** 自己参照（既存ファイルの拡張）

**parseJobResult の拡張パターン** (useChat.ts lines 53-74 を拡張):

```typescript
// 既存シグネチャ (line 53)
function parseJobResult(raw: string): {
  text: string;
  canvas: CanvasResult | null;
  debate: DebateResult | null;
  agentName: string | null;
  // ↓ 追加
  askUserQuestion: AskUserQuestionPayload | null;
}

// 既存の try ブロック (lines 54-73) に ask_user_question 分岐はないため、
// catch ブロック (lines 70-72) を拡張する:
} catch {
  // plain text — not JSON
  // ↓ 追加: AUQ タグ検出
  const AUQ_RE = /<ask_user_question>([\s\S]*?)<\/ask_user_question>/;
  const m = raw.match(AUQ_RE);
  if (m) {
    try {
      const auq = JSON.parse(m[1].trim()) as AskUserQuestionPayload;
      return { text: '', canvas: null, debate: null, agentName: null, askUserQuestion: auq };
    } catch {
      // JSON パース失敗 → plain text として返す
    }
  }
}
return { text: raw, canvas: null, debate: null, agentName: null, askUserQuestion: null };
```

**UseChatReturn インターフェース拡張** (useChat.ts lines 44-50):
```typescript
// 既存 (lines 44-50)
interface UseChatReturn {
  isThinking: boolean;
  currentTool: {tool: string; query: string} | null;
  streamPreview: string;
  sendMessage: (text: string, threadId?: string, contextMessages?: ContextMessage[]) => Promise<void>;
  cancelJob: () => void;
  // ↓ 追加
  pendingQuestion: AskUserQuestionPayload | null;
  handleQuestionSubmit: (answers: Record<string, string>) => void;
}
```

**pendingQuestion 状態追加** (既存の isThinking 宣言 line 94 と同パターン):
```typescript
// 既存 (line 94-96)
const [isThinking, setIsThinking] = useState(false);
const [currentTool, setCurrentTool] = useState<{tool: string; query: string} | null>(null);
// ↓ 追加
const [pendingQuestion, setPendingQuestion] = useState<AskUserQuestionPayload | null>(null);
```

**handleResult 内の AUQ 分岐** (既存の handleResult lines 149-189 に追加):
```typescript
// 既存 (line 149-150)
const handleResult = (raw: string) => {
  const { text: resultText, canvas, debate, agentName, askUserQuestion } = parseJobResult(raw);
  // ↓ 追加: ask_user_question を最初に処理
  if (askUserQuestion) {
    setPendingQuestion(askUserQuestion);
    // AI バブルは表示しない（質問パネルのみ表示）
    return;
  }
  // 既存の canvas / debate 処理...
```

**handleQuestionSubmit** — work/uaw/Chat.jsx lines 111-118 のパターン:
```typescript
const handleQuestionSubmit = useCallback((answers: Record<string, string>) => {
  setPendingQuestion(null);
  const text = Object.entries(answers)
    .filter(([, v]) => v)
    .map(([q, a]) => `${q}：${a}`)
    .join('\n');
  sendMessage(text);
}, [sendMessage]);
```

**return 文拡張** (useChat.ts line 323):
```typescript
// 既存 (line 323)
return { isThinking, currentTool, streamPreview, sendMessage, cancelJob };
// ↓ 変更
return { isThinking, currentTool, streamPreview, sendMessage, cancelJob, pendingQuestion, handleQuestionSubmit };
```

---

### `frontend/src/components/MessageArea.tsx` (component, request-response)

**Analog:** 自己参照（既存ファイルの変更）

**MessageAreaProps インターフェース拡張** (MessageArea.tsx lines 22-32):
```typescript
// 既存 (lines 22-32)
interface MessageAreaProps {
  messages: ChatMessage[];
  isThinking: boolean;
  currentTool?: {tool: string; query: string} | null;
  streamPreview?: string;
  onSend: (text: string, contextMessages?: ContextMessage[]) => void;
  onCancel?: () => void;
  disabled?: boolean;
  placeholder?: string;
  enableResend?: boolean;
  // ↓ 追加
  pendingQuestion?: AskUserQuestionPayload | null;
  onQuestionSubmit?: (answers: Record<string, string>) => void;
}
```

**入力エリア条件置換** (MessageArea.tsx lines 366-429 の chat-input-bar div を変更):
```typescript
// 変更対象: lines 366-429 の <div className="chat-input-bar"> ブロック全体

{/* Chat input bar — QuestionPanel or textarea */}
<div className="chat-input-bar" style={{
  borderTop: '1px solid #d1dbe3',
  background: '#fff',
  flexShrink: 0,
}}>
  {pendingQuestion ? (
    // D-01: 質問パネル表示時は入力欄を置換
    <div style={{ padding: '0.75rem' }}>
      <QuestionPanel
        questions={pendingQuestion.questions}
        onSubmit={onQuestionSubmit!}
      />
    </div>
  ) : (
    // 既存の CopyAllButton + textarea + Send ボタン部分
    <>
      {messages.length > 0 && ( ... )}
      <div style={{ display: 'flex', alignItems: 'flex-end', ... }}>
        <textarea ... disabled={isInputDisabled} ... />
        <button ... />
      </div>
    </>
  )}
</div>
```

---

### `frontend/src/types.ts` (type-definition)

**Analog:** 自己参照（既存ファイルの変更）

**追加する型定義** (既存 CanvasResult 定義 lines 139-143 の後に追加):
```typescript
// CanvasResult (lines 139-143) と同様のパターンで追加:
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
```

---

### `frontend/src/components/ChatApp.tsx` (component, request-response)

**Analog:** 自己参照（既存ファイルの変更）

**useChat の返値受け取り変更** (ChatApp.tsx line 85-91):
```typescript
// 既存 (line 85)
const { isThinking, streamPreview, sendMessage, cancelJob } = useChat({ ... });
// ↓ 変更
const { isThinking, streamPreview, sendMessage, cancelJob, pendingQuestion, handleQuestionSubmit } = useChat({ ... });
```

**MessageArea への props 追加** (ChatApp.tsx lines 175-181):
```typescript
// 既存 (lines 175-181)
<MessageArea
  messages={messages}
  isThinking={isThinking}
  streamPreview={streamPreview}
  onSend={handleSend}
  onCancel={cancelJob}
/>
// ↓ 変更
<MessageArea
  messages={messages}
  isThinking={isThinking}
  streamPreview={streamPreview}
  onSend={handleSend}
  onCancel={cancelJob}
  pendingQuestion={pendingQuestion}
  onQuestionSubmit={handleQuestionSubmit}
/>
```

---

### `frontend/src/components/SuperChatApp.tsx` / `GemChatApp.tsx` / `CanvasChatApp.tsx` / `DebateChatApp.tsx` (component, request-response)

**Analog:** `frontend/src/components/ChatApp.tsx` の変更パターンをそのまま適用

**各アプリの変更パターン (ChatApp.tsx と同一)**:
1. `useChat(...)` の返値分割代入に `pendingQuestion, handleQuestionSubmit` を追加
2. `<MessageArea ... />` に `pendingQuestion={pendingQuestion}` と `onQuestionSubmit={handleQuestionSubmit}` を追加

SuperChatApp.tsx の useChat 呼び出し箇所は `sendMessage`, `cancelJob`, `isThinking`, `streamPreview`, `currentTool` を返値として使用するパターンが確立されているため、同様に拡張する。

---

### `app/jobs/handlers/langgraph_handler.py` (handler, request-response)

**Analog:** 自己参照（既存ファイルの変更）

**effective_system_prompt 構築箇所** (langgraph_handler.py lines 75-76):
```python
# 既存 (lines 75-76)
datetime_prefix = get_datetime_context()
effective_system_prompt = datetime_prefix + "\n\n" + (system_prompt or "")
```

**AUQ_PROTOCOL 定数の定義と注入**:
```python
# ファイル先頭（インポート後）に定数を追加:
AUQ_PROTOCOL = (
    "\n\n## 質問プロトコル\n\n"
    "ユーザーに確認が必要な場合、以下の <ask_user_question> フォーマットのみで応答すること。\n"
    "通常の会話文と混在させてはならない。\n\n"
    "<ask_user_question>\n"
    '{"questions": [{"question": "...", "header": "...", "type": "single"|"multi"|"text", '
    '"options": [{"label": "...", "description": "..."}], "allowFreeText": true, '
    '"placeholder": "...", "optional": true}]}\n'
    "</ask_user_question>"
)

# lines 75-76 を変更:
datetime_prefix = get_datetime_context()
effective_system_prompt = datetime_prefix + "\n\n" + (system_prompt or "") + AUQ_PROTOCOL
```

---

### `app/utils/system_prompt.py` (utility)

**Analog:** 自己参照（既存ファイルの変更）

**SECURITY_GUARDRAIL と同パターンで AUQ_PROTOCOL 定数を追加** (system_prompt.py lines 11-21):
```python
# 既存の SECURITY_GUARDRAIL (lines 11-21) と同じパターンで追加:
AUQ_PROTOCOL = (
    "\n\n## 質問プロトコル\n\n"
    "ユーザーに確認が必要な場合、以下の <ask_user_question> フォーマットのみで応答すること。\n"
    "通常の会話文と混在させてはならない。\n\n"
    "<ask_user_question>\n"
    "{\"questions\": [{\"question\": \"...\", \"header\": \"...\", "
    "\"type\": \"single\"|\"multi\"|\"text\", "
    "\"options\": [{\"label\": \"...\", \"description\": \"...\"}]}]}\n"
    "</ask_user_question>"
)

# build_system_prompt_prefix (lines 24-36) を変更:
def build_system_prompt_prefix(user_id: str | None) -> str:
    parts = [get_datetime_context()]
    if user_id:
        parts.append(f"ログイン中のユーザー: {user_id}")
    parts.append(SECURITY_GUARDRAIL)
    parts.append(AUQ_PROTOCOL)  # 追加
    return "\n".join(parts)
```

---

## Shared Patterns

### AUQ タグ正規表現
**Source:** `work/uaw/AskUserQuestion.jsx` line 4
**Apply to:** `useChat.ts` の parseJobResult catch ブロック、`QuestionPanel.tsx` の parseAUQ ユーティリティ
```typescript
const AUQ_RE = /<ask_user_question>([\s\S]*?)<\/ask_user_question>/;
```

### JSON ペイロード型分岐パターン
**Source:** `frontend/src/hooks/useChat.ts` lines 54-73
**Apply to:** parseJobResult の askUserQuestion 分岐追加
```typescript
// 既存パターン: try { JSON.parse → type フィールドで分岐 } catch { plain text }
// 新規: catch ブロック内で AUQ_RE によるタグ検出を追加
```

### インラインスタイル（ダークテーマ）
**Source:** `work/uaw/AskUserQuestion.jsx` lines 188-244 の S オブジェクト
**Apply to:** `QuestionPanel.tsx` のスタイル定義
- ダーク背景: `#0f0f11` / `#1a1a22` / `#131316`
- ボーダー: `#2a2a35` / `#1e1e24`
- テキスト: `#e8e8ec`
- 選択色（緑）: `#22c55e`
- 注意: `S.optionIndicator` は関数プロパティのため TypeScript 化時にヘルパー関数として取り出す

### 回答テキスト化パターン
**Source:** `work/uaw/Chat.jsx` lines 111-117
**Apply to:** `useChat.ts` の handleQuestionSubmit
```typescript
const text = Object.entries(answers)
  .filter(([, v]) => v)
  .map(([q, a]) => `${q}：${a}`)
  .join('\n');
```

### システムプロンプト定数パターン
**Source:** `app/utils/system_prompt.py` lines 11-21 (SECURITY_GUARDRAIL)
**Apply to:** `langgraph_handler.py` の AUQ_PROTOCOL 定数、`system_prompt.py` への AUQ_PROTOCOL 追加
```python
CONSTANT_NAME = (
    "行1\n"
    "行2\n"
    "..."
)
```

---

## No Analog Found

なし — 全ファイルに既存アナログが存在する。

---

## Critical Implementation Notes

### Pitfall 5: optionIndicator TypeScript 変換
`work/uaw/AskUserQuestion.jsx` の `S.optionIndicator` は関数プロパティであり `React.CSSProperties` に直接割り当て不可。`getOptionIndicatorStyle(type, selected, locked)` として独立したヘルパー関数に取り出す。

### Pitfall 4: system prompt 注入の2経路
- **LangGraph 経路**（Chat/GemChat/CanvasChat）: `langgraph_handler.py` の `effective_system_prompt` 末尾に `AUQ_PROTOCOL` を追加
- **Orchestrator 経路**（SuperChat）: `app/utils/system_prompt.py` の `build_system_prompt_prefix` に `AUQ_PROTOCOL` を追加
両方に追加しないと D-05/D-06 の全アプリ一律有効化が達成できない。

### Pitfall 3: 全 ChatApp への伝播
`pendingQuestion` / `handleQuestionSubmit` の props 追加は ChatApp.tsx / SuperChatApp.tsx / GemChatApp.tsx / CanvasChatApp.tsx / DebateChatApp.tsx の**全 5 ファイル**に適用する。

### Pitfall 1: plain text タグ検出
AI は `<ask_user_question>` タグを plain text として返す（JSON ラッパーなし）。`JSON.parse` の **catch ブロック**で AUQ_RE による検出を行う。

---

## Metadata

**Analog search scope:** `frontend/src/`, `app/jobs/handlers/`, `app/utils/`, `work/uaw/`
**Files scanned:** 12
**Pattern extraction date:** 2026-04-17
