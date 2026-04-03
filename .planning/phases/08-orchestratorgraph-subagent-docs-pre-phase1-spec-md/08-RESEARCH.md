# Phase 8: スーパーエージェントサンプル実装 - Research

**Researched:** 2026-04-03
**Domain:** LangGraph multi-agent orchestration (OrchestratorGraph + RouterNode + SubAgent), langchain-anthropic, python-frontmatter
**Confidence:** HIGH

---

## Summary

Phase 8 implements a standalone sample demonstrating the OrchestratorGraph + SubAgent architecture as defined in `docs/pre/phase1_spec.md`. The sample is a self-contained Python project placed in a new subdirectory (e.g., `super-agent-sample/`) at the repo root, developed on a **separate branch**. It does NOT modify the main FastAPI application.

The spec is complete and prescriptive: all file content, class interfaces, and data structures are specified verbatim. The planner's job is to decompose the spec into sequential tasks (scaffolding, module implementation, agent definitions, menu definitions, entry point, tests, smoke run). The primary technical risks are: (1) the `PYTHONPATH=src` requirement that the spec omits from its run command, (2) model name verification (confirmed valid against Anthropic docs), and (3) `ANTHROPIC_API_KEY` must be set for the smoke test.

**Primary recommendation:** Implement the sample exactly as specified in `docs/pre/phase1_spec.md` in a `super-agent-sample/` subdirectory on a feature branch, adding `PYTHONPATH=src` to the run command and `pythonpath = ["src"]` to pytest config.

---

## Project Constraints (from CLAUDE.md)

- **Tech Stack:** Python (LangChain / LangGraph / Copilot SDK) — the main app constraint. Phase 8 sample uses `langchain-anthropic` (ChatAnthropic) per spec, NOT ChatCopilot. This is intentional and allowed as a standalone sample.
- **GSD Workflow:** Before file-changing operations, start through a GSD command. Phase is planned via `/gsd:execute-phase`.
- **No direct edits outside GSD:** Phase 8 work must stay in the feature branch and sample directory.
- **Architecture convention:** The main app's `app/` directory is NOT modified by this phase.
- **uv:** Use `uv sync` and `uv run` for the sample's own pyproject.toml.
- **Separate branch:** "別ブランチ作業" — create a feature branch (e.g., `feat/super-agent-sample`) before starting.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SAMPLE-01 | Create standalone `super-agent-sample/` directory with its own `pyproject.toml` | Spec section 2, 10 |
| SAMPLE-02 | Implement `AgentState` TypedDict in `src/state.py` | Spec section 4 |
| SAMPLE-03 | Implement `SubAgent` and `SubAgentRegistry` in `src/agent.py` | Spec section 5 |
| SAMPLE-04 | Implement `RouterNode`, `OrchestratorGraph`, `build_simple_graph` in `src/graph.py` | Spec section 6 |
| SAMPLE-05 | Implement `MenuRegistry` and `MenuDispatcher` in `src/dispatcher.py` | Spec section 7 |
| SAMPLE-06 | Create `agents/code-reviewer/AGENT.md` and `agents/sql-analyst/AGENT.md` | Spec section 3 |
| SAMPLE-07 | Create `menus/super-chat.yaml` and `menus/simple-chat.yaml` | Spec section 8 |
| SAMPLE-08 | Implement `src/main.py` entry point with 4 test cases | Spec section 9 |
| SAMPLE-09 | Smoke test: all 4 verification points pass (routing log, sub-agent exec, fallback, simple-chat) | Spec section 11 |
| SAMPLE-10 | Unit tests for `SubAgentRegistry`, `RouterNode`, `MenuDispatcher` (mocked LLM) | Nyquist validation — pytest required |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `langchain-anthropic` | 1.4.0 | ChatAnthropic LLM provider | Specified in spec. Standard LangChain integration for Anthropic Claude. |
| `langgraph` | 1.1.4 | StateGraph, conditional_edges, END | Already in main project. The orchestration backbone. |
| `langchain-core` | latest | HumanMessage, AIMessage, SystemMessage, BaseMessage | Already in main project. Required by langgraph. |
| `python-frontmatter` | 1.1.0 | Parse AGENT.md frontmatter (YAML) + body | Specified in spec as `frontmatter` (installed as `python-frontmatter`). |
| `pyyaml` | 6.0.3 | Parse `menus/*.yaml` files | Specified in spec. Already in the uv env globally. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | 8.x | Unit tests for registry, router, dispatcher | Required by nyquist_validation = true |
| `pytest-mock` or `unittest.mock` | stdlib | Mock `ChatAnthropic.invoke()` in tests | Avoids real API calls in unit tests |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `python-frontmatter` | Manual YAML parse | Spec explicitly requires `frontmatter.load()` — do not diverge |
| `langchain-anthropic` | `ChatCopilot` from main app | Spec requires ChatAnthropic — this is intentional (demo uses real Anthropic API) |

