# 0031. Copilot SDK トークンストリーミング実装 — 3 層配管の発見と修正

**Date:** 2026-04-15
**Status:** Accepted

## Context

Chat UI で AI 応答完了まで 3 ドットしか見えず、長文応答（Canvas HTML 生成等）でフィードバックが乏しかった。quick タスク `260415-fhu` でトークンストリーミングプレビューを実装した。

**前回セッションの誤診:**
最初の実装試行時、`_astream` を実装しても画面に何も出なかった。このとき「Copilot SDK 0.2.0 は Technical Preview 制限で `ASSISTANT_MESSAGE_DELTA` イベントを発火しない」と結論づけ、done 受信後に先頭 150 文字を 1500ms 擬似表示する fallback を実装してセッションを paused した。

**本セッションで再検証した結果、この診断は誤り** だった。実際には 3 層すべてが独立に壊れており、1 つ直しても次の層で止まるため「何も変わらない」ように見えていただけだった。

1. **SDK 層**: `create_session()` の `streaming: bool` パラメータを渡していなかった。デフォルト `None` では Copilot サーバーは delta イベントを送らない。
2. **LangGraph 層**: `chatbot_node` が `llm.ainvoke()` を使っていたため、仮に SDK が delta を送っても LangGraph の `astream_events(version="v2")` は `on_chat_model_stream` を発火しない（`astream()` 経由でないと tracing されない）。
3. **プロセス間通信層**: `WebNotifier.send_token()` が `JobStore.notify()` 経由で in-memory `asyncio.Queue` に put していたが、SSE エンドポイント（API プロセス）は別プロセスの worker の in-memory queue を読めない。SSE は Redis ポーリングで `done` や `push_turn` を検出しており、`notify()` は実質デッドコードだった。

## Decision

SDK の raw イベントを probe する診断スクリプト (`scripts/probe_sdk_events.py`) を書いて 2 回実行し、`streaming=False` / `streaming=True` の両方で実測してから 3 層すべてを修正した。

### 層 1 — SDK: `create_session(streaming=True)` を渡す

```python
# app/providers/copilot.py ChatCopilot._astream
session = await self._client.create_session(
    on_permission_request=PermissionHandler.approve_all,
    model=self.model,
    streaming=True,  # ← これがなかった
)
```

実測結果（probe スクリプト）:

| streaming | ASSISTANT_MESSAGE_DELTA | ASSISTANT_MESSAGE |
|-----------|-------------------------|-------------------|
| None（デフォルト） | 0 回 | 1 回（全文一発） |
| True | **109 回**（1〜4 文字/chunk） | 1 回（最終全文） |

`_agenerate`（非ストリーミング経路、他グラフで使用中）には `streaming=True` を足さない。余計な delta を無視するだけで無駄になるため。

### 層 2 — LangGraph: ノードを `llm.astream()` で呼ぶ

```python
# app/graph/builder.py chatbot_node / canvas_chatbot_node
response: AIMessage | None = None
async for chunk in llm.astream(system_messages + state["messages"]):
    response = chunk if response is None else response + chunk
if response is None:
    response = AIMessage(content="")
return {"messages": [response]}
```

`llm.astream()` は内部的に `_astream()` を呼ぶため、LangGraph の `astream_events(version="v2")` が `on_chat_model_stream` を発火する。ハンドラ側の `langgraph_handler.py` は既に `astream_events` + `on_chat_model_stream` → `notifier.send_token(token)` の配線があり、この層さえ通れば動く設計だった。

SubAgent (`agent.py::SubAgent.run`) も同パターンで `astream` 化し、SuperChat の tool なしエージェントと GemSubAgent（継承）を自動対応した。

### 層 3 — IPC: Redis list 経由で token を配信

```python
# app/jobs/job_store.py
async def push_token(self, job_id: str, token: str) -> None:
    await self.redis.rpush(f"job:{job_id}:tokens", token)
    await self.redis.expire(f"job:{job_id}:tokens", 3600)

async def get_tokens(self, job_id: str, since: int = 0) -> list[str]:
    raws = await self.redis.lrange(f"job:{job_id}:tokens", since, -1)
    return [r.decode() if isinstance(r, bytes) else r for r in raws]
```

`WebNotifier.send_token()` を `push_token()` 経由に切替。SSE ジェネレータ (`app/api/routes/chat.py::stream_job`) に token drain ループを追加し、polling 間隔を 500ms → 150ms に短縮した。

```python
# Still in progress — poll Redis
seen_tokens = 0
while True:
    tokens = await job_store.get_tokens(job_id, since=seen_tokens)
    for tok in tokens:
        yield f"data: {json.dumps({'status': 'token', 'token': tok})}\n\n"
        seen_tokens += 1
    # ... completion check + final flush ...
    await asyncio.sleep(0.15)
```

### 対応範囲

