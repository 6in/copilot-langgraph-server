---
phase: 08-orchestratorgraph-subagent-docs-pre-phase1-spec-md
verified: 2026-04-03T16:00:00Z
status: gaps_found
score: 7/10 must-haves verified
re_verification: false
gaps:
  - truth: "uv sync succeeds in super-agent-sample/ without errors"
    status: partial
    reason: "pyproject.toml uses github-copilot-sdk==0.2.0 instead of langchain-anthropic>=1.4.0 as planned; this is an intentional post-plan adaptation (Copilot SDK replaces Anthropic), but the plan artifact check for 'langchain-anthropic' in pyproject.toml fails"
    artifacts:
      - path: "super-agent-sample/pyproject.toml"
        issue: "Contains github-copilot-sdk==0.2.0 instead of langchain-anthropic>=1.4.0 — post-plan adaptation, functionally equivalent for goal, but diverges from plan spec"
    missing:
      - "No action required — this is a purposeful architectural deviation (Copilot SDK chosen over Anthropic). Document the deviation explicitly."

  - truth: "All unit tests pass with mocked LLM (no live API calls)"
    status: failed
    reason: "1 of 14 tests fails: test_subagent_from_dir_default_model in tests/test_registry.py asserts ChatCopilot is called with github_token=ANY but production code passes auth_manager=CopilotAuthManager() instead"
    artifacts:
      - path: "super-agent-sample/tests/test_registry.py"
        issue: "Line 35: MockLLM.assert_called_once_with(model='claude-sonnet-4-6', github_token=ANY) — wrong kwarg; actual call uses auth_manager= not github_token="
      - path: "super-agent-sample/src/agent.py"
        issue: "SubAgent.__init__ passes auth_manager=CopilotAuthManager() to ChatCopilot; test expects github_token=ANY"
    missing:
      - "Fix test_subagent_from_dir_default_model to assert MockLLM.assert_called_once_with(model='claude-sonnet-4-6', auth_manager=ANY) to match actual production code"

  - truth: "Feature branch feat/super-agent-sample is checked out for separate-branch work"
    status: failed
    reason: "Work was completed on feat/super-agent-sample and subsequently merged to main. Current branch is main. The post-plan commits (ChatCopilot migration) landed directly on main. This is expected merge workflow but the branch no longer exists as a separate branch."
    artifacts: []
    missing:
      - "No fix needed if merge was intentional — confirm merge was completed per project workflow"
---

# Phase 8: Super Agent Sample Verification Report

**Phase Goal:** スーパーエージェントサンプル実装 — OrchestratorGraph + SubAgent + メニュー追加（docs/pre/phase1_spec.md 仕様準拠、別ブランチ作業）

**Verified:** 2026-04-03T16:00:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

---

## Goal Achievement

The phase goal is substantially achieved. A standalone `super-agent-sample/` project exists with OrchestratorGraph + SubAgent + MenuDispatcher architecture. The post-plan adaptation replaced ChatAnthropic with ChatCopilot (GitHub Copilot SDK), which is architecturally sound but left one test expectation stale. 13 of 14 tests pass.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | super-agent-sample/ directory exists as standalone project at repo root | VERIFIED | `ls super-agent-sample/` — pyproject.toml, src/, agents/, menus/, tests/ all present |
| 2 | uv sync succeeds in super-agent-sample/ without errors | VERIFIED | uv.lock present, pytest ran successfully (imports resolved) |
| 3 | AgentState TypedDict has input, output, messages, next fields | VERIFIED | src/state.py lines 9-13 — exact 4-field TypedDict matching spec section 4 |
| 4 | code-reviewer and sql-analyst AGENT.md parse with python-frontmatter | VERIFIED | Both files have valid YAML frontmatter with name/description/model fields + system prompt body |
| 5 | Both menu YAML files parse with yaml.safe_load | VERIFIED | super-chat.yaml (graph: orchestrator) and simple-chat.yaml (graph: simple) both exist and parse correctly |
| 6 | SubAgent.from_dir() loads AGENT.md frontmatter and creates SubAgent instance | VERIFIED | agent.py SubAgent.from_dir() uses python-frontmatter, loads name/description/model/system_prompt |
| 7 | SubAgentRegistry scans agents/ directory and discovers all AGENT.md files | VERIFIED | SubAgentRegistry.__init__ uses Path.glob("**/AGENT.md"), test_registry_discovers_agents passes |
| 8 | RouterNode routes to correct agent name based on LLM response | VERIFIED | RouterNode.__call__ is async, uses ChatCopilot.ainvoke, strips whitespace, validates against known names |
| 9 | RouterNode falls back to 'fallback' for unknown agent names | VERIFIED | Lines 45-49 in graph.py — "fallback" hardcoded in valid set, unknown names redirected |
| 10 | OrchestratorGraph compiles with router, agent nodes, and fallback | VERIFIED | build_orchestrator_graph() creates StateGraph with router, fallback, conditional edges, compiles |
| 11 | MenuDispatcher dispatches to correct graph based on menu mode | VERIFIED | MenuDispatcher.dispatch() is async, calls graph.ainvoke(), routes by menu name |
| 12 | All unit tests pass with mocked LLM (no live API calls) | FAILED | 13/14 pass; test_subagent_from_dir_default_model fails — expects github_token=ANY, actual uses auth_manager= |
| 13 | main.py runs all 4 test cases without crashing | VERIFIED | main.py exists verbatim from spec (async version); smoke test passed per 08-03 SUMMARY human verification |
| 14 | simple-chat mode bypasses router and calls LLM directly | VERIFIED | build_simple_graph() has single-node graph ("llm") with no router |
| 15 | super-chat mode routes to agents via OrchestratorGraph | VERIFIED | build_orchestrator_graph() adds router + conditional edges to agent nodes |
| 16 | Feature branch feat/super-agent-sample for separate-branch work | PARTIAL | Branch created and used (per git log — cf64124 merge commit), then merged to main; current branch is main |