**Installation (inside `super-agent-sample/`):**
```bash
cd super-agent-sample
uv sync
```

**Version verification (confirmed 2026-04-03):**
```
langchain-anthropic: 1.4.0 (latest on PyPI)
python-frontmatter: 1.1.0 (latest on PyPI)
langgraph: 1.1.4 (already in main project pyproject.toml)
pyyaml: 6.0.3 (already installed)
```

---

## Architecture Patterns

### Recommended Project Structure
```
super-agent-sample/
  agents/
    code-reviewer/
      AGENT.md         # frontmatter: name, description, model + system prompt body
      rules.md         # (optional detail, not loaded in phase 1)
    sql-analyst/
      AGENT.md
  menus/
    super-chat.yaml    # graph: orchestrator
    simple-chat.yaml   # graph: simple
  src/
    state.py           # AgentState TypedDict
    agent.py           # SubAgent, SubAgentRegistry
    graph.py           # RouterNode, build_orchestrator_graph, build_simple_graph
    dispatcher.py      # MenuRegistry, MenuDispatcher
    main.py            # Entry point with 4 demo cases
  tests/
    test_registry.py   # SubAgentRegistry unit tests
    test_router.py     # RouterNode unit tests (mocked LLM)
    test_dispatcher.py # MenuDispatcher unit tests (mocked graph)
    conftest.py        # shared fixtures
  pyproject.toml       # standalone, own virtualenv
```

### Pattern 1: Spec-Exact Implementation
**What:** All classes, methods, and signatures must match `docs/pre/phase1_spec.md` exactly.
**When to use:** This phase is a demonstration of the spec — no creative deviation.
**Example (from spec, section 5):**
```python
# src/agent.py
import frontmatter  # installed as python-frontmatter
from langchain_anthropic import ChatAnthropic

class SubAgent:
    @classmethod
    def from_dir(cls, agent_dir: Path) -> "SubAgent":
        post = frontmatter.load(agent_dir / "AGENT.md")
        meta = post.metadata
        return cls(
            name=meta["name"],
            description=meta["description"],
            model=meta.get("model", "claude-sonnet-4-6"),
            system_prompt=post.content,
        )
```

### Pattern 2: Conditional Routing in LangGraph
**What:** `add_conditional_edges` with a lambda reading `state["next"]` to route to named agent nodes.
**When to use:** OrchestratorGraph routes from "router" node to agent nodes dynamically.
**Example (from spec, section 6):**
```python
routing_map = {a.name: a.name for a in registry.all()}
routing_map["fallback"] = "fallback"
graph.add_conditional_edges("router", lambda s: s["next"], routing_map)
```

### Pattern 3: Flat-Module Import with PYTHONPATH
**What:** `src/` is a flat directory of modules (not a Python package). Modules import each other with bare names (`from state import AgentState`).
**When to use:** Required by spec; standard for small standalone scripts.
**Run command (corrected from spec):**
```bash
ANTHROPIC_API_KEY=sk-... PYTHONPATH=src uv run python src/main.py
```
The spec writes `uv run python src/main.py` without `PYTHONPATH=src` — this will fail with `ModuleNotFoundError`. Add `PYTHONPATH=src`.

**pytest config to match:**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

### Pattern 4: AGENT.md Frontmatter Format
**What:** YAML frontmatter between `---` delimiters, body is system prompt text.
**When to use:** Every agent definition file.
**Example (from spec, section 3):**
```yaml
---
name: code-reviewer
description: |
  Python/JavaScript/TypeScript コードの静的解析・リント・フォーマットチェックを行う。
  入力: コードスニペットまたはファイルパス
  出力: 指摘リストと修正提案
  対象外: テスト実行 / デプロイ / DB操作
model: claude-opus-4-6
---

あなたは厳格なコードレビュアーです。
指摘は重大度（error/warning/info）付きで箇条書きにしてください。
```

