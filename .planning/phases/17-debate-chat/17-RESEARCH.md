# Phase 17: マルチエージェント討論チャット - Research

**Researched:** 2026-04-06
**Domain:** LangGraph マルチエージェントグラフ / ターン制会話 / FastAPI + React 統合
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**グラフトポロジー**
- D-01: `DebateGraph` は `app/orchestrator/debate_graph.py` に `build_debate_graph(participants, pattern, max_turns, llm, checkpointer=None)` ファクトリ関数として実装する。OrchestratorGraph から独立した完全に新しい `StateGraph`
- D-02: 3パターン（debate/panel/chain）は同一の `build_debate_graph` 関数で実装し、`pattern` パラメータによってエッジ構造を分岐させる。パターン別に独立グラフを作らない
- D-03: `DebateState` は独自 TypedDict として定義する（`AgentState` は継承しない）。必要フィールド: `turn: int`, `max_turns: int`, `pattern: str`, `participants: list[str]`, `messages: Annotated[list[BaseMessage], operator.add]`, `current_agent_idx: int`, `awaiting_extension: bool`
- D-04: 討論パターン（debate）: A→B→A→B→...のラウンドロビン後 → aggregator → END。チェーン（chain）: A→B→C→END。パネル（panel）: A・B・C を順次実行後 → aggregator → END（並列は arq の単一タスク前提で順次で代用）

**ターン制御と延長承認**
- D-05: ターン終了後の延長承認は **再エンキュー方式** で実装する。`interrupt_before` は採用しない（arq バックグラウンド worker との相性が悪いため）
- D-06: フロントエンドがターン終了を検知したら「延長しますか？」UI を表示し、ユーザーが承認すると追加 `max_turns` を付けて同一 `thread_id` で再度 `POST /api/chat` を送る
- D-07: DebateGraph は LangGraph checkpointer を使い、`thread_id` をキーに会話履歴を継続する（再エンキュー時に過去の発言が失われないようにする）

**ハンドラー設計**
- D-08: `task_type="debate"` を新規登録。`app/jobs/handlers/debate_handler.py` として `DebateHandler` を実装し、`worker.py` の `TASK_HANDLERS` dict に1行追加
- D-09: `ChatRequest` に `participants: list[str] | None = None`, `pattern: str = "debate"`, `max_turns: int = 3` を追加。`agents` フィールドとは独立（意味が異なる）
- D-10: `process_chat` 関数のシグネチャに同フィールドを追加し、`job` dict に含めて `DebateHandler` に渡す

**フロントエンド**
- D-11: `frontend/src/components/DebateChatApp.tsx` を新規作成。`SuperChatApp.tsx` を参考パターンとして `useThreads`, `useChat`, `MessageArea`, `ThreadSidebar` を流用
- D-12: `App.tsx` の `Screen` 型に `'debate'` を追加し、`MenuScreen` からナビゲートできるようにする
- D-13: 各エージェントの発言は `[エージェント名]: 発言内容` プレフィックス形式で既存 `MessageArea` に積み上げる（MVP）。`ChatMessage` 型の変更なし
- D-14: DebateChatApp の設定 UI: パターン選択（debate/panel/chain）ラジオ + 参加エージェント/Gem チェックリスト + ターン数入力。チャット開始前に1回だけ設定する

### Claude's Discretion

- aggregator ノードの実装（専用 LLM コールで統合するか、最後のエージェントが自然に締めるか）
- DebateChatApp の設定 UI の具体的なスタイリング
- ターン終了の検知方法（DebateHandler が job result に `status: "turn_complete"` を含めるか、通常の `done` と同じにするか）

### Deferred Ideas (OUT OF SCOPE)

