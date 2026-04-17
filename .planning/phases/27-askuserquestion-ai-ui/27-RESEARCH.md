# Phase 27: AskUserQuestion の実装 - Research

**Researched:** 2026-04-17
**Domain:** Frontend インタラクション拡張（React + chatscope + useChat hook + Python system prompt）
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** 入力エリア置換パターン — 質問パネル表示時はテキスト入力欄を QuestionPanel に置き換え、高さは自動調整される（work/uaw/Chat.jsx のパターン踏襲）
- **D-02:** 質問パネルが未回答の間、テキスト入力欄は無効化する。「質問に回答してください」等のヒントを表示し、回答後に入力欄を復帰させる
- **D-03:** system prompt 駆動方式。AI レスポンスに `<ask_user_question>` タグで JSON を埋め込む方式。専用 API エンドポイントは追加しない
- **D-04:** ユーザーの回答はテキスト化して通常の POST /api/chat に送信する。「質問：回答」形式のテキストに変換し、既存のチャットフローをそのまま使う
- **D-05:** 全アプリ一律で有効化（Chat / SuperChat / GemChat / CanvasChat / DebateChat）。useChat の共通ロジック（parseJobResult 拡張）で対応
- **D-06:** 質問プロトコルは共通ベースレベルで注入。LangGraphHandler / OrchestratorHandler の共通システムプロンプトに追加し、全エージェントが質問可能な状態にする
- **D-07:** 回答済み質問パネルはスレッド履歴に残さない。回答はテキスト化して通常ユーザーメッセージとして送信
- **D-08:** スレッド再開時の復元はテキストメッセージとして行う（追加実装不要）

### Claude's Discretion

- QuestionPanel の TypeScript 化・スタイリング詳細（ダークテーマ適合）
- parseJobResult での `ask_user_question` 検出ロジックの具体的実装
- system prompt への質問プロトコル追記の文言調整

### Deferred Ideas (OUT OF SCOPE)

なし — ディスカッションはフェーズスコープ内に留まった

</user_constraints>

---

## Summary

Phase 27 は、AI エージェントがユーザーに構造化質問（single/multi/text）を提示する **AskUserQuestion** パターンを既存アーキテクチャに統合する。参考実装 `work/uaw/` は完成度が高く、TypeScript 変換と既存フックへの統合が主要作業となる。

バックエンドへの変更は最小限。LangGraphHandler と OrchestratorHandler の system prompt に質問プロトコル仕様を追記するだけで全エージェントが `<ask_user_question>` タグを使えるようになる。フロントエンドは `parseJobResult()` の拡張（ask_user_question タイプ追加）、`MessageArea.tsx` の入力エリア条件付き置換、`QuestionPanel.tsx` 新規コンポーネント作成の 3 点が核心。

**Primary recommendation:** work/uaw/AskUserQuestion.jsx を TypeScript 化した `QuestionPanel.tsx` を作成し、useChat の `pendingQuestion` 状態と handleQuestionSubmit コールバックを全 ChatApp コンポーネントに伝播させる形で実装する。

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `<ask_user_question>` タグ生成 | API / Backend | — | system prompt 制御は worker 側責務。LangGraphHandler/OrchestratorHandler の effective_system_prompt に追記 |
| レスポンス解析（タグ検出） | Frontend Server（useChat hook） | — | parseJobResult() は hook 内関数。バックエンド変換不要 |
| 質問パネル表示（UI） | Browser / Client | — | QuestionPanel は純粋 React コンポーネント、状態は useState |
| 入力エリア置換 | Browser / Client | — | MessageArea の条件レンダリング。pendingQuestion prop で制御 |
| 回答テキスト化・送信 | Browser / Client | — | handleQuestionSubmit が「質問：回答」形式に変換後 sendMessage 呼び出し |

---

## Standard Stack

### Core（すでに導入済み）

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 19 | コンポーネントツリー | プロジェクト標準 |
| TypeScript | 5.x | 型安全 | プロジェクト標準 |
| @chatscope/chat-ui-kit-react | — | チャット UI | Phase 7 以降のプロジェクト標準 |

### 新規追加なし