| アプリ | Backend | Frontend |
|--------|---------|----------|
| Chat | `chatbot_node` astream | `ChatApp` + `streamPreview` 配線 |
| Gem（通常） | 継承 | `GemChatApp` 配線 |
| Canvas / Canvas Gem | `canvas_chatbot_node` astream | `CanvasChatApp` 配線 |
| SuperChat（tool なし SubAgent） | `SubAgent.run` astream + `orchestrator_handler` astream_events | `SuperChatApp` 配線 |

意図的に未対応:

- **Router LLM** (`orchestrator/graph.py::Router`) — routing 決定（"code-reviewer" 等の agent 名 1 単語）が preview に漏れるため `ainvoke` のまま
- **ToolEnabledSubAgent** (`orchestrator/tool_agent.py`) — tool_calls レスポンスは chunk.content が空で tool_call 情報だけが付くため、send_token 条件と preview 表示の設計が必要
- **DebateChat** (`debate_graph.py` / `debate_handler.py`) — 複数話者の token 属性付けとフロント側 state の再設計が必要

### 表示層: 1 行目のみ表示

`MessageArea.tsx` の preview を `streamPreview.split('\n')[0]` に変更し、`white-space: nowrap; overflow: hidden; text-overflow: ellipsis` で改行を含む応答でも 1 行に抑制した。

## Alternatives Considered

**案 A: フロント側タイプライター演出（SDK 非依存）**
`done` 受信後に完成テキストを 1 文字ずつ表示するアニメーション。前回セッションの「SDK delta 未対応」前提で一度検討したが、probe スクリプトで SDK が `streaming=True` で delta を送ることが判明したため不要になった。

**案 B: 前回セッションの fallback を温存（done 後に 150 字 1500ms 表示）**
真のストリーミングが効いていなかった時代の fallback。本修正で不要になり撤去。

**案 C: Redis Pub/Sub で token 配信**
`push_turn` の history (`9aaa213` → `0b47865`) で一度 Pub/Sub を採用し、Redis list polling に戻している前例がある。同じ方針で list polling を採用した。

**案 D: WebSocket 化**
真のリアルタイムだが、既存の SSE エコシステム（polling 配管、`done` 検出、ツールイベント）をすべて書き換えることになるため却下。polling 150ms で十分な体感を得られた。

**案 E: 全アプリ一括対応（C 案）**
DebateChat まで対応する案。複数話者の token 属性付けとフロント state 再設計を伴い、スコープが quick タスクから逸脱するため B+（Chat/Gem/Canvas/SuperChat tool なしのみ）に絞った。

## Consequences

**ポジティブ:**

- Chat / Gem / Canvas / SuperChat（tool なし）で真のトークンストリーミングが動作し、1〜4 文字刻みの delta がリアルタイム表示される
- SDK 0.2.0 で「ストリーミングが使えない」と誤解していた制限を解消
- `_astream` のフォールバック分岐（`has_deltas` / `ASSISTANT_MESSAGE` 捕捉）は将来の SDK 退行に対するデフェンシブコードとして残存
- `scripts/probe_sdk_events.py` が SDK 挙動の実測手段として残り、今後の SDK アップグレード時に再利用可能
- `push_token` / `get_tokens` の配管は app_id 非依存なので、将来 Debate や ToolEnabledSubAgent を対応するときも backend インフラは再利用できる

**ネガティブ / 注意点:**

- **SSE polling 150ms** への短縮で Redis 負荷が約 3.3 倍に増加（1 ジョブあたり）。200 名規模の利用想定では問題ないが、高トラフィック時は要監視
- **Router / ToolEnabledSubAgent / Debate は未対応**。今後対応する場合、ToolEnabledSubAgent は `chunk.content` が空のときスキップする条件、Debate は token に発言者タグを付ける設計が必要
- **`JobStore.notify()` は実質デッドコード** だが互換のため残した。将来 `progress()` や `done()` も Redis 経路に一本化する余地あり
- **`logger` import の未使用問題**: `copilot.py` で debug 時に追加した `logger.warning` は撤去済みだが、`logger = logging.getLogger(__name__)` は残存（他メソッドで使用予定のため削除せず）

**教訓:**

前回セッションの「SDK が delta を送らない」という診断は **「画面に何も出なかった」→「SDK が悪いのだろう」** という推測ベースだった。実際には `_astream` すらそもそも呼ばれていなかった（`chatbot_node` が `ainvoke` を使っていたため）ので、SDK が delta を送っていたかすら確認できていなかった。

- **エラーが出ないバグで推測に頼ると層を見誤る**。probe スクリプトで raw イベント種を実測していれば、最初のセッションで `streaming=True` が渡されていないことに気づけた
- **ドキュメントを引く価値**。`create_session(streaming: bool)` のパラメータは公式ドキュメント (`docs.github.com/en/copilot/how-tos/copilot-sdk/use-copilot-sdk/streaming-events`) と `inspect.signature()` の両方で確認可能だった。最初に公式ドキュメントを引いていれば 5 分で解決していた
- **層を切り分ける診断スクリプトは投資対効果が高い**。`scripts/probe_sdk_events.py` は 60 行程度だが、本件の根本原因特定を一発で可能にした