- エージェント別カラーバブル表示 — MVP はプレフィックス方式、次フェーズで強化
- 討論サマリーの自動生成（「この討論の結論は...」） — 将来フェーズ
- 討論結果の保存・共有機能 — 将来フェーズ
- パネル型の真の並列実行（asyncio.gather） — 現状は arq 単一タスクで順次代用
- LangGraph interrupt_before による中断・再開パターン — arq との統合研究が必要
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DEBATE-01 | ターン制マルチエージェントグラフ — 参加エージェントリスト × ターン数で構成される LangGraph グラフ。各ノードが前のメッセージ全体を見て発言する | build_debate_graph ファクトリパターン検証済み。DebateState TypedDict + operator.add で全メッセージ蓄積確認 |
| DEBATE-02 | 会話パターン選択 — 討論（A→B→A→B→...→統合）、パネル（並列→統合）、チェーン（A→B→C）の3パターン | 各パターンの LangGraph エッジ構造を実機検証済み |
| DEBATE-03 | ターン数制御 — 指定ターン数で自動終了。終了後に人間が延長承認できる | 再エンキュー方式の state 継続を MemorySaver で動作確認済み |
| DEBATE-04 | DebateChatApp フロントエンド — パターン選択 + 参加エージェント選択 + チャット UI。各エージェントの発言が順に表示される | SuperChatApp.tsx の流用パターン + useChat/useThreads フック確認済み |
| DEBATE-05 | 新 task_type "debate" + DebateHandler — arq worker に登録する新ハンドラー | TaskHandler 基底クラス + TASK_HANDLERS 登録パターン確認済み |
</phase_requirements>

---

## Summary

Phase 17 は既存の OrchestratorGraph + arq worker アーキテクチャの上に「討論チャット」を追加するフェーズ。コアとなる `DebateGraph` は `build_debate_graph()` ファクトリ関数として実装し、3 つの会話パターン（debate/panel/chain）を `pattern` パラメータで切り替えるシングルグラフ設計。

LangGraph の StateGraph と `operator.add` reducer を使ったメッセージ蓄積は **実機検証済み**。`DebateState` の TypedDict 定義・ファクトリ関数のコンパイル・再エンキュー方式での会話継続（同一 `thread_id` への複数回 `ainvoke`）がすべて正常に動作することを確認した。重要な実装判断として、participants はグラフビルド時（`DebateHandler.handle()` 内）に確定するため、ノードを動的に作成することが可能。

フロントエンド側は `SuperChatApp.tsx` のパターンをほぼそのまま流用できる。主な差分は「設定パネル（パターン選択 + 参加者チェックリスト + ターン数入力）をチャット開始前に表示する」点と、「ターン終了後の延長確認 UI」の追加。

**Primary recommendation:** `build_debate_graph` の単一ディスパッチャーノード方式（debate パターン）と per-agent ノード方式（chain パターン）を1つのファクトリ関数で実装し、DebateHandler → OrchestratorHandler と同じ DB/checkpointer パターンで接続する。

---

## Standard Stack

### Core（既存スタック — 追加インストール不要）
| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `langgraph` | 1.1.6 (installed) | StateGraph + checkpointer | DebateGraph の実装基盤。条件付きエッジ・MemorySaver/AsyncPostgresSaver が使用可能 |
| `langgraph-checkpoint-postgres` | >=3.0.5 | 会話永続化 | AsyncPostgresSaver で thread_id をキーに討論履歴を継続 |
| `langchain-core` | >=0.3.0 | BaseMessage / BaseChatModel | HumanMessage, AIMessage, SystemMessage。DebateState.messages の型 |
| `fastapi` | 0.135.2 | HTTP API | ChatRequest モデル拡張、既存ルートに participants/pattern/max_turns 追加 |
| `arq` | — | バックグラウンドタスク | DebateHandler を TASK_HANDLERS に登録するだけ |

[VERIFIED: pyproject.toml + pip show langgraph]

**追加インストール不要。** Phase 17 は既存スタック内で完結する。

---

## Architecture Patterns

### Recommended Project Structure（新規追加ファイル）

```
app/
  orchestrator/
    debate_graph.py       # 新規: build_debate_graph() ファクトリ関数 + DebateState
  jobs/
    handlers/
      debate_handler.py   # 新規: DebateHandler(TaskHandler)

frontend/src/
  components/
    DebateChatApp.tsx     # 新規: 討論チャットアプリ UI
  hooks/
    useDebateConfig.ts    # 新規（任意）: パターン選択・参加者・ターン数の状態管理
```