QuestionPanel は外部ライブラリ不要。work/uaw/AskUserQuestion.jsx の参考実装がインラインスタイルで完結しており、外部 CSS ライブラリへの依存を持たない。TypeScript 化のみで流用可能。

---

## Architecture Patterns

### System Architecture Diagram

```
AI レスポンス (raw string)
        |
        v
  parseJobResult()          ← useChat.ts 内関数を拡張
  try JSON.parse             |
  type === 'ask_user_question' ──→ setPendingQuestion(auq)
  type === 'canvas'          ──→ onCanvasResponse(...)
  type === 'debate_result'   ──→ onDebateResult(...)
  plain text                 ──→ setMessages(AI bubble)
        |
        v (pendingQuestion != null)
  MessageArea.tsx
  入力エリア条件分岐
  ┌─ pendingQuestion あり ──→ <QuestionPanel onSubmit={handleQuestionSubmit} />
  └─ pendingQuestion なし ──→ <textarea> (通常入力)
        |
        v (ユーザー回答送信)
  handleQuestionSubmit(answers)
  → テキスト化（「質問：回答\n...」）
  → sendMessage(text)        ← 既存フロー完全流用
  → setPendingQuestion(null)
```

### Recommended Project Structure

```
frontend/src/
  components/
    QuestionPanel.tsx        # 新規作成（work/uaw/AskUserQuestion.jsx の TS 変換）
    MessageArea.tsx          # 変更：pendingQuestion prop 追加、入力エリア条件置換
    ChatApp.tsx              # 変更：pendingQuestion/handleQuestionSubmit を useChat から受け取り MessageArea に渡す
    SuperChatApp.tsx         # 同上
    GemChatApp.tsx           # 同上
    CanvasChatApp.tsx        # 同上
    DebateChatApp.tsx        # 同上
  hooks/
    useChat.ts               # 変更：parseJobResult 拡張、pendingQuestion 状態追加、返値に追加

app/jobs/handlers/
  langgraph_handler.py       # 変更：effective_system_prompt に AUQ プロトコル追記
  orchestrator_handler.py    # 変更：SubAgent system prompt prefix に AUQ プロトコル追記（app/utils/system_prompt.py 経由が適切）
```

### Pattern 1: parseJobResult 拡張（useChat.ts）

**What:** ask_user_question タイプを既存の JSON ペイロード検出パターンに追加する
**When to use:** AI レスポンスの raw string 解析時（Phase 15/17 で確立済みパターン）

```typescript
// Source: [VERIFIED: 既存コード frontend/src/hooks/useChat.ts:53-74 を拡張]

// 新規型定義
interface AskUserQuestion {
  questions: AUQQuestion[];
}
interface AUQQuestion {
  question: string;
  header: string;
  type?: 'single' | 'multi' | 'text';
  options?: Array<{ label: string; description?: string }>;
  allowFreeText?: boolean;
  placeholder?: string;
  optional?: boolean;
}

// parseJobResult の戻り値型を拡張
function parseJobResult(raw: string): {
  text: string;
  canvas: CanvasResult | null;
  debate: DebateResult | null;
  agentName: string | null;
  askUserQuestion: AskUserQuestion | null;  // 追加
} {
  try {
    const parsed = JSON.parse(raw);
    // ... 既存 canvas / debate_result / orchestrator_result ...
  } catch {
    // plain text でも <ask_user_question> タグが含まれる場合の検出
    const m = raw.match(/<ask_user_question>([\s\S]*?)<\/ask_user_question>/);
    if (m) {
      try {
        const auq = JSON.parse(m[1].trim()) as AskUserQuestion;
        return { text: '', canvas: null, debate: null, agentName: null, askUserQuestion: auq };
      } catch {
        // JSON パース失敗 → plain text として返す
      }
    }
  }
  return { text: raw, canvas: null, debate: null, agentName: null, askUserQuestion: null };
}
```

**重要な注意点（[VERIFIED: work/uaw/AskUserQuestion.jsx:4-9]）:**
AI は `<ask_user_question>` タグを **plain text として** 返す（JSON の外側にタグがある）。
つまり `parseJobResult` の `JSON.parse` が失敗した後にタグを検出する必要がある。
既存の `try { JSON.parse } catch { plain text }` のブロックを拡張する形が正しい。

### Pattern 2: useChat 返値拡張

