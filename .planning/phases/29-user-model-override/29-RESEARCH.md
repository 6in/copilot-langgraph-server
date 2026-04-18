# Phase 29: ユーザー選択モデルのエージェントデフォルト優先 - Research

**Researched:** 2026-04-18
**Domain:** Python / LangGraph エージェント初期化パラメータ伝播
**Confidence:** HIGH

## Summary

本フェーズは UX 改善フェーズ（REQ-ID なし）であり、フロントエンドで選択したモデルが SuperChat モードの
エージェントデフォルト（AGENT.md `model` フィールド）より優先される仕組みを実装する。

現状分析の結果、「データパイプライン」はすでに整備済みであることが判明した。
フロントエンドは `selectedModel` を `POST /api/chat` に送信し、`chat.py` はそれを arq ジョブペイロードに
含め、`worker.py` の `process_chat` は `model` フィールドを `job` dict に詰める。
しかし `orchestrator_handler.py` の 30 行目コメント通り、Orchestrator 経路では `model` が無視される。

変更スコープは「インフラ・データフロー修正」ではなく「ロジック一点修正」で、
`orchestrator_handler.py` → `SubAgentRegistry.__init__` → 各 SubAgent クラスの `__init__`
という三段の `model_override` 伝播のみで完結する。

**Primary recommendation:** `model_override: str | None` を `SubAgentRegistry.__init__` に追加し、
`SubAgent` / `ToolEnabledSubAgent` / `CodeActSubAgent` のコンストラクタにも伝播させる。
`orchestrator_handler.py` で `job["model"]` が空文字でない場合に渡す。`GemSubAgent` は
`SubAgent` を継承しているため親クラスの変更だけで自動対応する。

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| モデル選択 UI | Browser / Client | — | Header の `<select>` から `selectedModel` state を管理 |
| model フィールド送信 | Frontend (useChat.ts) | — | `postChat({model: selectedModel, ...})` 済み |
| model の arq ペイロード化 | API / Backend (chat.py) | — | `body.model` を enqueue_job に渡す実装済み |
| model の job dict 詰め込み | Worker (worker.py) | — | `process_chat` の `job` dict に `model` 含む実装済み |
| **model_override 伝播（未実装）** | **Worker (orchestrator_handler.py)** | — | `job["model"]` を Registry に渡す必要あり |
| **エージェント初期化時 model 優先（未実装）** | **Worker (agent.py / tool_agent.py / codeact_agent.py)** | — | `ChatCopilot(model=model_override or agent_model)` に変更必要 |

## Standard Stack

### Core（変更なし、参照のみ）

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `ChatCopilot` | (内製) | Copilot SDK ラッパー | `model` パラメータを `create_session` に渡す |
| `SubAgentRegistry` | (内製) | エージェント一覧管理 | AGENT.md 自動ロード、エージェント生成を集約 |
| `SubAgent` | (内製) | 基本エージェント | `__init__` の `model` パラメータで ChatCopilot を初期化 |
| `ToolEnabledSubAgent` | (内製) | ツール付きエージェント | 同上 |
| `CodeActSubAgent` | (内製) | コード実行エージェント | 同上 |
| `GemSubAgent` | (内製) | Gem ベースエージェント | `SubAgent` を継承、変更不要 |

### Supporting

変更対象外。

## Architecture Patterns

### データフロー（現状）

```
Frontend (Header <select>)
  selectedModel = "gpt-4.1"
    ↓ useChat.ts / postChat()
POST /api/chat  { model: "gpt-4.1", mode: "super", ... }
    ↓ chat.py
arq enqueue_job(model="gpt-4.1", task_type="orchestrator", ...)
    ↓ worker.py / process_chat()
job = { "model": "gpt-4.1", ... }
    ↓ OrchestratorHandler.handle()
[現状] job["model"] は読まれず AGENT.md の model が使われる
SubAgentRegistry(agent_dir, github_token, mcp_tools=...) ←── model 未渡し
  ↓
SubAgent.__init__(model="claude-sonnet-4-6", ...)  ←── AGENT.md の値固定
  ↓
ChatCopilot(model="claude-sonnet-4-6")
```

### データフロー（変更後）

```
同上（Frontend〜worker.py は無変更）
    ↓
OrchestratorHandler.handle()
  model_override = job.get("model") or None   ←── NEW
  SubAgentRegistry(..., model_override=model_override)   ←── NEW
    ↓
SubAgent.__init__(model=model_override or agent_model, ...)   ←── NEW
  ↓
ChatCopilot(model=model_override or "claude-sonnet-4-6")   ←── model が上書きされる
```

### Pattern 1: model_override パラメータ追加

**What:** `SubAgentRegistry.__init__` に `model_override: str | None = None` を追加し、
全エージェント種別のコンストラクタに渡す。