### Anti-Patterns to Avoid
- **Modifying `app/`:** Phase 8 is a standalone sample. Never touch the main FastAPI app.
- **Using ChatCopilot:** The spec explicitly uses `ChatAnthropic`. Do not substitute.
- **Running without `PYTHONPATH=src`:** The bare imports will fail from the project root.
- **Omitting `fallback` from routing_map:** Router may return agent names not in the graph; `"fallback"` key must be present.
- **Sync invoke in async context:** The sample uses synchronous `graph.invoke()` (not `ainvoke`) — this is intentional for a CLI demo. Do not add async unnecessarily.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML frontmatter parsing | Custom string splitting on `---` | `python-frontmatter` | Handles edge cases: multiline values, escaped chars, missing frontmatter |
| YAML menu files | Custom ini or JSON parser | `yaml.safe_load()` | Already available (pyyaml), safe against YAML bomb attacks |
| Conditional graph routing | Custom if/else dispatch | `graph.add_conditional_edges()` | LangGraph native pattern; handles state transitions correctly |
| Agent discovery | Hardcoded agent list | `SubAgentRegistry` glob scan | `Path(agent_dir).glob("**/AGENT.md")` picks up new agents automatically |

**Key insight:** The spec already makes the right tool choices. Follow them exactly — the sample's value is in demonstrating the pattern, not building custom infrastructure.

---

## Runtime State Inventory

> Phase 8 is greenfield — a new standalone sample directory. No rename/refactor/migration involved.

**Not applicable.** This phase creates new files only. No existing data, services, or OS state is modified.

---

## Common Pitfalls

### Pitfall 1: Missing PYTHONPATH for flat imports
**What goes wrong:** `ModuleNotFoundError: No module named 'state'` when running `uv run python src/main.py`.
**Why it happens:** `src/` is not in Python's module search path by default when invoked from the project root.
**How to avoid:** Always run as `PYTHONPATH=src uv run python src/main.py`. Add `pythonpath = ["src"]` to `[tool.pytest.ini_options]` for tests.
**Warning signs:** First run fails immediately with `ModuleNotFoundError`.

### Pitfall 2: ANTHROPIC_API_KEY not set for smoke test
**What goes wrong:** `AuthenticationError` or `KeyError` when `ChatAnthropic` tries to initialize.
**Why it happens:** `langchain-anthropic` reads `ANTHROPIC_API_KEY` from environment at instantiation time.
**How to avoid:** Export `ANTHROPIC_API_KEY` before running. Confirmed the key IS set in this environment (verified 2026-04-03).
**Warning signs:** Error on first `SubAgent` or `RouterNode` instantiation.

### Pitfall 3: Model name typos
**What goes wrong:** `404` or `InvalidRequestError` from Anthropic API.
**Why it happens:** Incorrect model ID strings.
**How to avoid:** Use exact model IDs confirmed from official Anthropic docs (verified 2026-04-03):
- `claude-opus-4-6` (AGENT.md default for code-reviewer)
- `claude-sonnet-4-6` (simple_graph and SubAgent fallback default)
- `claude-haiku-4-5-20251001` (RouterNode — lightweight model, confirmed valid API ID)
**Warning signs:** API error mentioning model not found.

### Pitfall 4: `frontmatter` import vs `python-frontmatter` package
**What goes wrong:** `ModuleNotFoundError: No module named 'frontmatter'` after `uv add frontmatter`.
**Why it happens:** The PyPI package is named `python-frontmatter` but imported as `frontmatter`. `uv add frontmatter` installs a different package.
**How to avoid:** In `pyproject.toml` dependencies, use `"python-frontmatter"`. Import as `import frontmatter`.
**Warning signs:** ModuleNotFoundError after install, or wrong package installed.

### Pitfall 5: fallback routing when LLM returns unexpected text
**What goes wrong:** Router returns an agent name with trailing whitespace or extra text; lookup fails silently.
**Why it happens:** LLM output is not guaranteed to be a bare word.
**How to avoid:** The spec already handles this: `chosen = response.content.strip()` + validation against `valid` set with fallback. Implement exactly as specified.
**Warning signs:** `[router] unknown '...' → fallback` in logs for inputs that should route to a real agent.

### Pitfall 6: Running `uv sync` in wrong directory
**What goes wrong:** `uv sync` installs deps into the main project's venv, not the sample's.
**Why it happens:** `uv` uses the nearest `pyproject.toml` going up the directory tree.
**How to avoid:** Always `cd super-agent-sample && uv sync` — run from within the sample directory.
**Warning signs:** `langchain-anthropic` or `python-frontmatter` appears in the main project's lockfile.