**What:** pendingQuestion 状態と handleQuestionSubmit を useChat から返す
**When to use:** 全 ChatApp コンポーネントが統一インターフェースで質問状態を取得できるよう

```typescript
// Source: [ASSUMED / work/uaw/Chat.jsx:111-118 のパターンを踏襲]

// useChat の UseChatReturn インターフェースに追加
interface UseChatReturn {
  isThinking: boolean;
  currentTool: {tool: string; query: string} | null;
  streamPreview: string;
  sendMessage: (text: string, threadId?: string, contextMessages?: ContextMessage[]) => Promise<void>;
  cancelJob: () => void;
  pendingQuestion: AskUserQuestion | null;            // 追加
  handleQuestionSubmit: (answers: Record<string, string>) => void;  // 追加
}

// useChat 内部実装
const [pendingQuestion, setPendingQuestion] = useState<AskUserQuestion | null>(null);

// handleResult 内で askUserQuestion を検出したら setPendingQuestion
// handleQuestionSubmit は answers をテキスト化して sendMessage を呼ぶ
const handleQuestionSubmit = useCallback((answers: Record<string, string>) => {
  setPendingQuestion(null);
  const text = Object.entries(answers)
    .filter(([, v]) => v)
    .map(([q, a]) => `${q}：${a}`)
    .join('\n');
  sendMessage(text);
}, [sendMessage]);
```

### Pattern 3: MessageArea 入力エリア置換

**What:** pendingQuestion の有無で入力エリアを QuestionPanel と textarea の間で切り替え
**When to use:** D-01/D-02 の入力エリア置換パターン

```typescript
// Source: [VERIFIED: work/uaw/Chat.jsx:142-160 のパターンをチャットスコープ版に移植]

// MessageArea の props に追加
interface MessageAreaProps {
  // ...既存...
  pendingQuestion?: AskUserQuestion | null;
  onQuestionSubmit?: (answers: Record<string, string>) => void;
}

// 入力エリア部分のレンダリング
{pendingQuestion ? (
  <div className="chat-input-bar" style={{ ... }}>
    <QuestionPanel
      questions={pendingQuestion.questions}
      onSubmit={onQuestionSubmit!}
    />
  </div>
) : (
  // 既存の textarea + Send ボタン
  <div className="chat-input-bar" style={{ ... }}>
    ...
  </div>
)}
```

### Pattern 4: バックエンド system prompt 注入

**What:** LangGraphHandler の effective_system_prompt と SubAgent の build_system_prompt_prefix に質問プロトコルを追記
**When to use:** 全エージェントが AUQ タグを生成できるよう

```python
# Source: [VERIFIED: app/jobs/handlers/langgraph_handler.py:75-82]

# langgraph_handler.py — effective_system_prompt 構築時に AUQ プロトコルを末尾追加
AUQ_SYSTEM_PROMPT = """
## 質問プロトコル

ユーザーに確認が必要な場合、以下の <ask_user_question> フォーマットのみで応答すること。
通常の会話文と混在させてはならない。

<ask_user_question>
{
  "questions": [
    {
      "question": "質問テキスト",
      "header": "ラベル（12文字以内）",
      "type": "single" | "multi" | "text",
      "options": [ { "label": "選択肢", "description": "補足説明" } ],
      "allowFreeText": true,
      "placeholder": "入力例",
      "optional": true
    }
  ]
}
</ask_user_question>
"""

effective_system_prompt = datetime_prefix + "\n\n" + (system_prompt or "") + "\n\n" + AUQ_SYSTEM_PROMPT
```

```python
# Source: [VERIFIED: app/utils/system_prompt.py — build_system_prompt_prefix を拡張]
# OrchestratorHandler 経由の SubAgent には build_system_prompt_prefix + "\n\n" + AUQ_SYSTEM_PROMPT
# または system_prompt.py の SECURITY_GUARDRAIL と同じパターンで AUQ 仕様を定数として追加
```

### Anti-Patterns to Avoid

