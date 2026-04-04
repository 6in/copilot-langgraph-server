# AGENT.md ベース サブエージェントアーキテクチャ 追補設計

> 元ドキュメント（全16章）の追補。章番号は17〜20で続番。
> 章12の補完案も末尾に記載。

---

## 17. RPCContext と LangGraph State の統合

### 17-1. 設計方針

`MenuDispatcher` から `graph.invoke()` に `context` を渡しているが、
LangGraph のノード間でどう引き回すかが元ドキュメントに未記載。

**原則：context は State の一部として全ノードで参照可能にする。ただし不変。**

### 17-2. AgentState 定義

```python
from __future__ import annotations
from typing import Annotated
import operator
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage


def _keep_first(a: RPCContext, b: RPCContext) -> RPCContext:
    """context は最初にセットされた値を維持（ノードが上書き不可）"""
    return a


class AgentState(TypedDict):
    # --- 入出力 ---
    input: str
    output: str

    # --- メッセージ履歴（追記専用） ---
    messages: Annotated[list[BaseMessage], operator.add]

    # --- ルーティング ---
    next: str                    # ルーターが書き込む次のノード名

    # --- コンテキスト（不変） ---
    context: Annotated[RPCContext, _keep_first]

    # --- エラー情報 ---
    error: str | None
```

### 17-3. State の初期化（MenuDispatcher）

```python
class MenuDispatcher:
    def dispatch(self, request: UserRequest) -> str:
        graph_name = self.menu_registry.get_graph(request.mode)
        graph = self.graphs[graph_name]

        initial_state: AgentState = {
            "input": request.input,
            "output": "",
            "messages": [],
            "next": "",
            "context": request.context,   # ここでセット → 以降は不変
            "error": None,
        }
        result = graph.invoke(initial_state)
        return result["output"]
```

### 17-4. SubAgent ノードでの context 取得

```python
class SubAgent:
    def run(self, state: AgentState) -> AgentState:
        context = state["context"]    # どのノードからも同じ方法でアクセス

        # ツール呼び出し時にそのまま渡す
        result = self._tools["lint"]["handler"](
            input={"code": state["input"]},
            context=context,
        )
        return {"output": result, "messages": [AIMessage(content=result)]}
```

### 17-5. context が流れる全体像

```
UserRequest(input, mode, context)
  └─ MenuDispatcher.dispatch()
       └─ graph.invoke(initial_state)
            ├─ RouterNode        state["context"] 参照（認可チェック等）
            ├─ SubAgent A.run()  state["context"] → RestBackend → X-Headerに展開
            ├─ SubAgent B.run()  state["context"] → RestBackend → X-Headerに展開
            └─ OutputNode        state["context"].thread_id でログ集約
```

### 17-6. RPCContext のデータクラス定義（再掲・完全版）

```python
from dataclasses import dataclass, field
import uuid


@dataclass(frozen=True)   # frozen=True で不変性を型レベルで保証
class RPCContext:
    user_id: str
    user_roles: list[str] = field(default_factory=list)
    thread_id: str = ""
    message_id: str = ""
    session_id: str = ""
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @classmethod
    def from_slack(cls, event: dict) -> "RPCContext":
        return cls(
            user_id=event["user"],
            thread_id=event.get("thread_ts", event["ts"]),
            message_id=event["ts"],
            session_id=event["channel"],
        )

    @classmethod
    def from_http(cls, headers: dict) -> "RPCContext":
        return cls(
            user_id=headers.get("X-User-Id", ""),
            user_roles=headers.get("X-User-Roles", "").split(","),
            thread_id=headers.get("X-Thread-Id", ""),
            message_id=headers.get("X-Message-Id", ""),
            session_id=headers.get("X-Session-Id", ""),
            correlation_id=headers.get("X-Correlation-Id", str(uuid.uuid4())),
        )
```

---

## 18. SubAgentRegistry エラーハンドリング詳細設計

### 18-1. 問題点の整理

元実装の問題：

```python
# NG: on_ready() が1つ失敗すると後続エージェントの初期化が止まる
for path in Path(agent_dir).glob("**/AGENT.md"):
    agent = SubAgent.from_dir(path.parent)
    agent.init()
    agent.ready()   # ← ここで httpx が例外を投げると全滅
    self.agents[agent.name] = agent
```

### 18-2. 改善版 SubAgentRegistry