変更ファイル:
```
app/api/models.py         # ChatRequest に participants/pattern/max_turns 追加
app/jobs/worker.py        # TASK_HANDLERS + process_chat シグネチャ
app/api/routes/chat.py    # enqueue_job に新フィールドを追加
frontend/src/App.tsx      # Screen 型に 'debate' 追加 + handleNavigate 拡張
frontend/src/types.ts     # ChatRequest インターフェースに新フィールド追加
frontend/src/api/client.ts # 必要に応じて postChat 引数拡張
frontend/src/components/MenuScreen.tsx  # 討論チャットカード追加
```

---

### Pattern 1: DebateState TypedDict

[VERIFIED: python3 実機確認]

```python
# app/orchestrator/debate_graph.py
import operator
from typing import Annotated
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage

class DebateState(TypedDict):
    turn: int
    max_turns: int
    pattern: str
    participants: list[str]
    messages: Annotated[list[BaseMessage], operator.add]
    current_agent_idx: int
    awaiting_extension: bool
```

**注意:** `AgentState` は継承しない（D-03）。`messages` は `operator.add` reducer — 各エージェント発言が追記される。全フィールド必須（`AgentState` の precedent: `NotRequired` は使わない）。

---

### Pattern 2: build_debate_graph — debate パターン（ラウンドロビン）

[VERIFIED: python3 実機確認]

```python
def build_debate_graph(
    participants: list[str],    # エージェント名リスト（グラフビルド時に確定）
    pattern: str,               # "debate" | "panel" | "chain"
    max_turns: int,
    agents: dict[str, Any],     # name -> GemSubAgent or SubAgent インスタンス
    llm: BaseChatModel,         # aggregator 用 LLM
    checkpointer=None,
) -> Any:
    graph = StateGraph(DebateState)

    if pattern in ("debate", "panel"):
        # 単一ディスパッチャーノード方式（round-robin）
        # participants は state.participants から取得 → ノード内で解決
        def make_dispatch_node(agents_map):
            async def debate_turn(state: DebateState) -> dict:
                idx = state["current_agent_idx"] % len(state["participants"])
                agent_name = state["participants"][idx]
                agent = agents_map[agent_name]
                # Adapt state for agent.run(): AgentState 互換 dict を作る
                pseudo_state = {"input": _last_human_message(state), "messages": state["messages"]}
                response = await agent.run(pseudo_state)
                prefix = f"**[{agent_name}]**: "
                return {
                    "turn": state["turn"] + 1,
                    "current_agent_idx": state["current_agent_idx"] + 1,
                    "messages": [AIMessage(content=prefix + response["output"])],
                }
            return debate_turn

        graph.add_node("debate_turn", make_dispatch_node(agents))
        graph.add_node("aggregator", make_aggregator_node(llm))
        graph.set_entry_point("debate_turn")

        def route_debate(state: DebateState) -> str:
            return "aggregator" if state["turn"] >= state["max_turns"] else "debate_turn"

        graph.add_conditional_edges(
            "debate_turn", route_debate,
            {"debate_turn": "debate_turn", "aggregator": "aggregator"}
        )
        graph.add_edge("aggregator", END)

    elif pattern == "chain":
        # per-agent ノード方式（A→B→C→aggregator）
        for name in participants:
            graph.add_node(name, make_agent_node(name, agents[name]))
        graph.add_node("aggregator", make_aggregator_node(llm))
        graph.set_entry_point(participants[0])
        for i in range(len(participants) - 1):
            graph.add_edge(participants[i], participants[i + 1])
        graph.add_edge(participants[-1], "aggregator")
        graph.add_edge("aggregator", END)

    return graph.compile(checkpointer=checkpointer)
```

**重要な実装の注意点:**

1. `agent.run()` は `AgentState` 形式の dict を期待する（`input`, `messages` フィールド）。`DebateState` と直接互換ではないため、pseudo_state を作って渡す
2. debate/panel の差分: panel は `pattern` フィールドを保持するだけで、グラフ構造は同じ（順次実行）。将来の並列化に備えてパターン名を分けている
3. participants はグラフビルド時に確定 → 動的ノード生成 OK（`chain` パターンで確認済み）

