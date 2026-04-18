# Phase 29: ユーザー選択モデルのエージェントデフォルト優先 - Pattern Map

**Mapped:** 2026-04-18
**Files analyzed:** 3（変更対象 2 + 新規テスト 1）
**Analogs found:** 3 / 3

## File Classification

| 新規/変更ファイル | Role | Data Flow | Closest Analog | Match Quality |
|------------------|------|-----------|----------------|---------------|
| `app/jobs/handlers/orchestrator_handler.py` | handler | request-response | `app/jobs/handlers/langgraph_handler.py` | role-match |
| `app/orchestrator/agent.py` | service | request-response | `app/orchestrator/tool_agent.py` | exact |
| `tests/test_model_override.py` (新規) | test | — | `tests/test_subagent_registry_tools.py` | exact |

---

## Pattern Assignments

### `app/jobs/handlers/orchestrator_handler.py` (handler, request-response)

**Analog:** `app/jobs/handlers/orchestrator_handler.py`（自ファイルの現状コードをそのまま参照）

**変更箇所: job dict から model_override を読み取る（行 30-31 付近）**

現状コード（行 26-31）:
```python
async def handle(self, ctx: dict, job: dict) -> dict:
    job_id: str = job["job_id"]
    thread_id: str = job["thread_id"]
    prompt: str = job["prompt"]
    github_token: str = job["github_token"]
    # model is intentionally unused in super mode; each agent's AGENT.md defines its own model
    reply_to: dict = job["reply_to"]
```

変更後パターン（行 30 のコメントを削除し model_override 読み取りを追加）:
```python
    github_token: str = job["github_token"]
    # model_override: フロントで選択したモデル（未選択/空文字時は None → AGENT.md の model を使用）
    model_override: str | None = job.get("model") or None
    reply_to: dict = job["reply_to"]
```

**変更箇所: SubAgentRegistry 呼び出し（行 42-47 付近）**

現状コード:
```python
        registry = SubAgentRegistry(
            AGENT_DIR,
            github_token,
            mcp_tools=mcp_tools or None,
            privileged_tool_names=privileged_names,
        )
```

変更後パターン:
```python
        registry = SubAgentRegistry(
            AGENT_DIR,
            github_token,
            mcp_tools=mcp_tools or None,
            privileged_tool_names=privileged_names,
            model_override=model_override,
        )
```

**変更箇所: GemSubAgent 生成部分（行 76-83 付近）**

現状コード:
```python
                        gem_agent = GemSubAgent(
                            name=gem_name,
                            system_prompt=gem_system_prompt or "",
                            github_token=github_token,
                        )
```

変更後パターン（`DEFAULT_MODEL` インポートを gem_agent.py から追加）:
```python
                    from app.orchestrator.gem_agent import GemSubAgent, DEFAULT_MODEL
                    # ...（DBフェッチループ内）
                        gem_agent = GemSubAgent(
                            name=gem_name,
                            system_prompt=gem_system_prompt or "",
                            github_token=github_token,
                            model=model_override or DEFAULT_MODEL,
                        )
```

注意: 行 61 の `from app.orchestrator.gem_agent import GemSubAgent` は既にあるので、
`DEFAULT_MODEL` だけをインポート追加するか、行 61 のインポートを統合する。

---

### `app/orchestrator/agent.py` (service, request-response)

**Analog:** `app/orchestrator/tool_agent.py`（ToolEnabledSubAgent の `__init__` / `from_dir` パターン）

**変更箇所 1: SubAgent.from_dir に model_override を追加（行 101-112）**

現状コード:
```python
    @classmethod
    def from_dir(cls, agent_dir: Path, github_token: str) -> "SubAgent":
        post = frontmatter.load(agent_dir / "AGENT.md")
        meta = post.metadata
        return cls(
            name=meta["name"],
            description=meta["description"],
            model=meta.get("model", "claude-sonnet-4-6"),
            system_prompt=post.content,
            github_token=github_token,
            keywords=meta.get("keywords", []),
        )
```