- **plain text 前提でタグ検出をしない:** AI は `<ask_user_question>` タグを JSON ではなく plain text として返す。`JSON.parse` が成功した場合でもタグを含む可能性があるが、system prompt で「タグのみで応答すること」を強制するため JSON ラッパーは発生しない
- **isPending チェックを MessageArea 内で完結させない:** `pendingQuestion` 状態は useChat で管理し、sendMessage による次のサイクルで自然にクリアされる。MessageArea が独自状態を持つと送信完了タイミングの不整合が起きる
- **回答済みパネルのロック表示:** D-07 の決定により locked 表示は不要。AskUserQuestion.jsx にある `locked`/`lockedAnswers` props は TypeScript 化時に含めなくてよい（または optional として残す）
- **各 ChatApp に個別の parseAUQ 実装:** parseJobResult の共通関数で一元管理する。各アプリ個別実装は禁止

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| タグパーサー | 独自正規表現実装 | work/uaw/AskUserQuestion.jsx の `AUQ_RE` パターン流用 | 既存の検証済み実装がある |
| 質問パネル UI | 独自コンポーネント設計 | work/uaw/AskUserQuestion.jsx を TypeScript 化 | 完成度の高い参考実装が存在する |
| 回答テキスト化 | 独自フォーマット | `${q}：${a}` パターン（work/uaw/Chat.jsx:113-117） | AI が読みやすい形式として設計済み |

**Key insight:** work/uaw/ ディレクトリの参考実装は本フェーズのためにすでに設計・検証されている。ゼロから実装する必要はない。

---

## Common Pitfalls

### Pitfall 1: AI レスポンスが `<ask_user_question>` タグを含む plain text として返る

**What goes wrong:** JSON.parse でパースしようとして失敗し、plain text として表示されてしまう
**Why it happens:** system prompt の指示で AI はタグをそのままテキストに埋め込む（JSON ラッパーなし）
**How to avoid:** parseJobResult の catch ブロックで `AUQ_RE` によるタグ検出を追加する
**Warning signs:** チャット画面に `<ask_user_question>{...}</ask_user_question>` がそのまま表示される

### Pitfall 2: pendingQuestion と isThinking の競合

**What goes wrong:** AI が考え中（isThinking=true）の間に質問パネルが表示される、またはその逆
**Why it happens:** SSE イベント done を受けてから handleResult が呼ばれ、そこで setPendingQuestion が呼ばれる。順序は正しいが、isThinking の false 設定前後のレンダリングで一瞬ちらつく可能性
**How to avoid:** handleResult 呼び出し後に setIsThinking(false) を呼ぶ既存の順序を維持する。pendingQuestion が null でなければ isThinking は必ず false のはず
**Warning signs:** 質問パネルとローディングアニメーションが同時表示される

### Pitfall 3: 各 ChatApp コンポーネントへの伝播漏れ

**What goes wrong:** ChatApp.tsx のみ対応し、SuperChatApp / GemChatApp / CanvasChatApp / DebateChatApp が未対応で質問パネルが表示されない
**Why it happens:** D-05 で全アプリ一律有効化が決定されているが、実装時に見落としやすい
**How to avoid:** 全 5 アプリコンポーネントを一括でチェックするタスク設計にする
**Warning signs:** SuperChat や GemChat で `<ask_user_question>` テキストがそのまま表示される

### Pitfall 4: system_prompt.py か langgraph_handler.py どちらに追記するか

**What goes wrong:** LangGraph（Gem/Canvas）と Orchestrator（SuperChat）で異なる経路にあるため、片方にしか追記せず、もう片方が AUQ を使えない
**Why it happens:** LangGraphHandler は `effective_system_prompt` を自前で構築し、Orchestrator は `build_system_prompt_prefix()` 経由
**How to avoid:**
  - LangGraphHandler: `effective_system_prompt` 末尾に AUQ プロトコルを追記
  - `app/utils/system_prompt.py` の `build_system_prompt_prefix` か、SubAgent の system_prompt 注入部分に AUQ プロトコルを追記
**Warning signs:** Chat/GemChat では機能するが SuperChat では機能しない（または逆）

### Pitfall 5: TypeScript 変換時の optionIndicator 関数スタイル

**What goes wrong:** インラインスタイルオブジェクト内の関数 `optionIndicator: (type, selected, locked) => (...)` は TypeScript の `CSSProperties` 型に直接アサインできない
**Why it happens:** work/uaw/AskUserQuestion.jsx の `S` オブジェクトは関数プロパティを含む
**How to avoid:** `optionIndicator` は独立したヘルパー関数として取り出し、JSX 内でインラインスタイルに直接適用する
**Warning signs:** TypeScript コンパイルエラー（型不一致）