---

### Pattern 3: DebateHandler

[VERIFIED: OrchestratorHandler の構造を参照]

```python
# app/jobs/handlers/debate_handler.py
class DebateHandler(TaskHandler):
    async def handle(self, ctx: dict, job: dict) -> dict:
        job_id = job["job_id"]
        thread_id = job["thread_id"]
        prompt = job["prompt"]
        github_token = job["github_token"]
        reply_to = job["reply_to"]
        participants: list[str] = job.get("participants") or []
        pattern: str = job.get("pattern", "debate")
        max_turns: int = job.get("max_turns", 3)
        github_login: str = job.get("github_login", "unknown")
        gem_ids: list[str] = job.get("gem_ids") or []

        job_store = ctx["job_store"]
        notifier = build_notifier(reply_to, job_store)

        try:
            await notifier.progress("thinking")

            # 1. エージェントインスタンスを構築（SubAgent + GemSubAgent）
            registry = SubAgentRegistry(AGENT_DIR, github_token)
            agents = _build_debate_agents(registry, gem_ids, participants, github_token, github_login)
            llm = ChatCopilot(model="claude-haiku-4-5-20251001", github_token=github_token)

            # 2. グラフをビルド・実行
            async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
                await checkpointer.setup()
                graph = build_debate_graph(participants, pattern, max_turns, agents, llm, checkpointer)
                config = {"configurable": {"thread_id": thread_id}}
                initial: DebateState = {
                    "turn": 0,
                    "max_turns": max_turns,
                    "pattern": pattern,
                    "participants": participants,
                    "messages": [HumanMessage(content=prompt)],
                    "current_agent_idx": 0,
                    "awaiting_extension": False,
                }
                result = await graph.ainvoke(initial, config=config)

            # 3. 結果をフォーマット
            final_text = _format_debate_result(result["messages"])
            await job_store.save_result(job_id, final_text)
            await notifier.done()

        except Exception as e:
            logger.exception("DebateHandler failed for job %s", job_id)
            await job_store.save_result(job_id, f"Error: {e}")
            await notifier.done()
        finally:
            await registry.close()

        return {"job_id": job_id, "status": "done"}
```

---

### Pattern 4: 再エンキュー方式（延長承認）

[VERIFIED: python3 実機確認 — MemorySaver で同一 thread_id への複数回 ainvoke]

```
ターン1回目（max_turns=3）:
  POST /api/chat { task_type:"debate", participants:["A","B"], max_turns:3, pattern:"debate", ... }
  → DebateHandler が graph.ainvoke() を実行 → 3ターン完了 → save_result() → notifier.done()

フロントエンド:
  job result の最後のメッセージが aggregator の統合発言
  → DebateChatApp が「延長しますか？あと何ターン？」UI を表示
  → ユーザーが N を入力して承認

ターン延長（max_turns=3+N）:
  POST /api/chat { ..., max_turns:6, thread_id: 同一 }
  → DebateHandler: initial state に turn=3, max_turns=6, messages=[] を渡す
  → checkpointer が thread_id から既存 state を復元
  → 続きから実行（turn=3→6）
```

**state 渡し方の注意（実機確認済み）:**

```python
# 延長時の initial state（DebateHandler 内）
# job から previous_turn を読み取る必要がある
# → job dict に "current_turn" フィールドを追加する（D-09 の拡張）
initial: DebateState = {
    "turn": job.get("current_turn", 0),          # 前回の終了ターン数
    "max_turns": max_turns,                        # 新しい上限（current_turn + extension）
    "pattern": pattern,
    "participants": participants,
    "messages": [],                                # 空: checkpointer が蓄積分を保持
    "current_agent_idx": job.get("current_turn", 0),  # ラウンドロビン継続
    "awaiting_extension": False,
}
```

---

### Pattern 5: ChatRequest 拡張

[VERIFIED: 既存 app/api/models.py を参照]