**When to use:** `orchestrator_handler.py` から呼ぶとき。

```python
# Source: [VERIFIED: app/orchestrator/agent.py 読み込み]
class SubAgentRegistry:
    def __init__(
        self,
        agent_dir: str,
        github_token: str,
        mcp_tools: list | None = None,
        privileged_tool_names: frozenset[str] | set[str] | None = None,
        model_override: str | None = None,   # NEW
    ):
        ...
        # SubAgent 生成時
        agent = SubAgent.from_dir(path.parent, github_token, model_override=model_override)
        # ToolEnabledSubAgent 生成時
        agent = ToolEnabledSubAgent(..., model=model_override or meta.get("model", "claude-sonnet-4-6"), ...)
        # CodeActSubAgent 生成時
        agent = CodeActSubAgent(..., model=model_override or meta.get("model", "gpt-4.1"), ...)
```

### Pattern 2: SubAgent.from_dir に model_override を渡す

```python
# Source: [VERIFIED: app/orchestrator/agent.py 読み込み]
@classmethod
def from_dir(cls, agent_dir: Path, github_token: str, model_override: str | None = None) -> "SubAgent":
    post = frontmatter.load(agent_dir / "AGENT.md")
    meta = post.metadata
    return cls(
        ...
        model=model_override or meta.get("model", "claude-sonnet-4-6"),
        ...
    )
```

### Pattern 3: orchestrator_handler での model_override 読み取り

```python
# Source: [VERIFIED: app/jobs/handlers/orchestrator_handler.py 読み込み]
# 行 30 付近（現状コメント）
# model is intentionally unused in super mode; each agent's AGENT.md defines its own model
# ↓ 変更後:
model_override: str | None = job.get("model") or None   # 空文字はNoneに変換

registry = SubAgentRegistry(
    AGENT_DIR,
    github_token,
    mcp_tools=mcp_tools or None,
    privileged_tool_names=privileged_names,
    model_override=model_override,   # NEW
)
```

### Pattern 4: GemSubAgent は変更不要

`GemSubAgent` は `SubAgent` を継承しており `model` パラメータを受け取る `__init__` がある。
現状 `GemSubAgent` は `OrchestratorHandler` で直接インスタンス化されているが、
その際も `model` パラメータを `model_override or DEFAULT_MODEL` にすれば対応できる。

```python
# OrchestratorHandler の gem_agent 生成部分（行 78）
gem_agent = GemSubAgent(
    name=gem_name,
    system_prompt=gem_system_prompt or "",
    github_token=github_token,
    model=model_override or GemSubAgent.__init__.__defaults__[0],  # DEFAULT_MODEL
)
```

より読みやすくするなら:

```python
from app.orchestrator.gem_agent import GemSubAgent, DEFAULT_MODEL
gem_agent = GemSubAgent(
    name=gem_name,
    system_prompt=gem_system_prompt or "",
    github_token=github_token,
    model=model_override or DEFAULT_MODEL,
)
```

### Anti-Patterns to Avoid

- **空文字列を model_override として渡す:** フロントエンドが未選択時に空文字を送ることがある。`job.get("model") or None` でフォールバックを確実にする
- **`model_override` を SubAgent の `run()` メソッドに渡す:** `model` は `__init__` 時に `ChatCopilot` を初期化するパラメータであり、実行時に変更するものではない。初期化時の 1 回変更で完結する
- **通常 Chat モード（langgraph_handler）を変更する:** `model` はすでに `langgraph_handler.py` 経由で `ChatCopilot` に渡されている。SuperChat 専用の修正に限定する

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| model 優先判定 | 複雑な優先順位ロジック | `model_override or agent_default` | Python の `or` で十分。単純な fallback |
| モデル名バリデーション | 独自バリデーター | 不要（ChatCopilot が SDK に渡すだけ） | Copilot SDK が不正モデル名をエラーにする |

## Common Pitfalls

### Pitfall 1: 空文字列の model フィールド

**What goes wrong:** フロントエンドの `selectedModel` が空文字 `""` のとき `job["model"]` も `""` になる。
`job.get("model")` は `""` を返すため、`or None` をつけないと空文字を `model_override` に渡してしまう。

**Why it happens:** JavaScript で `""` は falsy だが Python の dict.get() は `""` を正常値として返す。

**How to avoid:** `model_override = job.get("model") or None` — Python の `or` で空文字を `None` に変換する。

**Warning signs:** エージェントが空モデル名でエラーを吐く

### Pitfall 2: GemSubAgent の model が DEFAULT_MODEL ハードコード

**What goes wrong:** `GemSubAgent` 生成コードが `OrchestratorHandler` に直接書かれており、
`model_override` 変数が定義された後の行であれば参照できるが、変数スコープを確認せずに修正すると
`NameError` になる可能性がある。

