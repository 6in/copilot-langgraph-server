---
phase: quick
plan: 260403-wlh
type: execute
wave: 1
depends_on: []
files_modified:
  - super-agent-sample/src/copilot.py
  - super-agent-sample/src/agent.py
  - super-agent-sample/src/graph.py
  - super-agent-sample/src/dispatcher.py
  - super-agent-sample/src/main.py
  - super-agent-sample/pyproject.toml
  - super-agent-sample/tests/test_registry.py
  - super-agent-sample/tests/test_router.py
  - super-agent-sample/tests/test_dispatcher.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "super-agent-sample uses ChatCopilot instead of ChatAnthropic"
    - "No import of langchain_anthropic remains in any source file"
    - "All existing tests pass with ChatCopilot mocked instead of ChatAnthropic"
    - "main.py runs via asyncio.run() since ChatCopilot is async-only"
  artifacts:
    - path: "super-agent-sample/src/copilot.py"
      provides: "Standalone copy of ChatCopilot provider"
    - path: "super-agent-sample/pyproject.toml"
      provides: "Dependencies with github-copilot-sdk instead of langchain-anthropic"
  key_links:
    - from: "super-agent-sample/src/agent.py"
      to: "super-agent-sample/src/copilot.py"
      via: "from copilot import ChatCopilot"
      pattern: "from copilot import ChatCopilot"
    - from: "super-agent-sample/src/graph.py"
      to: "super-agent-sample/src/copilot.py"
      via: "from copilot import ChatCopilot"
      pattern: "from copilot import ChatCopilot"
---

<objective>
Replace ChatAnthropic with ChatCopilot in super-agent-sample so it uses GitHub Copilot SDK instead of requiring an Anthropic API key.

Purpose: Make super-agent-sample consistent with the main app's AI provider (Copilot SDK via ChatCopilot), eliminating the ANTHROPIC_API_KEY dependency.
Output: All super-agent-sample source files use ChatCopilot; all tests pass.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@app/providers/copilot.py

<interfaces>
<!-- ChatCopilot is async-only. _generate() raises NotImplementedError. Must use ainvoke(). -->

From app/providers/copilot.py:
```python
class ChatCopilot(BaseChatModel):
    model: str = "claude-sonnet-4.5"
    github_token: Optional[str] = None
    auth_manager: Optional[Any] = None

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult: ...
    async def close(self) -> None: ...

    # _generate() raises NotImplementedError — sync invoke() will fail
    # MUST use ainvoke() or _agenerate() in async context
```

Key constraint: ChatCopilot requires `github_token` or `auth_manager`. For super-agent-sample standalone use, pass `github_token` from environment variable (e.g. `GITHUB_TOKEN`).

The `model` parameter is accepted by ChatCopilot and forwarded to `create_session(model=self.model)`, so AGENT.md model fields still have meaning (Copilot SDK chooses a model based on it).
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Copy ChatCopilot provider and update dependencies</name>
  <files>super-agent-sample/src/copilot.py, super-agent-sample/pyproject.toml</files>
  <action>
1. Copy `app/providers/copilot.py` to `super-agent-sample/src/copilot.py` as a standalone copy (Option B for self-containment).
   - Keep the file identical except: remove the module docstring reference to `app.providers.copilot` import path. Update the docstring Usage example to show `from copilot import ChatCopilot`.
   - Keep all imports, class definition, methods unchanged.

2. Update `super-agent-sample/pyproject.toml`:
   - Remove `"langchain-anthropic>=1.4.0"` from dependencies.
   - Add `"github-copilot-sdk==0.2.0"` (pinned exact, Technical Preview).
   - Add `"pydantic>=2.0"` (ChatCopilot uses ConfigDict, PrivateAttr).
   - Add `"cryptography>=41.0"` (needed by copilot SDK auth manager, though optional here).
   - Keep all other deps unchanged.
  </action>
  <verify>
    <automated>cd /home/parallels/workspaces/copilot-langgraph/super-agent-sample && python -c "import ast; ast.parse(open('src/copilot.py').read()); print('copilot.py syntax OK')" && grep -q 'github-copilot-sdk' pyproject.toml && ! grep -q 'langchain-anthropic' pyproject.toml && echo "PASS"</automated>
  </verify>
  <done>copilot.py exists in super-agent-sample/src/ with valid syntax; pyproject.toml has github-copilot-sdk and no langchain-anthropic</done>
</task>

<task type="auto">
  <name>Task 2: Convert sync to async and replace ChatAnthropic with ChatCopilot</name>
  <files>super-agent-sample/src/agent.py, super-agent-sample/src/graph.py, super-agent-sample/src/dispatcher.py, super-agent-sample/src/main.py, super-agent-sample/tests/test_registry.py, super-agent-sample/tests/test_router.py, super-agent-sample/tests/test_dispatcher.py</files>
  <action>
