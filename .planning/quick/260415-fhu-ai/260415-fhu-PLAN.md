---
phase: quick-260415-fhu
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/providers/copilot.py
  - app/jobs/notifier.py
  - app/jobs/job_store.py
  - app/jobs/handlers/langgraph_handler.py
  - frontend/src/hooks/useChat.ts
  - frontend/src/components/MessageArea.tsx
  - frontend/src/components/ChatApp.tsx
autonomous: false
requirements:
  - QUICK-260415-FHU
user_setup: []

must_haves:
  truths:
    - "ユーザーがチャットを送信すると 3ドットアニメーションの下にストリーミング中のテキストプレビューが表示される"
    - "最終的な AI 応答は従来通り 1 つの完成メッセージとしてチャット履歴に追加される"
    - "ストリーミング中に接続が切れても従来のジョブ完了フローが動作する（退行なし）"
  artifacts:
    - path: "app/providers/copilot.py"
      provides: "ChatCopilot._astream — session.on() + asyncio.Queue で delta を yield する AsyncIterator[ChatGenerationChunk]"
    - path: "app/jobs/notifier.py"
      provides: "Notifier.send_token(token) — SSE キューへ {status: 'token', token} を enqueue"
    - path: "app/jobs/handlers/langgraph_handler.py"
      provides: "graph.astream_events(version='v2') で on_chat_model_stream を捕捉し notifier.send_token 経由で転送"
    - path: "frontend/src/hooks/useChat.ts"
      provides: "SSE token イベントハンドラ + streamPreview state（最大 200 文字）"
    - path: "frontend/src/components/MessageArea.tsx"
      provides: "streamPreview prop を受け取り 3 ドット下に truncated text を表示"
  key_links:
    - from: "app/providers/copilot.py ChatCopilot._astream"
      to: "langchain-core BaseChatModel streaming protocol"
      via: "AsyncIterator[ChatGenerationChunk] yield"
      pattern: "async def _astream"
    - from: "app/jobs/handlers/langgraph_handler.py"
      to: "app/jobs/notifier.py send_token"
      via: "astream_events on_chat_model_stream ハンドリング"
      pattern: "astream_events.*on_chat_model_stream"
    - from: "frontend/src/hooks/useChat.ts"
      to: "frontend/src/components/MessageArea.tsx"
      via: "streamPreview prop"
      pattern: "streamPreview"
---

<objective>
AI 応答のトークンストリーミングプレビューを実装する。Copilot SDK の `ASSISTANT_MESSAGE_DELTA` イベントを `ChatCopilot._astream` で AsyncIterator 化し、LangGraph の `astream_events` 経由で SSE `token` イベントとしてフロントに送る。フロントは 3 ドットアニメーションの下に受信中のテキスト（最大 200 文字）をプレビュー表示し、完了時には従来通り完成メッセージを履歴に追加する。

Purpose: ユーザーは現状 AI の応答完了まで 3 ドットしか見えず、長い応答（Canvas HTML 生成等）でフィードバックが乏しい。ストリーミングプレビューで「生きている感」と進捗可視化を得る。

Output: バックエンドは Copilot SDK → LangGraph → Notifier → SSE の一貫したトークンストリームパス、フロントは `streamPreview` state とプレビュー UI。
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@app/providers/copilot.py
@app/jobs/notifier.py
@app/jobs/job_store.py
@app/jobs/handlers/langgraph_handler.py
@frontend/src/hooks/useChat.ts
@frontend/src/components/MessageArea.tsx
@frontend/src/components/ChatApp.tsx

<interfaces>
<!-- 既存の Copilot SDK / LangChain / Notifier 契約。調査で確認済み。 -->

From github_copilot_sdk:
```python
from github_copilot_sdk.session import SessionEventType
# SessionEventType.ASSISTANT_MESSAGE_DELTA = 'assistant.message_delta'
# SessionEventType.SESSION_IDLE = 'session.idle'
# event.data.delta_content  # incremental text for delta event
# session.on(handler)       # register event handler
# session.send(prompt)      # non-blocking send
```