```python
import asyncio
from enum import Enum


class AgentStatus(Enum):
    HEALTHY  = "healthy"
    DEGRADED = "degraded"   # on_ready 失敗：動くが外部依存が未確認
    FAILED   = "failed"     # from_dir / on_init 失敗：使用不可


@dataclass
class AgentEntry:
    agent: SubAgent | None
    status: AgentStatus
    error: str = ""


class SubAgentRegistry:
    def __init__(self, agent_dir: str):
        self._entries: dict[str, AgentEntry] = {}
        self._load_all(Path(agent_dir))

    def _load_all(self, base: Path) -> None:
        for path in base.glob("**/AGENT.md"):
            name = path.parent.name
            try:
                agent = SubAgent.from_dir(path.parent)
                agent.init()
            except Exception as e:
                logger.error(f"[{name}] init failed: {e}")
                self._entries[name] = AgentEntry(None, AgentStatus.FAILED, str(e))
                continue

            try:
                agent.ready()
                self._entries[agent.name] = AgentEntry(agent, AgentStatus.HEALTHY)
                logger.info(f"[{agent.name}] ready")
            except Exception as e:
                logger.warning(f"[{agent.name}] ready failed (degraded): {e}")
                self._entries[agent.name] = AgentEntry(agent, AgentStatus.DEGRADED, str(e))

    # --- 取得 ---

    def get(self, name: str) -> SubAgent:
        entry = self._entries.get(name)
        if entry is None:
            raise KeyError(f"Agent '{name}' not found")
        if entry.status == AgentStatus.FAILED:
            raise RuntimeError(f"Agent '{name}' failed to initialize: {entry.error}")
        if entry.status == AgentStatus.DEGRADED:
            logger.warning(f"[{name}] is degraded: {entry.error}")
        return entry.agent

    def all_healthy(self) -> list[SubAgent]:
        return [e.agent for e in self._entries.values() if e.status == AgentStatus.HEALTHY]

    def all_usable(self) -> list[SubAgent]:
        """HEALTHY + DEGRADED（ルーティング候補）"""
        return [e.agent for e in self._entries.values()
                if e.status in (AgentStatus.HEALTHY, AgentStatus.DEGRADED)]

    # --- ヘルス情報 ---

    def health_report(self) -> dict:
        return {
            name: {"status": e.status.value, "error": e.error}
            for name, e in self._entries.items()
        }

    # --- シャットダウン ---

    def shutdown_all(self) -> None:
        for name, entry in self._entries.items():
            if entry.agent is None:
                continue
            try:
                entry.agent.shutdown()
            except Exception as e:
                logger.error(f"[{name}] shutdown error: {e}")
```

### 18-3. ヘルスチェックエンドポイント（FastAPI 例）

```python
@app.get("/health/agents")
def agent_health():
    report = registry.health_report()
    overall = "ok" if all(v["status"] == "healthy" for v in report.values()) else "degraded"
    return {"overall": overall, "agents": report}
```

レスポンス例：

```json
{
  "overall": "degraded",
  "agents": {
    "code-reviewer": {"status": "healthy",  "error": ""},
    "sql-analyst":   {"status": "degraded", "error": "Connection refused: http://sql-service/health"},
    "doc-writer":    {"status": "failed",   "error": "AGENT.md parse error: unknown key 'mdoel'"}
  }
}
```

### 18-4. 再起動なしの回復（オプション）

本番で外部サービスが一時停止した場合に `DEGRADED → HEALTHY` への回復を可能にする：

```python
def retry_ready(self, name: str) -> AgentStatus:
    """個別エージェントの on_ready を再実行"""
    entry = self._entries.get(name)
    if entry is None or entry.agent is None:
        raise KeyError(f"Agent '{name}' not retryable")
    try:
        entry.agent.ready()
        self._entries[name] = AgentEntry(entry.agent, AgentStatus.HEALTHY)
        return AgentStatus.HEALTHY
    except Exception as e:
        self._entries[name] = AgentEntry(entry.agent, AgentStatus.DEGRADED, str(e))
        return AgentStatus.DEGRADED
```

---

## 19. OrchestratorGraph ルーティング設計

### 19-1. 設計方針

ルーティングの精度 = システム全体の品質（§16 の指摘を具体化）。

**ルーター自体も LangGraph のノードとして実装し、AgentState の `next` フィールドに書き込む。**