変更後パターン（`tool_agent.py` の `from_dir` シグネチャ拡張パターンを踏襲）:
```python
    @classmethod
    def from_dir(
        cls,
        agent_dir: Path,
        github_token: str,
        model_override: str | None = None,
    ) -> "SubAgent":
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

**変更箇所 2: SubAgentRegistry.__init__ に model_override を追加（行 149-155）**

現状コード:
```python
class SubAgentRegistry:
    def __init__(
        self,
        agent_dir: str,
        github_token: str,
        mcp_tools: list | None = None,
        privileged_tool_names: frozenset[str] | set[str] | None = None,
    ):
```

変更後パターン:
```python
class SubAgentRegistry:
    def __init__(
        self,
        agent_dir: str,
        github_token: str,
        mcp_tools: list | None = None,
        privileged_tool_names: frozenset[str] | set[str] | None = None,
        model_override: str | None = None,
    ):
```

**変更箇所 3: Registry 内 CodeActSubAgent 生成（行 187-197 付近）**

現状コード:
```python
                            agent = CodeActSubAgent(
                                name=meta["name"],
                                description=meta["description"],
                                model=meta.get("model", "gpt-4.1"),
                                system_prompt=post.content,
                                github_token=github_token,
                                tools=selected_tools,
                                keywords=meta.get("keywords", []),
                                max_iterations=meta.get("max_iterations", 3),
                            )
```

変更後パターン:
```python
                            agent = CodeActSubAgent(
                                name=meta["name"],
                                description=meta["description"],
                                model=model_override or meta.get("model", "gpt-4.1"),
                                system_prompt=post.content,
                                github_token=github_token,
                                tools=selected_tools,
                                keywords=meta.get("keywords", []),
                                max_iterations=meta.get("max_iterations", 3),
                            )
```

**変更箇所 4: Registry 内 ToolEnabledSubAgent 生成（行 199-207 付近）**

現状コード:
```python
                            agent = ToolEnabledSubAgent(
                                name=meta["name"],
                                description=meta["description"],
                                model=meta.get("model", "claude-sonnet-4-6"),
                                system_prompt=post.content,
                                github_token=github_token,
                                tools=selected_tools,
                                keywords=meta.get("keywords", []),
                            )
```

変更後パターン:
```python
                            agent = ToolEnabledSubAgent(
                                name=meta["name"],
                                description=meta["description"],
                                model=model_override or meta.get("model", "claude-sonnet-4-6"),
                                system_prompt=post.content,
                                github_token=github_token,
                                tools=selected_tools,
                                keywords=meta.get("keywords", []),
                            )
```

**変更箇所 5: Registry 内 SubAgent.from_dir 呼び出し箇所 2か所（行 214、217 付近）**

現状コード（2か所）:
```python
                            agent = SubAgent.from_dir(path.parent, github_token)
                            ...
                        agent = SubAgent.from_dir(path.parent, github_token)
```

変更後パターン（2か所とも）:
```python
                            agent = SubAgent.from_dir(path.parent, github_token, model_override=model_override)
                            ...
                        agent = SubAgent.from_dir(path.parent, github_token, model_override=model_override)
```

---

### `tests/test_model_override.py` (test, 新規)

**Analog:** `tests/test_subagent_registry_tools.py`（SubAgentRegistry を tmp_path + mock_copilot_cls で検証するパターン）

**フィクスチャパターン（`tests/test_subagent_registry_tools.py` 行 51-56）:**
```python
@pytest.fixture
def mock_copilot_cls():
    """Patch ChatCopilot so no Copilot SDK is instantiated."""
    with patch("app.providers.copilot.CopilotClient"), \
         patch("app.providers.copilot.SubprocessConfig"), \
         patch("app.providers.copilot.PermissionHandler"):
        yield