**How to avoid:** `gem_agent = GemSubAgent(..., model=model_override or DEFAULT_MODEL)` と明示的に記述し、
`from app.orchestrator.gem_agent import DEFAULT_MODEL` をインポートする。

### Pitfall 3: ToolEnabledSubAgent の _llm_with_tools が初期化時に bind_tools を呼ぶ

**What goes wrong:** `ToolEnabledSubAgent.__init__` で `self._llm_with_tools = self._llm.bind_tools(tools)`
が呼ばれる。`model_override` を `self._llm` の初期化時（`ChatCopilot(model=...)` 生成時）に反映しないと、
`bind_tools` は古い model のまま実行されてしまう。

**Why it happens:** `__init__` の処理順が `self._llm = ChatCopilot(model=...) → self._llm_with_tools = self._llm.bind_tools(...)` であるため、`ChatCopilot` の `model` が正しければ `bind_tools` も正しい model で動く。

**How to avoid:** コンストラクタで `model=model_override or agent_model` を確実に渡す。追加の変更は不要。

### Pitfall 4: code-type エージェント（agent.py）の model_override

**What goes wrong:** `_load_code_agent` で読み込む code-type エージェントは `SubAgent.from_dir()` ではなく
`agent_cls.from_dir(agent_dir, github_token)` を呼ぶ。このシグネチャには `model_override` がない。

**Why it happens:** code-type エージェントは独自の `from_dir` クラスメソッドを持つことを想定している。

**How to avoid:** code-type エージェントは `model_override` を渡せないため、このフェーズでは対象外とする。
AGENT.md ベースエージェント（folder / folder+tools / codeact）のみ対象にする。
コメントで明示しておく。

## Code Examples

### orchestrator_handler.py の変更箇所

```python
# Source: [VERIFIED: app/jobs/handlers/orchestrator_handler.py を読み込み確認]

async def handle(self, ctx: dict, job: dict) -> dict:
    job_id: str = job["job_id"]
    thread_id: str = job["thread_id"]
    prompt: str = job["prompt"]
    github_token: str = job["github_token"]
    # model_override: フロントで選択したモデル（未選択時は None）
    model_override: str | None = job.get("model") or None
    reply_to: dict = job["reply_to"]
    ...
    registry = SubAgentRegistry(
        AGENT_DIR,
        github_token,
        mcp_tools=mcp_tools or None,
        privileged_tool_names=privileged_names,
        model_override=model_override,
    )
    ...
    # GemSubAgent 生成部分（行 78 付近）
    from app.orchestrator.gem_agent import GemSubAgent, DEFAULT_MODEL
    gem_agent = GemSubAgent(
        name=gem_name,
        system_prompt=gem_system_prompt or "",
        github_token=github_token,
        model=model_override or DEFAULT_MODEL,
    )
```

### agent.py の変更箇所（SubAgent.from_dir）

```python
# Source: [VERIFIED: app/orchestrator/agent.py を読み込み確認]

@classmethod
def from_dir(cls, agent_dir: Path, github_token: str, model_override: str | None = None) -> "SubAgent":
    post = frontmatter.load(agent_dir / "AGENT.md")
    meta = post.metadata
    return cls(
        name=meta["name"],
        description=meta["description"],
        model=model_override or meta.get("model", "claude-sonnet-4-6"),
        system_prompt=post.content,
        github_token=github_token,
        keywords=meta.get("keywords", []),
    )
```

### SubAgentRegistry.__init__ の変更箇所（ToolEnabledSubAgent / CodeActSubAgent 生成）

```python
# Source: [VERIFIED: app/orchestrator/agent.py を読み込み確認]

# ToolEnabledSubAgent 生成（行 199 付近）
agent = ToolEnabledSubAgent(
    name=meta["name"],
    description=meta["description"],
    model=model_override or meta.get("model", "claude-sonnet-4-6"),  # ← model_override 優先
    ...
)

# CodeActSubAgent 生成（行 187 付近）
agent = CodeActSubAgent(
    name=meta["name"],
    description=meta["description"],
    model=model_override or meta.get("model", "gpt-4.1"),  # ← model_override 優先
    ...
)

# tools なし folder エージェント（行 214 付近）
agent = SubAgent.from_dir(path.parent, github_token, model_override=model_override)
```

## Implementation Scope

### 変更対象ファイル（最小限）

| ファイル | 変更内容 | 難易度 |
|---------|---------|-------|
| `app/jobs/handlers/orchestrator_handler.py` | `model_override = job.get("model") or None` を読んで Registry に渡す | 低 |
| `app/orchestrator/agent.py` | `SubAgentRegistry.__init__` に `model_override` 追加。`SubAgent.from_dir` に `model_override` 追加。Registry 内の各エージェント生成コードで適用 | 低-中 |

### 変更不要ファイル