From langchain_core.outputs:
```python
from langchain_core.outputs import ChatGenerationChunk
from langchain_core.messages import AIMessageChunk
# ChatGenerationChunk(message=AIMessageChunk(content=token))
```

From app/jobs/notifier.py (existing):
```python
class Notifier:
    def __init__(self, reply_to: str, job_store: JobStore): ...
    async def progress(self, message: str) -> None: ...
    async def send_turn(self, agent: str, content: str) -> None: ...
    async def done(self) -> None: ...
```

From app/jobs/job_store.py (existing):
```python
class JobStore:
    async def notify(self, job_id: str, status: str, **extra) -> None: ...
    # Puts {"status": status, **extra} onto SSE queue
```

From frontend/src/hooks/useChat.ts (existing SSE handler):
```typescript
// processes: 'message', 'tool_executing', 'done'
// EventSource at /api/job/{id}/stream
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: ChatCopilot._astream 実装 + Notifier.send_token 追加</name>
  <files>app/providers/copilot.py, app/jobs/notifier.py, app/jobs/job_store.py</files>
  <action>
バックエンドのストリーミング基盤を整備する。

1. **app/providers/copilot.py** — `ChatCopilot` に `_astream` メソッドを追加:
   - シグネチャ: `async def _astream(self, messages, stop=None, run_manager=None, **kwargs) -> AsyncIterator[ChatGenerationChunk]`
   - 実装パターン（調査で確定済み）:
     - `asyncio.Queue[str | None]` を作成（None = 完了シグナル）
     - `SessionEventType.ASSISTANT_MESSAGE_DELTA` ハンドラで `event.data.delta_content` を queue.put
     - `SessionEventType.SESSION_IDLE` ハンドラで queue.put(None)
     - `session.on(handler)` で登録してから `session.send(prompt)` を呼ぶ（非ブロッキング）
     - `while True: token = await queue.get(); if token is None: break; yield ChatGenerationChunk(message=AIMessageChunk(content=token))`
   - エラーハンドリング: 既存 `_agenerate` と同じく例外時は `self._client = None` にリセットして re-raise
   - プロンプト整形は `_agenerate` の既存ロジックを共通化（`_build_prompt(messages)` に抽出してもよい）
   - import: `from langchain_core.outputs import ChatGenerationChunk`, `from langchain_core.messages import AIMessageChunk`, `AsyncIterator` from `typing`
   - **注意**: `_agenerate` は削除せず残す（fallback および非ストリーミング経路のため）

2. **app/jobs/notifier.py** — `send_token` メソッド追加:
   ```python
   async def send_token(self, token: str) -> None:
       await self._job_store.notify(self._reply_to, status="token", token=token)
   ```

3. **app/jobs/job_store.py** — 既存の `notify(job_id, status, **extra)` がそのまま `token` を受け付けるか確認。extra フィールドをそのまま SSE event の JSON に含める実装なら変更不要。含めない実装なら `token` フィールドを伝搬するよう修正。

**避けるべき点**:
- `session.send_and_wait` を `_astream` で使わないこと（ブロッキングで delta が取れない）
- `session.on()` の登録を `send()` の後にしないこと（初期 delta を取り逃す）
- `_astream` 内で `self._client` を作り直さないこと（既存の auth/client ライフサイクル踏襲）

**なぜ**: LangGraph の `astream_events(version="v2")` は `BaseChatModel._astream` が実装されていれば自動で `on_chat_model_stream` イベントを発火するため、ここさえ実装すれば handler 側で低侵襲にフックできる。
  </action>
  <verify>
    <automated>cd /home/parallels/workspaces/copilot-langgraph && docker compose exec -T api python -c "from app.providers.copilot import ChatCopilot; import inspect; assert inspect.isasyncgenfunction(ChatCopilot._astream), '_astream must be async generator'; from app.jobs.notifier import Notifier; assert hasattr(Notifier, 'send_token'), 'send_token missing'; print('OK')"</automated>
  </verify>
  <done>
- `ChatCopilot._astream` が async generator として存在し、import エラーなし
- `Notifier.send_token` が存在
- 既存の `_agenerate` は無変更（もしくは `_build_prompt` 抽出のみのリファクタ）で動作
  </done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: langgraph_handler で astream_events → send_token 配管</name>
  <files>app/jobs/handlers/langgraph_handler.py</files>
  <action>
`LangGraphHandler.handle` 内で現在 `await graph.ainvoke(state, config)` している箇所を以下に置き換える:

```python
final_state = None
async for event in graph.astream_events(state, config=config, version="v2"):
    kind = event.get("event")
    if kind == "on_chat_model_stream":
        chunk = event["data"].get("chunk")
        token = getattr(chunk, "content", None) if chunk is not None else None
        if token:
            await notifier.send_token(token)
    elif kind == "on_chain_end" and event.get("name") == "LangGraph":
        final_state = event["data"].get("output")