```

**AGENT.md 書き込みヘルパーパターン（`tests/test_subagent_registry_tools.py` 行 16-48）:**
```python
def write_agent_md(agent_dir: Path, *, with_tools: bool = True) -> None:
    agent_dir.mkdir(parents=True, exist_ok=True)
    content = textwrap.dedent("""\
        ---
        name: test-agent
        keywords: []
        description: |
          テスト用エージェント。
          対象外: なし
        model: gpt-4.1
        ---

        テスト用プロンプト。
    """)
    (agent_dir / "AGENT.md").write_text(content)
```

**Registry 生成パターン（`tests/test_subagent_registry_tools.py` 行 77-91）:**
```python
def test_registry_creates_tool_enabled_agent(tmp_path, mock_copilot_cls):
    from app.orchestrator.agent import SubAgentRegistry
    from app.orchestrator.tool_agent import ToolEnabledSubAgent

    write_agent_md(tmp_path / "test-agent", with_tools=True)
    mock_mcp_tools = make_mock_tools()

    registry = SubAgentRegistry(str(tmp_path), "ghu_test", mcp_tools=mock_mcp_tools)

    assert "test-agent" in registry.agents
    agent = registry.agents["test-agent"]
    assert isinstance(agent, ToolEnabledSubAgent)
```

**新規テストで追加すべきケース（このパターンを拡張して作成）:**
```python
def test_registry_model_override_applies_to_subagent(tmp_path, mock_copilot_cls):
    """model_override が SubAgent._llm.model に反映される。"""
    from app.orchestrator.agent import SubAgent, SubAgentRegistry

    write_agent_md(tmp_path / "folder-agent")
    registry = SubAgentRegistry(str(tmp_path), "ghu_test", model_override="gpt-4o")

    agent = registry.agents["folder-agent"]
    assert isinstance(agent, SubAgent)
    assert agent._llm.model == "gpt-4o"


def test_registry_no_model_override_uses_agent_md(tmp_path, mock_copilot_cls):
    """model_override=None のとき AGENT.md の model フィールドが使われる。"""
    from app.orchestrator.agent import SubAgent, SubAgentRegistry

    write_agent_md(tmp_path / "folder-agent")  # model: gpt-4.1 in AGENT.md
    registry = SubAgentRegistry(str(tmp_path), "ghu_test", model_override=None)

    agent = registry.agents["folder-agent"]
    assert agent._llm.model == "gpt-4.1"
```

---

## Shared Patterns

### 空文字 → None 変換（Anti-Pitfall）
**Source:** `app/jobs/handlers/orchestrator_handler.py`（新規追加箇所）
**Apply to:** `orchestrator_handler.py` の model_override 読み取り行のみ
```python
model_override: str | None = job.get("model") or None
```
Python の `or` で空文字列 `""` と `None` を同時に `None` に変換する。
`job.get("model", None)` では空文字が素通りするため必ずこの形式にする。

### `or` フォールバックによるモデル優先（コアパターン）
**Source:** `app/orchestrator/agent.py`（変更後）
**Apply to:** agent.py 内の全エージェント生成箇所（CodeActSubAgent / ToolEnabledSubAgent / SubAgent.from_dir）
```python
model=model_override or meta.get("model", "<default>"),
```
- `model_override` が `None` または空文字のとき、AGENT.md の値にフォールバック
- `<default>` は SubAgent/ToolEnabledSubAgent で `"claude-sonnet-4-6"`、CodeActSubAgent で `"gpt-4.1"`

### ChatCopilot 初期化パターン（変更なし・参照のみ）
**Source:** `app/orchestrator/agent.py` 行 98、`app/orchestrator/tool_agent.py` 行 244
```python
self._llm = ChatCopilot(model=model, github_token=github_token)
```
`model` 引数を `__init__` で受け取り、ChatCopilot に渡す。run() では変更しない。

---

## No Analog Found

なし。全変更対象ファイルに対して既存の近似アナログが存在する。

---

## Metadata

**Analog search scope:** `app/jobs/handlers/`, `app/orchestrator/`, `tests/`
**Files scanned:** 6（orchestrator_handler.py, agent.py, tool_agent.py, gem_agent.py, test_subagent_registry_tools.py, test_tool_enabled_subagent.py）
**Pattern extraction date:** 2026-04-18