| ファイル | 理由 |
|---------|-----|
| `app/orchestrator/tool_agent.py` | `ToolEnabledSubAgent.__init__(model=...)` は既に外から渡す設計。Registry が正しく渡せばよい |
| `app/orchestrator/codeact_agent.py` | 同上 |
| `app/orchestrator/gem_agent.py` | `SubAgent` 継承。`model` パラメータあり。`orchestrator_handler.py` の gem 生成箇所で直接渡す |
| `app/api/routes/chat.py` | `body.model` を既に enqueue_job に渡している（実装済み） |
| `frontend/src/hooks/useChat.ts` | `model: selectedModel` を既に postChat に渡している（実装済み） |
| `app/jobs/worker.py` | `process_chat` が `model` を `job` dict に詰めている（実装済み） |
| `app/jobs/handlers/langgraph_handler.py` | 通常 Chat モードは既に `model` を使って ChatCopilot を初期化している |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| model 無視 (SuperChat) | model_override 優先 | Phase 29 | ユーザーのモデル選択が全エージェントに反映される |

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (既存) |
| Config file | `pyproject.toml` の `[tool.pytest.ini_options]` |
| Quick run command | `docker compose exec api pytest tests/ -x -q 2>/dev/null` |
| Full suite command | `docker compose exec api pytest tests/ -q 2>/dev/null` |

### Phase Requirements → Test Map

本フェーズは REQ-ID なし (UX 改善)。ただし動作検証として以下を確認する。

| 検証項目 | テスト種別 | 確認方法 |
|---------|----------|---------|
| model_override が SubAgent に渡る | unit | pytest で SubAgentRegistry に model_override を渡し、生成された SubAgent の `_llm.model` を assert |
| model 未指定時は AGENT.md の model が使われる | unit | model_override=None 時に AGENT.md の値が使われることを assert |
| ToolEnabledSubAgent に model_override が反映される | unit | 同様 |
| GemSubAgent に model_override が反映される | unit | 直接 GemSubAgent(model=...) を確認 |
| 通常 Chat モード（langgraph_handler）に影響がない | integration | 既存 langgraph テストが Pass のまま |

### Wave 0 Gaps

- [ ] `tests/test_model_override.py` — 上記 unit テストカバー

既存テスト基盤（`tests/`）は存在するため、フレームワーク追加不要。

## Environment Availability

Step 2.6: SKIPPED (外部依存なし。コード変更のみ)

## Security Domain

本フェーズはモデル名選択の伝播であり、新たなセキュリティ境界は生まれない。
`model` 値は `ChatCopilot` 経由で Copilot SDK の `create_session` に渡されるだけで、
ユーザー入力が直接 SQL や shell に渡ることはない。

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | no | model 名は SDK が検証する。不正値はサーバーサイドエラーとして応答 |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `job.get("model")` が空文字になりうる | Pitfall 1 | 空文字をそのまま渡すと ChatCopilot がエラー。`or None` で対策済み |
| A2 | code-type エージェント（agent.py）は本フェーズ対象外 | Pitfall 4 | code-type の model が変わらない。許容範囲と判断 |

## Open Questions (RESOLVED)

1. **モデル未選択時のデフォルト値**
   - What we know: `App.tsx` の初期値は `useState('gpt-4.1')` → 常に何らかのモデルが選ばれている
   - RESOLVED: 空文字の場合のみ None 扱いとし、`gpt-4.1` 等の値が来た場合は常に model_override として使用する。「エージェントデフォルト優先」モードの UI は不要 — 空文字送信でフォールバックが機能する

## Sources

### Primary (HIGH confidence)

- `app/jobs/handlers/orchestrator_handler.py` 全文読み込み — model フィールド無視のコメント確認
- `app/orchestrator/agent.py` 全文読み込み — SubAgent / SubAgentRegistry 構造確認
- `app/orchestrator/tool_agent.py` 全文読み込み — ToolEnabledSubAgent 構造確認
- `app/orchestrator/codeact_agent.py` 全文読み込み — CodeActSubAgent 構造確認
- `app/orchestrator/gem_agent.py` 全文読み込み — GemSubAgent 構造確認
- `app/api/routes/chat.py` — model フィールドの enqueue_job 渡し確認（実装済み）
- `app/jobs/worker.py` — process_chat の job dict 構造確認（model 含む）
- `frontend/src/hooks/useChat.ts` — selectedModel の postChat 送信確認（実装済み）

### Secondary (MEDIUM confidence)

なし

### Tertiary (LOW confidence)

なし

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — コードを直接読み込み、全パスを確認
- Architecture: HIGH — データフローを全ファイル追跡
- Pitfalls: HIGH — 実際のコードから空文字、継承構造、初期化順序を確認

**Research date:** 2026-04-18
**Valid until:** 2026-06-18（コード変更がない限り有効）