---

## Code Examples

### AgentState (verbatim from spec)
```python
# src/state.py
# Source: docs/pre/phase1_spec.md section 4
from __future__ import annotations
import operator
from typing import Annotated
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    input: str
    output: str
    messages: Annotated[list[BaseMessage], operator.add]
    next: str
```

### pyproject.toml for the sample
```toml
# super-agent-sample/pyproject.toml
# Source: docs/pre/phase1_spec.md section 10 + pitfall fixes
[project]
name = "super-agent-sample"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
    "langchain-anthropic>=1.4.0",
    "langgraph>=1.1.4",
    "langchain-core>=0.3.0",
    "python-frontmatter>=1.1.0",
    "pyyaml>=6.0.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-mock>=3.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

### Unit test pattern (mocked ChatAnthropic)
```python
# tests/test_router.py
from unittest.mock import MagicMock, patch
from state import AgentState
from graph import RouterNode
from agent import SubAgentRegistry

def make_mock_registry(names: list[str]):
    registry = MagicMock()
    agents = [MagicMock(name=n, description=f"desc for {n}") for n in names]
    registry.all.return_value = agents
    return registry

def test_router_selects_code_reviewer(tmp_path):
    # Create minimal AGENT.md files
    # ... (fixture creates agents/ dir)
    with patch("graph.ChatAnthropic") as MockLLM:
        instance = MockLLM.return_value
        instance.invoke.return_value = MagicMock(content="code-reviewer")
        registry = make_mock_registry(["code-reviewer", "sql-analyst"])
        router = RouterNode(registry)
        state: AgentState = {"input": "review my code", "output": "", "messages": [], "next": ""}
        result = router(state)
        assert result["next"] == "code-reviewer"
```

### Correct run command
```bash
# From super-agent-sample/ directory
ANTHROPIC_API_KEY=sk-ant-... PYTHONPATH=src uv run python src/main.py
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| LangGraph `set_entry_point()` | `set_entry_point()` still valid in 1.1.x | — | No change needed |
| `typing.TypedDict` for state | `typing_extensions.TypedDict` for older Python | — | Spec uses `typing_extensions` — keep as-is |
| `langchain` (full) for messages | `langchain-core` only | 2024+ | Spec imports from `langchain_core.messages` — correct |

**Deprecated/outdated:**
- `claude-3-haiku-20240307`: Deprecated, retiring April 19, 2026. Do NOT use. Spec correctly uses `claude-haiku-4-5-20251001`.
- `MemorySaver` without checkpointer: Not relevant — sample uses `graph.compile()` without checkpointer (stateless, CLI demo).

---

## Open Questions

1. **Sample directory name**
   - What we know: Spec calls it `project/` generically.
   - What's unclear: Whether to use `super-agent-sample/`, `sample/`, or another name.
   - Recommendation: Use `super-agent-sample/` — matches the phase description and is self-documenting.

2. **sql-analyst AGENT.md content**
   - What we know: Spec only shows `code-reviewer/AGENT.md` in full (section 3). `sql-analyst/AGENT.md` is listed in the directory structure but content is not provided.
   - What's unclear: Exact `description` and system prompt for sql-analyst.
   - Recommendation: Write a reasonable sql-analyst AGENT.md following the same frontmatter format. The router must be able to route SQL-related queries to it based on description — make description specific: "SQLクエリのパフォーマンス分析・最適化を行う。".

3. **`rules.md` content for code-reviewer**
   - What we know: Listed in directory structure but not loaded in Phase 1.
   - What's unclear: Whether to create an empty file or skip.
   - Recommendation: Create a minimal placeholder `rules.md` with a comment that it's reserved for Phase 2+.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | Runtime | Yes | 3.12.3 | — |
| uv | Package management | Yes | 0.8.4 | pip |
| ANTHROPIC_API_KEY | ChatAnthropic live calls | Yes | (set, verified) | — |
| `langchain-anthropic` | SubAgent, RouterNode, SimpleGraph | Not in main venv (install needed) | 1.4.0 on PyPI | — |
| `python-frontmatter` | SubAgentRegistry.from_dir() | Not in main venv (install needed) | 1.1.0 on PyPI | — |
| `pyyaml` | MenuRegistry YAML parsing | Yes (6.0.3 in uv env) | 6.0.3 | — |
| `langgraph` | StateGraph compilation | In main project, install in sample | 1.1.4 | — |
| git branch | Separate branch requirement | Yes (git available) | — | — |