```python
# app/api/models.py — 追加フィールド
class ChatRequest(BaseModel):
    # ... 既存フィールド ...
    participants: list[str] | None = None  # 討論参加者エージェント名リスト
    pattern: str = "debate"                # "debate" | "panel" | "chain"
    max_turns: int = 3                     # 討論ターン数
    current_turn: int = 0                  # 再エンキュー時に前回の終了ターンを渡す
```

```python
# app/jobs/worker.py — process_chat シグネチャ追加
async def process_chat(
    ctx: dict,
    *,
    # ... 既存引数 ...
    participants: list[str] | None = None,
    pattern: str = "debate",
    max_turns: int = 3,
    current_turn: int = 0,
) -> dict:
    job = {
        # ... 既存フィールド ...
        "participants": participants,
        "pattern": pattern,
        "max_turns": max_turns,
        "current_turn": current_turn,
    }
```

---

### Pattern 6: DebateChatApp フロントエンド

[VERIFIED: SuperChatApp.tsx, App.tsx, useChat.ts を参照]

```tsx
// frontend/src/App.tsx — 変更箇所
type Screen = 'menu' | 'superchat' | 'gems' | 'gemchat' | 'debate';  // 'debate' 追加

// handleNavigate を拡張: app.slug === 'debate' の場合に 'debate' 画面へ
// OR: MenuScreen に onOpenDebate コールバックを追加（Gems カードと同パターン）
```

```tsx
// DebateChatApp.tsx の構造（SuperChatApp.tsx を参考）
interface DebateChatAppProps {
  selectedModel: string;
}

interface DebateConfig {
  pattern: 'debate' | 'panel' | 'chain';
  participants: string[];  // 選択済みエージェント名 + Gem 名
  maxTurns: number;
}

export function DebateChatApp({ selectedModel }: DebateChatAppProps) {
  const [config, setConfig] = useState<DebateConfig | null>(null);  // null = 設定画面表示中
  const [currentTurn, setCurrentTurn] = useState(0);
  const [awaitingExtension, setAwaitingExtension] = useState(false);

  // config == null のとき: 設定パネルを表示
  // config != null のとき: チャット UI を表示
}
```

**設定パネルの UI 要素:**
1. パターン選択: radio ボタン（debate / panel / chain）
2. 参加者選択: エージェントチェックリスト（useAgents から取得）+ Gem チェックリスト（useGemSelector から取得）
3. ターン数入力: number input（デフォルト 3、最小 1）
4. 「討論開始」ボタン → `config` を確定 → チャット UI に切り替え

**ターン終了検知（Claude's Discretion 解決案）:**

`DebateHandler` の job result に JSON を含める方式を採用する:

```json
{
  "type": "debate_result",
  "debate_text": "[A]: ...\n[B]: ...",
  "final_turn": 3,
  "max_turns": 3,
  "is_complete": true
}
```

- `is_complete: true` → フロントが「延長しますか？」UI を表示
- `is_complete: false` → 通常の AI メッセージとして表示
- 既存の `parseJobResult()` 関数（Canvas と同パターン）で検出

ただし MVP では単純化: **plain text のみ**で実装し、延長 UI は「送信フォームにターン数を追加」で代用する方が実装コストが低い。

---

### Pattern 7: aggregator ノードの実装（Claude's Discretion 解決案）

aggregator は **専用 LLM コール方式**を推奨:

```python
def make_aggregator_node(llm: BaseChatModel):
    async def aggregator(state: DebateState) -> dict:
        debate_log = "\n".join(
            msg.content for msg in state["messages"]
            if isinstance(msg, AIMessage)
        )
        prompt = f"""以下は複数のエージェントによる討論です。要点を簡潔にまとめてください。

{debate_log}"""
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        return {
            "messages": [AIMessage(content=f"**[まとめ]**: {response.content}")]
        }
    return aggregator
```

最後のエージェントが「自然に締める」方式は、エージェントのシステムプロンプトを変更しなければならないため避ける。

---

### Anti-Patterns to Avoid