---

## Code Examples

### AskUserQuestion.tsx 型定義

```typescript
// Source: [VERIFIED: work/uaw/AskUserQuestion.jsx:1-9 を TypeScript 化]

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

const AUQ_RE = /<ask_user_question>([\s\S]*?)<\/ask_user_question>/;

export function parseAUQ(text: string): AskUserQuestionPayload | null {
  const m = text.match(AUQ_RE);
  if (!m) return null;
  try { return JSON.parse(m[1].trim()) as AskUserQuestionPayload; }
  catch { return null; }
}
```

### handleResult 内での AUQ 検出（useChat.ts）

```typescript
// Source: [ASSUMED / 既存パターンを拡張]
const handleResult = (raw: string) => {
  const { text: resultText, canvas, debate, agentName, askUserQuestion } = parseJobResult(raw);
  if (askUserQuestion) {
    setPendingQuestion(askUserQuestion);
    // AI メッセージバブルは表示しない（質問パネルのみ）
  } else if (canvas && onCanvasResponse) {
    // ... 既存
  } else {
    // ... 既存
  }
};
```

### system_prompt.py への AUQ_PROTOCOL 追加

```python
# Source: [VERIFIED: app/utils/system_prompt.py の SECURITY_GUARDRAIL パターンを踏襲]

AUQ_PROTOCOL = (
    "## 質問プロトコル\n\n"
    "ユーザーに確認が必要な場合、以下の <ask_user_question> フォーマットのみで応答すること。\n"
    "通常の会話文と混在させてはならない。\n\n"
    "<ask_user_question>\n"
    '{"questions": [{"question": "...", "header": "...", "type": "single"|"multi"|"text", '
    '"options": [{"label": "...", "description": "..."}]}]}\n'
    "</ask_user_question>"
)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 専用 API エンドポイントで質問状態管理 | system prompt 駆動 + parseJobResult タグ検出 | D-03 決定（Phase 27） | バックエンド API 追加不要、既存 SSE フローを完全流用 |
| 質問パネルを独立 UI レイヤーで表示 | 入力エリア置換パターン | D-01 決定（Phase 27） | 実装シンプル、スクロール不要 |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `handleQuestionSubmit` を useChat 内で定義し返値として公開するアプローチ | Pattern 2 | 各 ChatApp が sendMessage を直接呼ぶ設計でも動作するが、DRY 違反になる |
| A2 | OrchestratorHandler の SubAgent system prompt に AUQ プロトコルを追加する場合、`app/utils/system_prompt.py` の `build_system_prompt_prefix` に追記するか、handler 内で直接追記するかは実装時に判断 | Pattern 4 | どちらでも機能するが一方は全 SubAgent に影響する |
| A3 | AI は system prompt 指示通り `<ask_user_question>` タグを plain text として返し、JSON ラッパーには入れない | Pattern 1（タグ検出） | JSON ラッパーに入れた場合は parseJobResult の try ブロック内でも検出できるよう両方対応が安全 |

---

## Open Questions

1. **OrchestratorHandler の AUQ system prompt 注入先**
   - What we know: `build_system_prompt_prefix()` は全 SubAgent に適用される（`tool_agent.py:183`）
   - What's unclear: AUQ プロトコルを全 SubAgent に追加したいか（D-06 は「全エージェント」と明言）vs. 特定エージェントのみ
   - Recommendation: `build_system_prompt_prefix()` に追加し全エージェント一律有効化（D-06 に合致）

2. **streaming=True の場合、AI が `<ask_user_question>` タグをトークン分割して SSE に流す際の streamPreview 表示**
   - What we know: streamPreview は最大 200 文字の末尾保持。タグが途中で切れると不完全表示になる
   - What's unclear: タグを含む応答の streamPreview がユーザー体験として問題になるか
   - Recommendation: 問題になる場合は、streamPreview 表示時にタグが含まれる場合は非表示にする処理を追加する（低優先度）

---

## Environment Availability

Step 2.6: SKIPPED（外部ツール・サービス依存なし — フロントエンド TypeScript + Python コード変更のみ）

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest（バックエンド）/ TypeScript tsc（フロントエンド） |
| Config file | pyproject.toml（pytest）/ tsconfig.json（tsc） |
| Quick run command | `docker compose exec api python -m pytest tests/ -x -q` |
| Full suite command | `docker compose exec api python -m pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUQ-01 | parseJobResult が ask_user_question タイプを正しく検出する | unit | `pytest tests/test_parse_job_result.py -x` | ❌ Wave 0 |
| AUQ-02 | QuestionPanel が single/multi/text 質問タイプをレンダリングする | manual（ブラウザ確認） | — | N/A |
| AUQ-03 | handleQuestionSubmit が正しい「質問：回答」テキストを生成する | unit | フロントエンド型チェックのみ | N/A（TSなので型保証） |
| AUQ-04 | LangGraphHandler が AUQ system prompt を含む effective_system_prompt を生成する | unit | `pytest tests/test_langgraph_handler.py -x` | ❌ Wave 0 |