### 19-2. description の記述規約

AGENT.md の `description` に以下の構造を必須とする：

```yaml
# NG（あいまい）
description: コードに関する処理を行うエージェント

# OK（境界が明確）
description: |
  Python/JavaScript/TypeScript コードの静的解析・リント・フォーマットチェックを行う。
  入力: コードスニペット（文字列）またはファイルパス
  出力: 指摘リスト、重大度（error/warning/info）、修正提案
  対象外: テスト実行 / デプロイ / DB操作 / ドキュメント生成
```

**`対象外` は必須フィールドとして lint する。** SubAgentRegistry がロード時に警告を出す：

```python
def _validate_description(meta: dict) -> None:
    desc = meta.get("description", "")
    if "対象外" not in desc and "not for" not in desc.lower():
        logger.warning(f"[{meta['name']}] description に '対象外' 節がありません。ルーティング精度が低下します。")
```

### 19-3. ルーターノードの実装

```python
ROUTER_PROMPT = """あなたはエージェントルーターです。
ユーザーの入力を読み、最も適切なエージェントを1つ選んでください。

## 利用可能なエージェント

{agent_descriptions}

## ルール
- 必ずエージェント名（name フィールドの値）のみを返す
- 該当なしの場合は "fallback" を返す
- 判断根拠は不要

## ユーザー入力
{user_input}
"""


class RouterNode:
    def __init__(self, registry: SubAgentRegistry, model: BaseChatModel):
        self.registry = registry
        self.model = model

    def __call__(self, state: AgentState) -> AgentState:
        agents = self.registry.all_usable()

        descriptions = "\n\n".join(
            f"name: {a.name}\ndescription: {a.description}"
            for a in agents
        )

        prompt = ROUTER_PROMPT.format(
            agent_descriptions=descriptions,
            user_input=state["input"],
        )

        response = self.model.invoke([HumanMessage(content=prompt)])
        chosen = response.content.strip()

        # バリデーション：存在しないエージェント名が返ってきた場合は fallback
        valid_names = {a.name for a in agents} | {"fallback"}
        if chosen not in valid_names:
            logger.warning(f"Router returned unknown agent '{chosen}', falling back")
            chosen = "fallback"

        logger.info(f"Router: '{state['input'][:50]}...' → {chosen}")
        return {"next": chosen}
```

### 19-4. OrchestratorGraph の構成

```python
from langgraph.graph import StateGraph, END


def build_orchestrator_graph(registry: SubAgentRegistry, router_model: BaseChatModel):
    graph = StateGraph(AgentState)

    # ルーターノード登録
    router = RouterNode(registry, router_model)
    graph.add_node("router", router)

    # サブエージェントノード登録
    for agent in registry.all_usable():
        graph.add_node(agent.name, agent.run)

    # フォールバックノード
    graph.add_node("fallback", fallback_node)

    # エントリーポイント
    graph.set_entry_point("router")

    # 条件付きエッジ：router の next フィールドで分岐
    graph.add_conditional_edges(
        "router",
        lambda state: state["next"],
        {agent.name: agent.name for agent in registry.all_usable()} | {"fallback": "fallback"},
    )

    # 各エージェントから END へ
    for agent in registry.all_usable():
        graph.add_edge(agent.name, END)
    graph.add_edge("fallback", END)

    return graph.compile()


def fallback_node(state: AgentState) -> AgentState:
    return {
        "output": "ご要望に対応できるエージェントが見つかりませんでした。質問を具体的にしてください。",
        "error": "no_agent_matched",
    }
```

### 19-5. ルーティング精度の改善サイクル

```
description を書く
  → テストケース（入力文）を用意
  → RouterNode を単体で実行してログを確認
  → "対象外" 節を充実させる or description を書き直す
  → 再テスト
```

ルーティングログを蓄積してミスルーティングを分析する：

```python
# ルーティングログのフォーマット（構造化ログ）
{
  "event": "routing",
  "input": "このコードをレビューして",
  "chosen": "code-reviewer",
  "candidates": ["code-reviewer", "sql-analyst", "doc-writer"],
  "thread_id": "thread-abc",
  "correlation_id": "corr-789"
}
```

---

## 20. input_schema 標準化

### 20-1. 規約

ツールスクリプトに `INPUT_SCHEMA` 定数を必須定義とする：