- **`interrupt_before` の使用:** arq の非同期 worker と組み合わせると、グラフが中断されたまま worker が終了してしまう。D-05 で明確に禁止。再エンキュー方式を使う
- **`participants` をグラフビルド後に変更:** LangGraph のノード構成はコンパイル時に固定。chain パターンで per-agent ノードを作る場合は毎回 build_debate_graph を呼ぶ
- **`messages` を全量渡してしまう再エンキュー:** 再エンキュー時に `messages` に全履歴を渡すと、checkpointer の蓄積分と二重になる。再エンキュー時は `messages: []` を渡す
- **TypeScript の `ChatRequest` 型を更新せずに POST する:** `participants`, `pattern`, `max_turns` を追加しないと TypeScript が型エラーを出す
- **`AgentState.input` に依存した agent.run() をそのまま使う:** `GemSubAgent.run()` と `SubAgent.run()` はどちらも `state["input"]` を参照する。DebateState には `input` フィールドがないため、pseudo_state を作って渡す必要がある（**最重要ピットフォール**）

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 会話履歴の永続化 | カスタム DB 保存 | AsyncPostgresSaver（既存） | スレッド継続・再エンキュー方式の基盤。既に動作中 |
| エージェントインスタンス管理 | カスタムファクトリ | SubAgentRegistry + GemSubAgent（既存） | agents ディレクトリ・DB からの Gem ロードが既に実装済み |
| SSE 完了通知 | カスタム pub/sub | build_notifier（既存） | DebateHandler も同じパターンで使用可能 |
| 条件付きルーティング | 手動 if/else | LangGraph conditional edges | ターン数カウント・パターン分岐がグラフで宣言的に書ける |

---

## Common Pitfalls

### Pitfall 1: agent.run() が DebateState を受け付けない

**What goes wrong:** `SubAgent.run()` と `GemSubAgent.run()` は `AgentState` 型の dict を期待し、`state["input"]` を参照する。`DebateState` には `input` フィールドがないため `KeyError` が発生する。

**Why it happens:** `DebateState` は独自 TypedDict で、`AgentState` の `input` フィールドを持たない（D-03）。

**How to avoid:** DebateGraph 内のノード実装で pseudo_state を作る:
```python
pseudo_state = {
    "input": _extract_last_human_message(state),
    "messages": state["messages"],
    "output": "",
    "next": "",
    "error": None,
    "context": None,
}
```

または、`GemSubAgent.run()` / `SubAgent.run()` をラップする debate-specific 呼び出しヘルパーを作る。

---

### Pitfall 2: 再エンキュー時の messages 二重蓄積

**What goes wrong:** 再エンキュー時に `messages` に前回の全発言を渡すと、checkpointer に保存済みの messages と `operator.add` で結合され、全メッセージが2倍になる。

**Why it happens:** LangGraph checkpointer は `ainvoke` で渡された state と、保存済み state を reducer でマージする。`operator.add` は concat。

**How to avoid:** 再エンキュー時は常に `messages: []` を渡す（実機検証済み）。

---

### Pitfall 3: chain パターンで participants が空の場合

**What goes wrong:** `participants = []` の場合、`graph.set_entry_point(participants[0])` が `IndexError`。

**How to avoid:** DebateHandler の先頭でバリデーション:
```python
if len(participants) < 2:
    raise ValueError(f"debate requires at least 2 participants, got {participants}")
```

---

### Pitfall 4: frontend の task_type 送信漏れ

**What goes wrong:** `DebateChatApp` が `POST /api/chat` を送る際に `task_type: "debate"` を含めないと、`worker.py` がデフォルトの `"langgraph"` ハンドラーを使い、討論が実行されない。

**How to avoid:** `useChat` の呼び出し時に `selectedTaskType="debate"` を明示的に渡す。

---

### Pitfall 5: participants と agents/gem_ids の取り違え

**What goes wrong:** `ChatRequest.agents` はスーパーチャット用のフィルター、`ChatRequest.participants` は討論参加者リスト。混在させると誤ったエージェントが呼ばれる。

**How to avoid:** `DebateHandler.handle()` では `job.get("participants")` を使い、`job.get("agents")` は参照しない。コードに明示的なコメントを書く。