**注記:** AUQ のコア機能（タグ検出・テキスト変換）はフロントエンド Hook 内の純粋関数として実装されるため、Jest/vitest での単体テストが理想的だが、本プロジェクトのフロントエンドテスト環境は未整備（Phase 7 以降テストなし）。TypeScript コンパイルによる型チェックを代替とし、動作確認はブラウザ手動テストで行う。

### Wave 0 Gaps

- [ ] `tests/test_auq_system_prompt.py` — LangGraphHandler の effective_system_prompt に AUQ プロトコルが含まれることを確認（REQ AUQ-04）
- [ ] parseJobResult の TypeScript テストは環境なしのため省略（型チェックで代替）

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | ユーザー回答テキストは通常の sendMessage 経由で送信されるため、既存の入力バリデーションがそのまま適用される |
| V6 Cryptography | no | — |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| AI 生成 JSON のパース（`<ask_user_question>` タグ内容） | Tampering | try-catch で不正 JSON を無視。パース失敗は plain text として扱う |
| ユーザー回答のテキスト化 | — | Object.entries のフィルタで空値除去。XSS リスクなし（sendMessage 経由の既存フロー）|

---

## Sources

### Primary (HIGH confidence)

- `work/uaw/AskUserQuestion.jsx` — QuestionPanel 完全実装（parseAUQ, QuestionPanel コンポーネント、スタイル定義）[VERIFIED: 直接読み取り]
- `work/uaw/Chat.jsx` — handleQuestionSubmit パターン（テキスト化送信）[VERIFIED: 直接読み取り]
- `work/uaw/system_prompt_auq.md` — `<ask_user_question>` プロトコル仕様（フォーマット・ルール）[VERIFIED: 直接読み取り]
- `frontend/src/hooks/useChat.ts` — parseJobResult 拡張先、UseChatReturn インターフェース [VERIFIED: 直接読み取り]
- `frontend/src/components/MessageArea.tsx` — 入力エリア条件置換の実装先 [VERIFIED: 直接読み取り]
- `app/jobs/handlers/langgraph_handler.py` — effective_system_prompt 構築パターン [VERIFIED: 直接読み取り]
- `app/utils/system_prompt.py` — build_system_prompt_prefix / SECURITY_GUARDRAIL パターン [VERIFIED: 直接読み取り]

### Secondary (MEDIUM confidence)

- `frontend/src/types.ts` — ChatMessage / AskUserQuestionPayload 追加先 [VERIFIED: 直接読み取り]
- `app/jobs/handlers/orchestrator_handler.py` — SubAgent system prompt 注入フロー確認 [VERIFIED: 直接読み取り]
- `.planning/patterns.md` — Token Streaming 3 層配管パターン、parseJobResult の Phase 15/17 確立パターン [VERIFIED: 直接読み取り]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — 既存コードを流用・拡張する実装のため
- Architecture: HIGH — 参考実装（work/uaw/）と既存コード（useChat.ts, MessageArea.tsx）の両方を確認済み
- Pitfalls: HIGH — コードを実際に読んで具体的な落とし穴を特定済み

**Research date:** 2026-04-17
**Valid until:** 2026-05-17（安定した既存コードベース拡張のため）