```python
# tools/lint.py

"""Python/JS/TS コードのリントチェックを行う。指摘リストと重大度を返す。"""

# モジュールレベルの定数として宣言（ASTで安全に取得できる）
INPUT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "code": {
            "type": "string",
            "description": "チェック対象のコード（文字列）",
        },
        "language": {
            "type": "string",
            "enum": ["python", "javascript", "typescript"],
            "description": "対象言語。省略時は自動判定",
        },
    },
    "required": ["code"],
}


def run(input: dict) -> str:
    code = input["code"]
    language = input.get("language", "auto")
    # ...実装...
    return "ok"
```

### 20-2. AST 抽出の実装

```python
import ast
from pathlib import Path


def _read_tool_meta(tool_path: Path) -> dict:
    source = tool_path.read_text()
    tree = ast.parse(source)

    # docstring → description
    description = ast.get_docstring(tree) or ""

    # INPUT_SCHEMA 定数を AST から安全に取得
    input_schema: dict = {"type": "object", "properties": {}, "required": []}
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "INPUT_SCHEMA"
        ):
            try:
                input_schema = ast.literal_eval(node.value)
            except (ValueError, TypeError) as e:
                logger.warning(f"{tool_path}: INPUT_SCHEMA の評価失敗: {e}")
            break
    else:
        logger.warning(f"{tool_path}: INPUT_SCHEMA が未定義です")

    return {
        "description": description,
        "input_schema": input_schema,
    }
```

### 20-3. バリデーション（呼び出し前チェック）

`jsonschema` を使って呼び出し前に入力値を検証する：

```python
import jsonschema


class ScriptBackend(ToolBackend):
    def execute(self, input: dict, context: RPCContext) -> str:
        # スキーマバリデーション（呼び出し前）
        try:
            jsonschema.validate(instance=input, schema=self.meta["input_schema"])
        except jsonschema.ValidationError as e:
            raise ValueError(f"Tool input validation failed: {e.message}") from e

        # 実行
        spec = importlib.util.spec_from_file_location("_tool", self.tool_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.run(input)
```

### 20-4. LLM へのツール定義の渡し方

Anthropic API の `tools` パラメーター形式に変換：

```python
def to_anthropic_tool(scoped_name: str, meta: dict) -> dict:
    """
    AgentState のツール定義を Anthropic API フォーマットに変換
    """
    return {
        "name": scoped_name,                      # "code-reviewer__lint"
        "description": meta["description"],
        "input_schema": meta["input_schema"],     # そのまま渡せる形式
    }


# SubAgent.run() 内での使用
tools_for_llm = [
    to_anthropic_tool(name, tool["meta"])
    for name, tool in self._tools.items()
]
```

### 20-5. ツール定義の lint スクリプト（CI 用）

```python
# scripts/lint_tools.py
# CI で全ツールの INPUT_SCHEMA 欠落・スキーマ不正を検出する

from pathlib import Path
import ast, sys

errors = []
for path in Path("agents").glob("**/tools/*.py"):
    source = path.read_text()
    tree = ast.parse(source)
    has_schema = any(
        isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "INPUT_SCHEMA" for t in n.targets)
        for n in ast.walk(tree)
    )
    if not has_schema:
        errors.append(f"MISSING INPUT_SCHEMA: {path}")

if errors:
    print("\n".join(errors))
    sys.exit(1)

print(f"All tools OK ({len(list(Path('agents').glob('**/tools/*.py')))} files)")
```

---

## 補完案：第12章

元ドキュメントは 11（ライフサイクル）→ **12（欠番）** → 13（REST API）の順。
流れから推測すると **オブザーバビリティ（ロギング・トレーシング・メトリクス）** か
**キャッシュ実装詳細（watchdog 連携）** が有力候補。

次回検討課題に「キャッシュ戦略の実装詳細（watch モードの watchdog 連携）」が
リストされていた点から、**キャッシュ実装詳細** の可能性が高い。

補完案（仮）：

```
## 12. キャッシュ実装詳細

12-1. lazy ファイルの TTL キャッシュ実装
12-2. watch モードの watchdog 連携
12-3. 環境変数による TTL 制御の実装
12-4. キャッシュのキー設計（パス + mtime ハッシュ）
```

覚えていなければ、オブザーバビリティ（構造化ログ・X-Correlation-Id の活用・
メトリクス収集）で埋めるのも自然な流れ。どちらかを選んで詳細化する。