---

## Code Examples

### agent.run() の pseudo_state ラッパー（最重要）

```python
# debate_graph.py 内のヘルパー
from langchain_core.messages import HumanMessage

def _extract_last_human_message(state: DebateState) -> str:
    """DebateState の messages から最後の HumanMessage のテキストを取得する。"""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            return msg.content
    return ""

def _make_pseudo_agent_state(state: DebateState) -> dict:
    """agent.run() に渡す AgentState 互換 dict を DebateState から作成する。"""
    return {
        "input": _extract_last_human_message(state),
        "messages": state["messages"],
        "output": "",
        "next": "",
        "error": None,
        "context": None,
    }
```

### 結果フォーマット関数

```python
def _format_debate_result(messages: list[BaseMessage]) -> str:
    """討論の全 AI メッセージを結合してフロントに返す文字列を生成する。"""
    lines = []
    for msg in messages:
        if isinstance(msg, AIMessage) and msg.content:
            lines.append(msg.content)
    return "\n\n".join(lines)
```

### worker.py 登録（1行追加）

```python
# app/jobs/worker.py
from app.jobs.handlers.debate_handler import DebateHandler

TASK_HANDLERS: dict[str, TaskHandler] = {
    "langgraph": LangGraphHandler(),
    "orchestrator": OrchestratorHandler(),
    "debate": DebateHandler(),              # 追加
}
```

### App.tsx — debate 画面追加パターン