**Score:** 13/16 truths fully verified (1 test failure, 1 branch merged as expected, 1 pyproject deviation noted)

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `super-agent-sample/pyproject.toml` | Project metadata and dependencies | VERIFIED (with deviation) | Present; uses github-copilot-sdk==0.2.0 instead of langchain-anthropic>=1.4.0 — post-plan architectural choice |
| `super-agent-sample/src/state.py` | AgentState TypedDict | VERIFIED | Contains `class AgentState(TypedDict):` with all 4 fields |
| `super-agent-sample/agents/code-reviewer/AGENT.md` | Code reviewer agent definition | VERIFIED | name: code-reviewer, model: claude-opus-4-6, system prompt present |
| `super-agent-sample/agents/sql-analyst/AGENT.md` | SQL analyst agent definition | VERIFIED | name: sql-analyst, model: claude-sonnet-4-6, system prompt present |
| `super-agent-sample/menus/super-chat.yaml` | Orchestrator menu definition | VERIFIED | graph: orchestrator, enabled: true |
| `super-agent-sample/menus/simple-chat.yaml` | Simple chat menu definition | VERIFIED | graph: simple, enabled: true |
| `super-agent-sample/src/agent.py` | SubAgent and SubAgentRegistry | VERIFIED | Both classes present; uses ChatCopilot (not ChatAnthropic) — post-plan adaptation |
| `super-agent-sample/src/graph.py` | RouterNode, build_orchestrator_graph, build_simple_graph | VERIFIED | All 3 exports present; uses `-> Any` (correct); async with ChatCopilot |
| `super-agent-sample/src/dispatcher.py` | MenuRegistry and MenuDispatcher | VERIFIED | Both classes; dispatch() is async using graph.ainvoke() |
| `super-agent-sample/src/main.py` | CLI entry point with 4 demo cases | VERIFIED | def main() is async; 4 cases present; asyncio.run(main()) entry |
| `super-agent-sample/tests/conftest.py` | Shared test fixtures | VERIFIED | tmp_agents_dir and tmp_menus_dir fixtures present |
| `super-agent-sample/tests/test_state.py` | AgentState unit tests | VERIFIED | 2 tests pass |
| `super-agent-sample/tests/test_registry.py` | SubAgentRegistry unit tests | PARTIAL | 4/5 tests pass; test_subagent_from_dir_default_model fails |
| `super-agent-sample/tests/test_router.py` | RouterNode unit tests | VERIFIED | 3 async tests pass with AsyncMock |
| `super-agent-sample/tests/test_dispatcher.py` | MenuDispatcher unit tests | VERIFIED | 4 tests pass (2 async with AsyncMock) |

---

## Key Link Verification

### Plan 02 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/agent.py` | `src/state.py` | `from state import AgentState` | VERIFIED | Line 8 of agent.py |
| `src/graph.py` | `src/agent.py` | `from agent import SubAgentRegistry` | VERIFIED | Line 9 of graph.py |
| `src/dispatcher.py` | `src/state.py` | `from state import AgentState` | VERIFIED | Line 4 of dispatcher.py |

### Plan 03 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/main.py` | `src/agent.py` | `from agent import SubAgentRegistry` | VERIFIED | Line 4 of main.py |
| `src/main.py` | `src/graph.py` | `from graph import build_orchestrator_graph, build_simple_graph` | VERIFIED | Line 5 of main.py |
| `src/main.py` | `src/dispatcher.py` | `from dispatcher import MenuDispatcher, MenuRegistry` | VERIFIED | Line 6 of main.py |

---

## Notable Architectural Deviation (Post-Plan)

After Plan 08-02 and 08-03 were completed, a post-plan migration replaced `ChatAnthropic` with `ChatCopilot` across all modules. This is documented in git log commits `9e7933b` (ChatCopilot migration), `ec6b398` (add auth_manager), `3be4e4c` (replace github_token with auth_manager), and `aef3669` (rename to avoid shadowing SDK).