**Missing dependencies with no fallback:**
- `langchain-anthropic` and `python-frontmatter` must be installed in the sample's own venv via `uv sync` in `super-agent-sample/`.

**Missing dependencies with fallback:**
- None blocking. All required tools are available.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | `super-agent-sample/pyproject.toml` — `[tool.pytest.ini_options]` |
| Quick run command | `cd super-agent-sample && PYTHONPATH=src uv run pytest tests/ -x` |
| Full suite command | `cd super-agent-sample && PYTHONPATH=src uv run pytest tests/ -v` |

Note: `pythonpath = ["src"]` in pytest config means `PYTHONPATH=src` is handled by pytest automatically. The pytest run command does NOT need explicit `PYTHONPATH=src` prefix — pytest reads it from pyproject.toml. The `main.py` smoke run still needs it.

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SAMPLE-02 | AgentState fields present | unit | `pytest tests/test_state.py -x` | Wave 0 |
| SAMPLE-03 | SubAgentRegistry loads AGENT.md files | unit | `pytest tests/test_registry.py -x` | Wave 0 |
| SAMPLE-04 | RouterNode selects correct agent name | unit (mocked LLM) | `pytest tests/test_router.py -x` | Wave 0 |
| SAMPLE-05 | MenuDispatcher.dispatch() routes to correct graph | unit (mocked graph) | `pytest tests/test_dispatcher.py -x` | Wave 0 |
| SAMPLE-06 | AGENT.md frontmatter parses correctly | unit (file fixture) | `pytest tests/test_registry.py -x` | Wave 0 |
| SAMPLE-09 | Smoke test: all 4 cases produce output | smoke (live API, manual) | `PYTHONPATH=src uv run python src/main.py` | manual-only |

Note: SAMPLE-09 is manual-only because it requires a live Anthropic API call and produces non-deterministic output. The verification check is log line presence: `[router] '...' → code-reviewer`, `[router] '...' → sql-analyst`, `[router] '...' → fallback`.

### Sampling Rate
- **Per task commit:** `cd super-agent-sample && uv run pytest tests/ -x`
- **Per wave merge:** `cd super-agent-sample && uv run pytest tests/ -v`
- **Phase gate:** Unit tests green + manual smoke run verified before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `super-agent-sample/tests/conftest.py` — shared fixtures (tmp AGENT.md files)
- [ ] `super-agent-sample/tests/test_state.py` — covers SAMPLE-02
- [ ] `super-agent-sample/tests/test_registry.py` — covers SAMPLE-03, SAMPLE-06
- [ ] `super-agent-sample/tests/test_router.py` — covers SAMPLE-04
- [ ] `super-agent-sample/tests/test_dispatcher.py` — covers SAMPLE-05
- [ ] Framework install: `cd super-agent-sample && uv sync` — installs pytest from dev group

---

## Sources

### Primary (HIGH confidence)
- Official Anthropic model docs (fetched 2026-04-03): https://platform.claude.com/docs/en/about-claude/models/overview — confirmed model IDs: `claude-opus-4-6`, `claude-sonnet-4-6`, `claude-haiku-4-5-20251001`
- `docs/pre/phase1_spec.md` — primary implementation spec (read directly)
- PyPI: `python-frontmatter` 1.1.0 (latest), `langchain-anthropic` 1.4.0 (latest) — confirmed via `pip index versions`
- `.planning/config.json` — confirmed `nyquist_validation: true`

### Secondary (MEDIUM confidence)
- LangGraph 1.1.4 StateGraph API: verified against existing `app/graph/builder.py` which uses the same `StateGraph` + `add_edge` + `compile()` pattern
- uv 0.8.4 behavior: verified via `uv run --help` and existing project usage

### Tertiary (LOW confidence)
- `pytest pythonpath` config in `[tool.pytest.ini_options]`: standard pytest 7+ feature, confirmed pattern in pytest docs (not directly fetched)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all package versions verified against PyPI, model IDs verified against official Anthropic docs
- Architecture: HIGH — spec is prescriptive and complete; no design decisions needed
- Pitfalls: HIGH — `PYTHONPATH` issue verified by analysis of Python import resolution; `frontmatter` import name is a known packaging convention

**Research date:** 2026-04-03
**Valid until:** 2026-05-03 (model IDs and package versions are stable over 30-day horizon)