```tsx
// App.tsx
type Screen = 'menu' | 'superchat' | 'gems' | 'gemchat' | 'debate';

// MenuScreen に onOpenDebate コールバックを追加
const handleOpenDebate = () => { setCurrentScreen('debate'); };

// JSX内
{currentScreen === 'debate' && (
  <>
    <Header ... onBackToMenu={() => setCurrentScreen('menu')} appName="討論チャット" />
    <DebateChatApp selectedModel={selectedModel} />
  </>
)}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `interrupt_before` + human-in-the-loop | 再エンキュー方式（D-05） | Phase 17 設計時 | arq worker との互換性。`interrupt_before` は arq では worker 終了後にグラフ状態が消えるリスクがある |
| single-agent chat | multi-agent debate graph | Phase 17 (新機能) | OrchestratorGraph とは独立した新グラフ。ルーターなし、ターン制 |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | aggregator ノードの実装は専用 LLM コール方式を推奨（Claude's Discretion） | Pattern 7 | 開発者が別方式を選んでも動く。スタイルの問題のみ |
| A2 | `DebateHandler` の output は plain text（JSON ではなく単純連結文字列） | Pattern 6 | 延長検知の精度が下がるが MVP として許容可能 |
| A3 | `ChatRequest.current_turn` フィールドを追加して再エンキュー時のターン継続に使う | Pattern 5 | フロントが current_turn を管理していない場合、延長が ターン 0 から再スタートする |

---

## Open Questions

1. **延長承認 UI の詳細設計**
   - What we know: D-06 でフロントが「延長しますか？」を表示し、承認で再 POST
   - What's unclear: job result から「討論完了」を検知する方法。plain text のみでは判定不可
   - Recommendation: job result を `{"type":"debate_done","text":"...","final_turn":3}` JSON にする方式を採用し、`parseJobResult()` と同パターンで検出する。plain text フォールバックも維持

2. **参加者と Gem の混在時の agent インスタンス構築**
   - What we know: `OrchestratorHandler` が `registry.agents` に `GemSubAgent` をマージする実装がある（再利用可能）
   - What's unclear: `participants` リストに Gem の名前が含まれる場合、`gem_ids` とのマッピングが必要。Gem 名（表示名）と gem_id（UUID）の対応をどのフィールドで渡すか
   - Recommendation: フロントから `participants: [{name: "GemA", gem_id: "uuid-xxx"}]` 形式で渡し、`ChatRequest` で `participants_with_ids` として定義するか、または `gem_ids` を維持して名前はDB から取得する（OrchestratorHandler と同じ DB クエリパターン）

---

## Environment Availability

Step 2.6: SKIPPED — Phase 17 は既存スタック内のコード追加のみ。新しい外部依存なし。

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (`asyncio_mode = "auto"`) |
| Quick run command | `python -m pytest tests/test_debate_graph.py -x -q` |
| Full suite command | `python -m pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEBATE-01 | DebateState TypedDict が機能する | unit | `pytest tests/test_debate_graph.py::test_debate_state -x` | ❌ Wave 0 |
| DEBATE-01 | debate パターンで N ターン後に aggregator が実行される | unit | `pytest tests/test_debate_graph.py::test_debate_pattern_runs_n_turns -x` | ❌ Wave 0 |
| DEBATE-02 | chain パターンで A→B→C の順に実行される | unit | `pytest tests/test_debate_graph.py::test_chain_pattern_order -x` | ❌ Wave 0 |
| DEBATE-02 | panel パターンが debate と同じ順次実行になる | unit | `pytest tests/test_debate_graph.py::test_panel_pattern -x` | ❌ Wave 0 |
| DEBATE-03 | 同一 thread_id で再エンキューしてターン継続できる | unit | `pytest tests/test_debate_graph.py::test_reenqueue_extension -x` | ❌ Wave 0 |
| DEBATE-05 | DebateHandler が TASK_HANDLERS に登録されている | unit | `pytest tests/test_worker.py::test_debate_handler_registered -x` | ❌ Wave 0 |
| DEBATE-05 | process_chat が participants/pattern/max_turns を受け取れる | unit | `pytest tests/test_worker.py::test_process_chat_debate_args -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_debate_graph.py tests/test_worker.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_debate_graph.py` — build_debate_graph テスト（DEBATE-01, DEBATE-02, DEBATE-03）
- [ ] `tests/test_debate_handler.py` — DebateHandler.handle() の mock テスト（DEBATE-05）
- [ ] 既存 `tests/test_worker.py` への追加: `test_debate_handler_registered`, `test_process_chat_debate_args`

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | 既存 JWT cookie 認証を流用（変更なし） |
| V4 Access Control | yes | `participants` フィールドの Gem 所有者検証が必要（OrchestratorHandler と同パターン） |
| V5 Input Validation | yes | `pattern` フィールドは "debate"/"panel"/"chain" のみ許可。`max_turns` は上限設定（例: 20） |
| V6 Cryptography | no | — |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| 他ユーザーの Gem を participants に指定 | Elevation of privilege | DB クエリで `is_public = true OR github_login = %s` のフィルター（OrchestratorHandler と同パターン） |
| max_turns に巨大な値（例: 10000）を指定 | DoS | バックエンドで上限検証: `max_turns = min(max_turns, 20)` |
| participants に存在しないエージェント名を指定 | Tampering | DebateHandler でエージェント解決時に `KeyError` を適切に捕捉して 400 相当のエラーを返す |

---

## Sources

### Primary (HIGH confidence)
- `app/orchestrator/graph.py` — build_orchestrator_graph パターン（DebateGraph の設計参考）
- `app/orchestrator/state.py` — AgentState TypedDict（DebateState の設計参考）
- `app/orchestrator/gem_agent.py` — GemSubAgent.run() インターフェース
- `app/jobs/handlers/orchestrator_handler.py` — DebateHandler の参照実装
- `app/jobs/worker.py` — TASK_HANDLERS 登録パターン
- `frontend/src/components/SuperChatApp.tsx` — DebateChatApp の UI 参考
- `frontend/src/App.tsx` — Screen 型・navigate パターン

### Secondary (MEDIUM confidence)
- LangGraph 1.1.6 実機検証（python3 スクリプトによる StateGraph コンパイル・ainvoke 確認）

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — 既存スタックの確認のみ、追加インストールなし
- Architecture: HIGH — build_debate_graph ファクトリ・再エンキュー方式を実機確認済み
- Pitfalls: HIGH — agent.run() の pseudo_state 問題は実コードから直接導出

**Research date:** 2026-04-06
**Valid until:** 2026-05-06（LangGraph 安定版、30日間有効）