ChatCopilot is async-only (_generate raises NotImplementedError), so the entire call chain must become async.

**agent.py:**
- Replace `from langchain_anthropic import ChatAnthropic` with `from copilot import ChatCopilot`
- In `SubAgent.__init__`: replace `self._llm = ChatAnthropic(model=model)` with `self._llm = ChatCopilot(model=model, github_token=os.environ.get("GITHUB_TOKEN", ""))`.
  Add `import os` at top.
- Rename `SubAgent.run()` to `async def run()` — change `self._llm.invoke(messages)` to `await self._llm.ainvoke(messages)`.

**graph.py:**
- Replace `from langchain_anthropic import ChatAnthropic` with `from copilot import ChatCopilot` and `import os`.
- In `RouterNode.__init__`: replace `ChatAnthropic(model="claude-haiku-4-5-20251001")` with `ChatCopilot(model="claude-haiku-4-5-20251001", github_token=os.environ.get("GITHUB_TOKEN", ""))`.
- Rename `RouterNode.__call__` to `async def __call__` — change `self._llm.invoke(messages)` to `await self._llm.ainvoke(messages)`.
- In `build_simple_graph()`: rename `simple_node` to `async def simple_node` — replace `ChatAnthropic(model="claude-sonnet-4-6")` with `ChatCopilot(model="claude-sonnet-4-6", github_token=os.environ.get("GITHUB_TOKEN", ""))`, change `.invoke()` to `await llm.ainvoke()`.

**dispatcher.py:**
- Rename `MenuDispatcher.dispatch()` to `async def dispatch()` — change `graph.invoke(initial)` to `await graph.ainvoke(initial)`.

**main.py:**
- Add `import asyncio`.
- Rename `def main()` to `async def main()` — change all `dispatcher.dispatch()` calls to `await dispatcher.dispatch()`.
- Change `main()` call at bottom to `asyncio.run(main())`.

**tests/test_registry.py:**
- Replace all `patch("agent.ChatAnthropic")` with `patch("agent.ChatCopilot")`.
- In `test_subagent_from_dir_default_model`: update assertion to `MockLLM.assert_called_once_with(model="claude-sonnet-4-6", github_token=...)` — use `unittest.mock.ANY` for github_token since it reads env var.

**tests/test_router.py:**
- Replace all `patch("graph.ChatAnthropic")` with `patch("graph.ChatCopilot")`.
- Since RouterNode.__call__ is now async, convert test functions to async:
  - Add `import pytest` and `@pytest.mark.asyncio` decorator to each test.
  - Change `result = router(state)` to `result = await router(state)`.
  - Add `pytest-asyncio>=0.23` to dev dependencies in pyproject.toml.

**tests/test_dispatcher.py:**
- Read existing file first. If it uses `graph.invoke()`, update to use `graph.ainvoke()` and make tests async with `@pytest.mark.asyncio`.

Ensure NO `langchain_anthropic` import remains anywhere in `super-agent-sample/src/` or `super-agent-sample/tests/`.
  </action>
  <verify>
    <automated>cd /home/parallels/workspaces/copilot-langgraph/super-agent-sample && python -m pytest tests/ -x -v 2>&1 | tail -30</automated>
  </verify>
  <done>All tests pass; grep -r "langchain_anthropic" super-agent-sample/ returns no results; all source files use ChatCopilot via async ainvoke()</done>
</task>

</tasks>

<verification>
1. `grep -r "langchain_anthropic" super-agent-sample/` returns empty (no Anthropic references remain)
2. `grep -r "ChatAnthropic" super-agent-sample/` returns empty
3. `grep -r "from copilot import ChatCopilot" super-agent-sample/src/` shows agent.py and graph.py
4. `cd super-agent-sample && python -m pytest tests/ -x -v` — all tests pass
5. `python -c "from copilot import ChatCopilot; print('import OK')"` from super-agent-sample/src/ works
</verification>

<success_criteria>
- ChatAnthropic fully replaced by ChatCopilot across all super-agent-sample source files
- Entire call chain is async (main -> dispatcher -> graph nodes -> ChatCopilot.ainvoke)
- All existing tests updated and passing with ChatCopilot mocked
- pyproject.toml dependencies updated (no langchain-anthropic, has github-copilot-sdk)
- copilot.py exists as standalone copy in super-agent-sample/src/
</success_criteria>

<output>
After completion, create `.planning/quick/260403-wlh-super-agent-sample-chatanthropic-chatcop/260403-wlh-SUMMARY.md`
</output>
