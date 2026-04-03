---
phase: quick
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - super-agent-sample/src/auth_manager.py
  - super-agent-sample/src/agent.py
  - super-agent-sample/src/graph.py
autonomous: true
must_haves:
  truths:
    - "ChatCopilot instances receive a CopilotAuthManager and can obtain a token via get_token()"
    - "No ChatCopilot instantiation uses bare github_token from env var"
  artifacts:
    - path: "super-agent-sample/src/auth_manager.py"
      provides: "CopilotAuthManager standalone copy"
      contains: "class CopilotAuthManager"
    - path: "super-agent-sample/src/agent.py"
      provides: "SubAgent using auth_manager"
      contains: "auth_manager="
    - path: "super-agent-sample/src/graph.py"
      provides: "RouterNode and simple_node using auth_manager"
      contains: "auth_manager="
  key_links:
    - from: "super-agent-sample/src/agent.py"
      to: "super-agent-sample/src/auth_manager.py"
      via: "import CopilotAuthManager"
      pattern: "from auth_manager import CopilotAuthManager"
    - from: "super-agent-sample/src/graph.py"
      to: "super-agent-sample/src/auth_manager.py"
      via: "import CopilotAuthManager"
      pattern: "from auth_manager import CopilotAuthManager"
---

<objective>
Integrate CopilotAuthManager into super-agent-sample so ChatCopilot can authenticate via encrypted token persistence and Device Flow, instead of requiring a GITHUB_TOKEN env var (which causes ValueError when unset).

Purpose: Fix the ValueError in ChatCopilot._ensure_client() when neither github_token nor auth_manager is provided.
Output: All ChatCopilot instantiations use auth_manager=CopilotAuthManager().
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@super-agent-sample/src/copilot.py
@super-agent-sample/src/agent.py
@super-agent-sample/src/graph.py
@app/auth/manager.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Copy CopilotAuthManager as standalone module</name>
  <files>super-agent-sample/src/auth_manager.py</files>
  <action>
Copy `app/auth/manager.py` to `super-agent-sample/src/auth_manager.py` verbatim. This is a standalone copy to preserve super-agent-sample's independence from the main app package. No modifications needed -- the module has no imports from `app/` and only depends on `httpx` and `cryptography`, both already in super-agent-sample's pyproject.toml (cryptography >= 41.0).

Note: `httpx` is NOT in super-agent-sample/pyproject.toml yet. Add it as a dependency: `"httpx>=0.27"`. CopilotAuthManager uses httpx for Device Flow HTTP calls.
  </action>
  <verify>
    <automated>cd /home/parallels/workspaces/copilot-langgraph/super-agent-sample && python -c "import sys; sys.path.insert(0, 'src'); from auth_manager import CopilotAuthManager; print('OK')"</automated>
  </verify>
  <done>auth_manager.py exists in src/, imports successfully, httpx added to pyproject.toml</done>
</task>

<task type="auto">
  <name>Task 2: Replace github_token with auth_manager in all ChatCopilot instantiations</name>
  <files>super-agent-sample/src/agent.py, super-agent-sample/src/graph.py</files>
  <action>
There are 3 places that instantiate ChatCopilot with `github_token=os.environ.get("GITHUB_TOKEN", "")`. Replace all with `auth_manager=CopilotAuthManager()`.

**agent.py line 15** (SubAgent.__init__):
- Add import: `from auth_manager import CopilotAuthManager`
- Remove: `import os` (no longer needed after this change -- verify no other usage first)
- Change: `ChatCopilot(model=model, github_token=os.environ.get("GITHUB_TOKEN", ""))` to `ChatCopilot(model=model, auth_manager=CopilotAuthManager())`

**graph.py line 30** (RouterNode.__init__):
- Add import: `from auth_manager import CopilotAuthManager`
- Remove: `import os` (no longer needed -- verify no other usage first)
- Change: `ChatCopilot(model="claude-haiku-4-5-20251001", github_token=os.environ.get("GITHUB_TOKEN", ""))` to `ChatCopilot(model="claude-haiku-4-5-20251001", auth_manager=CopilotAuthManager())`

**graph.py line 86** (simple_node inside build_simple_graph):
- Change: `ChatCopilot(model="claude-sonnet-4-6", github_token=os.environ.get("GITHUB_TOKEN", ""))` to `ChatCopilot(model="claude-sonnet-4-6", auth_manager=CopilotAuthManager())`

IMPORTANT: Each CopilotAuthManager() creates its own instance but they all read from the same `~/.copilot_sdk/token.enc` file, so this is fine. No shared state concerns.
  </action>
  <verify>
    <automated>cd /home/parallels/workspaces/copilot-langgraph/super-agent-sample && grep -rn "github_token" src/agent.py src/graph.py; echo "Exit: $?" && grep -rn "auth_manager=CopilotAuthManager" src/agent.py src/graph.py | wc -l</automated>
  </verify>
  <done>Zero occurrences of github_token in agent.py and graph.py. Three occurrences of auth_manager=CopilotAuthManager() (1 in agent.py, 2 in graph.py).</done>
</task>

</tasks>

<verification>
1. `grep -rn "github_token" super-agent-sample/src/` should only show copilot.py (the parameter definition), not any instantiation sites
2. `grep -rn "auth_manager=CopilotAuthManager" super-agent-sample/src/` should show 3 matches
3. `cd super-agent-sample && python -c "import sys; sys.path.insert(0, 'src'); from agent import SubAgent; from graph import build_simple_graph; print('imports OK')"` succeeds
</verification>

<success_criteria>
- All ChatCopilot instantiations in super-agent-sample use auth_manager=CopilotAuthManager()
- No ChatCopilot instantiation relies on GITHUB_TOKEN env var
- auth_manager.py is a standalone copy with no app/ imports
- httpx is listed in pyproject.toml dependencies
</success_criteria>

<output>
After completion, create `.planning/quick/260403-auth-super-agent-sample/260403-auth-SUMMARY.md`
</output>