**Impact on plans:**
- `pyproject.toml`: `langchain-anthropic` removed, `github-copilot-sdk==0.2.0` added. The plan's `contains: "python-frontmatter"` check still passes.
- `agent.py`, `graph.py`, `main.py`: All LLM calls are now async (`ainvoke`) using ChatCopilot; `main()` is now async.
- Tests updated to use `AsyncMock` and `patch("agent.ChatCopilot")` / `patch("graph.ChatCopilot")` — but one test assertion was not updated correctly.

This deviation achieves the phase's broader goal (use Copilot SDK as AI provider, per CLAUDE.md project constraints) and is architecturally correct for this project.

---

## Test Suite Results

```
FAILED tests/test_registry.py::test_subagent_from_dir_default_model
13 passed, 1 failed
```

**Failing test cause:** `test_subagent_from_dir_default_model` (line 35) asserts:
```python
MockLLM.assert_called_once_with(model="claude-sonnet-4-6", github_token=ANY)
```
But `agent.py` line 15 calls:
```python
self._llm = ChatCopilot(model=model, auth_manager=CopilotAuthManager())
```
The test was not updated when `github_token=` was replaced by `auth_manager=` in the post-plan migration.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `tests/test_registry.py` | 35 | `github_token=ANY` assertion mismatch with production code | Warning | 1 test fails; does not block goal achievement but leaves test suite non-green |

No TODO/FIXME/placeholder patterns found in production code. No empty implementations found.

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All modules importable (PYTHONPATH=src) | `PYTHONPATH=src uv run python -c "from agent import SubAgent; from graph import RouterNode; from dispatcher import MenuDispatcher; print('OK')"` | Imports resolve (confirmed by test runner importing successfully) | PASS |
| pytest test suite | `uv run pytest tests/ -v` | 13 passed, 1 failed | PARTIAL |
| AgentState has 4 fields | test_state.py::test_agent_state_has_required_keys | Passes | PASS |
| RouterNode async routing | test_router.py — 3 async tests | All pass | PASS |
| MenuDispatcher routing | test_dispatcher.py — 4 tests | All pass | PASS |
| Live smoke test (human) | `PYTHONPATH=src uv run python src/main.py` | Verified by human per 08-03 SUMMARY: all 4 cases correct | PASS (human) |

---

## Human Verification Required

### 1. Live Smoke Test Re-run (Optional)

**Test:** Run `cd super-agent-sample && PYTHONPATH=src uv run python src/main.py` with Copilot auth available
**Expected:** 4 cases complete: simple-chat (direct LLM), super-chat code-review (`[router] → code-reviewer`), super-chat SQL (`[router] → sql-analyst`), super-chat fallback (`[router] → fallback`, "対応できるエージェントが見つかりませんでした。")
**Why human:** Requires live Copilot OAuth token; cannot verify in headless automation
**Note:** This was already verified by human in 08-03 SUMMARY. Re-run only if regression suspected.

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status |
|-------------|-------------|-------------|--------|
| SAMPLE-01 | 08-01 | Scaffold super-agent-sample/ standalone project | SATISFIED |
| SAMPLE-02 | 08-01 | AgentState TypedDict | SATISFIED |
| SAMPLE-03 | 08-02 | SubAgent and SubAgentRegistry | SATISFIED |
| SAMPLE-04 | 08-02 | RouterNode / OrchestratorGraph | SATISFIED |
| SAMPLE-05 | 08-02 | MenuDispatcher | SATISFIED |
| SAMPLE-06 | 08-01 | AGENT.md files (code-reviewer, sql-analyst) | SATISFIED |
| SAMPLE-07 | 08-01 | Menu YAML files | SATISFIED |
| SAMPLE-08 | 08-03 | main.py entry point | SATISFIED |
| SAMPLE-09 | 08-03 | Smoke test verified | SATISFIED (human-verified) |
| SAMPLE-10 | 08-02 | Unit tests (mocked LLM, no live API calls) | PARTIAL — 13/14 pass |

---

## Gaps Summary

**1 gap requires a fix (blocker for green test suite):**

The post-plan migration from `github_token=` to `auth_manager=` in `SubAgent.__init__` (agent.py line 15) was not reflected in `test_subagent_from_dir_default_model`. The test still asserts the old `github_token=ANY` kwarg. Fix is a single-line change in `tests/test_registry.py` line 35:

```python
# Current (wrong):
MockLLM.assert_called_once_with(model="claude-sonnet-4-6", github_token=ANY)

# Fix:
MockLLM.assert_called_once_with(model="claude-sonnet-4-6", auth_manager=ANY)
```

**2 informational notes (no action required unless disputed):**

- `pyproject.toml` deviation (langchain-anthropic replaced by github-copilot-sdk) is architecturally correct for this project — intentional post-plan adaptation per CLAUDE.md project constraints.
- `feat/super-agent-sample` branch was merged to main — this is expected per project Merge Workflow in CLAUDE.md.

---

_Verified: 2026-04-03T16:00:00Z_
_Verifier: Claude (gsd-verifier)_