if final_state is None:
    # fallback: re-run with ainvoke if astream_events did not surface root output
    final_state = await graph.ainvoke(state, config=config)
```

**要点**:
- `astream_events(version="v2")` は既存の `ainvoke` と同じ最終状態を生成する。ルートノードの `on_chain_end` から output を取る
- `on_chat_model_stream` は `ChatCopilot._astream` が Task 1 で実装された時点で自動発火
- `chunk.content` が空文字（delta なし）の場合はスキップ
- 例外時はこれまで通り `notifier.done()` を finally で呼ぶ既存フローに任せる
- Canvas / SuperChat 等で本 handler を共有している場合も同じ仕組みが効くので影響範囲を考慮する必要はない（SSE に余分な `token` イベントが流れるだけで、既存フロントは無視する）
- `process_chat` の `save_result` は `final_state` を使って従来通り実行する

**避けるべき点**:
- `astream` と `astream_events` を混同しない（後者はノード単位イベント、前者は状態差分）
- token を batching しない（即時フラッシュでプレビューのライブ感を維持）
  </action>
  <verify>
    <automated>cd /home/parallels/workspaces/copilot-langgraph && docker compose exec -T api python -c "import ast, pathlib; src = pathlib.Path('app/jobs/handlers/langgraph_handler.py').read_text(); assert 'astream_events' in src and 'on_chat_model_stream' in src and 'send_token' in src, 'handler not wired'; ast.parse(src); print('OK')"</automated>
  </verify>
  <done>
- `langgraph_handler.py` が `astream_events(version="v2")` を使用
- `on_chat_model_stream` 時に `notifier.send_token(token)` を呼ぶ
- 最終状態を取得して既存 `save_result` フローが動作
- Python 構文エラーなし
  </done>
</task>

<task type="auto" tdd="false">
  <name>Task 3: フロント useChat + MessageArea で streamPreview 表示</name>
  <files>frontend/src/hooks/useChat.ts, frontend/src/components/MessageArea.tsx, frontend/src/components/ChatApp.tsx</files>
  <action>
フロントに SSE `token` イベント処理とプレビュー表示を実装する。

1. **frontend/src/hooks/useChat.ts**:
   - `const [streamPreview, setStreamPreview] = useState<string>("")` を追加
   - SSE `onmessage` ハンドラに新 case 追加:
     ```ts
     if (data.status === 'token') {
       setStreamPreview(prev => {
         const next = prev + (data.token ?? '');
         // 末尾 200 文字だけ保持（DOM 肥大化防止）
         return next.length > 200 ? next.slice(-200) : next;
       });
       return;
     }
     ```
   - `done` / エラー / 新メッセージ送信時に `setStreamPreview("")` でクリア
   - フックの戻り値に `streamPreview` を追加してエクスポート

2. **frontend/src/components/MessageArea.tsx**:
   - props に `streamPreview?: string` を追加
   - 既存の TypingIndicator（`isThinking` で表示）の直下にプレビュー要素を追加:
     - 条件: `isThinking && streamPreview`
     - 表示: 小さめのフォント、`color: var(--text-secondary)`、`white-space: pre-wrap`、`max-height: 3em; overflow: hidden`
     - 内容: `streamPreview`（必要なら先頭「…」で省略記号を付ける）
   - chatscope の TypingIndicator が JSX 子を受け付けない場合は、MessageList の外側/下に独自 div を重ねる（既存の typingIndicator prop 配置は壊さない）

3. **frontend/src/components/ChatApp.tsx**:
   - `useChat` から `streamPreview` を受け取り、`<MessageArea streamPreview={streamPreview} ... />` に渡す
   - SuperChat / Canvas / DebateChat 等が同じ MessageArea を共有していても、プレビュー表示条件 `isThinking && streamPreview` を満たすときだけ出るので無害。必要なら他のチャット画面にも同じく prop を渡して統一挙動にする（最低限 ChatApp だけで完結してよい）

**避けるべき点**:
- preview 文字列を無制限に蓄積しない（200 文字上限は DOM / React reconciliation 負荷対策）
- Markdown レンダリングしない（プレビューは plain text、完成時に従来の MarkdownMessage で描画）
- done イベントで preview クリアを忘れない（次ターンに古いプレビューが残る不具合）
  </action>
  <verify>
    <automated>cd /home/parallels/workspaces/copilot-langgraph && docker compose exec -T frontend bunx tsc --noEmit --project tsconfig.json 2>&1 | tail -20 || cd frontend && bunx tsc --noEmit --project tsconfig.json 2>&1 | tail -20</automated>
  </verify>
  <done>
- `useChat` が `token` SSE イベントを処理し `streamPreview` state を返す
- `MessageArea` が `streamPreview` prop を受け取り 3 ドット下に表示
- `ChatApp` が配線済み
- TypeScript 型チェック pass
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>
Copilot SDK ASSISTANT_MESSAGE_DELTA → ChatCopilot._astream → LangGraph astream_events(on_chat_model_stream) → Notifier.send_token → SSE `token` イベント → useChat streamPreview → MessageArea プレビュー表示、という一貫したストリーミング配管。
  </what-built>
  <how-to-verify>
1. `docker compose up -d` で起動（api / worker / frontend すべて）
2. ブラウザで `http://localhost:5173/orochi/` を開きログイン
3. Chat アプリを選択して新スレッドを作成
4. 「100文字程度で自己紹介してください」のような少し長めの返答を要求する質問を送信
5. 期待する挙動:
   - 3 ドットアニメーションが表示される
   - その**下**にストリーミング中のテキストが徐々に伸びていく（plain text、ゆっくりではなく tick ごとに追記）
   - テキストが 200 文字を超えると末尾 200 文字だけが表示される（末尾追尾）
   - 完了すると 3 ドット＋プレビューが消え、完成した AI メッセージが Markdown 付きで履歴に追加される
6. ブラウザ DevTools Network タブで `/api/job/{id}/stream` を確認し `data: {"status": "token", "token": "..."}` イベントが流れていること
7. 退行チェック: もう 1 通送信して同じ挙動 / 新スレッド作成 / スレッド切替が正常に動作すること
  </how-to-verify>
  <resume-signal>「approved」または問題点を報告してください</resume-signal>
</task>

</tasks>

<verification>
- バックエンド: `docker compose exec api python -c "from app.providers.copilot import ChatCopilot; import inspect; assert inspect.isasyncgenfunction(ChatCopilot._astream)"` が通ること
- バックエンド: `app/jobs/handlers/langgraph_handler.py` に `astream_events` と `send_token` が両方出現
- フロント: `bunx tsc --noEmit` で型エラーなし
- 手動: 3 ドット下にストリーミングプレビューが表示される（checkpoint で確認）
</verification>

<success_criteria>
- ユーザー質問に対し、AI 応答が完了する前にプレビューテキストが 3 ドット下に流れる
- 完成メッセージは従来通り 1 回だけ履歴に追加される（重複なし）
- 既存の Chat / Canvas / SuperChat / DebateChat の各フローが退行しない
- エラー時（SDK 失敗・切断）も従来通り job 完了フローでリカバリされる
</success_criteria>

<output>
完了後、`.planning/quick/260415-fhu-ai/260415-fhu-SUMMARY.md` を作成する
</output>
