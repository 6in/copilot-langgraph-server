# Phase 12: Hybrid SubAgentRegistry + Tool Quality - Research

**Researched:** 2026-04-04
**Domain:** Python plugin discovery, health status pattern, jsonschema validation, CI lint scripts
**Confidence:** HIGH

## Summary

Phase 12 extends the existing `SubAgentRegistry` (in `app/orchestrator/agent.py`) to support two agent types side-by-side: **folder-type** agents (AGENT.md only, no agent.py — current behavior) and **code-type** agents (agent.py present, takes precedence). It adds HEALTHY/DEGRADED/FAILED health status to every registered entry so that one broken agent cannot crash the application. It also introduces `INPUT_SCHEMA` as a mandatory constant in tool scripts, with `ScriptBackend` validating against it before execution and a CI lint script (`scripts/lint_tools.py`) enforcing the standard.

The implementation is entirely within the existing Python codebase — no new web frameworks, no new language runtimes, and no external services. The primary new dependencies are `jsonschema` (for TOOL-02 validation) and `importlib.util` (stdlib, for loading agent.py modules at runtime). The health endpoint `GET /health/agents` is a new FastAPI route alongside the existing `GET /api/agents`.

**Primary recommendation:** Extend `SubAgentRegistry.__init__` to catch per-agent initialization errors (wrapping each agent load in try/except), record status and error reason per agent, and expose `list_status() -> list[AgentStatus]` for the health route. Code-type agent loading uses `importlib.util.spec_from_file_location` to import agent.py and retrieve a `SubAgent`-compatible class. Add `jsonschema` to `pyproject.toml` and build `ScriptBackend` with pre-call validation using the script module's `INPUT_SCHEMA` constant.

## Project Constraints (from CLAUDE.md)

The project has no CONTEXT.md for this phase, so there are no user locked decisions. The following constraints come from CLAUDE.md and the existing codebase and must be respected by the planner.

### Stack Constraints
- Python 3.12, FastAPI, arq worker pattern, async-first
- `pyproject.toml` (PEP 621) only — no requirements.txt
- `uv` for dependency management; use `uv add` to add new packages
- Docker Compose is the primary startup method — new env vars must be added to docker-compose.yml
- `AGENT_DIR` env var is already wired into `OrchestratorHandler` and `app/api/routes/agents.py`

### Architecture Constraints
- `SubAgentRegistry` lives at `app/orchestrator/agent.py` — extend in place, do not create a parallel registry
- Tests use `pytest` + `pytest-asyncio` with `asyncio_mode = "auto"`, in `tests/` directory
- No `pythonpath` entry in pytest config — the `app/` package is installed via hatchling, imports as `from app.orchestrator...`
- Test infrastructure: mocks via `unittest.mock.AsyncMock`/`MagicMock`; `ASGITransport` pattern for API tests
- All routes are `async def`; new health route follows existing pattern in `app/api/routes/`

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REGISTRY-01 | Folder-type agents (AGENT.md + tools/) auto-loaded on startup with no code change | SubAgentRegistry already does this for AGENT.md-only agents; extension preserves behavior |
| REGISTRY-02 | Code-type agents (AGENT.md + agent.py) take precedence over folder-type | `importlib.util.spec_from_file_location` loads agent.py; presence check before fallback to folder-type |
| REGISTRY-03 | Initialization failure → FAILED; external dependency error → DEGRADED; one failure doesn't stop others | Per-agent try/except with status enum; different error categories distinguished by error type |
| REGISTRY-04 | GET /health/agents returns HEALTHY/DEGRADED/FAILED status + failure reason for all agents | New FastAPI route in `app/api/routes/health.py`; reads from registry stored on `app.state` |
| TOOL-01 | Tool scripts define `INPUT_SCHEMA` constant (JSON Schema dict) for interface clarity | Module-level constant convention; `importlib.util` to introspect at lint time and at call time |
| TOOL-02 | ScriptBackend validates input against INPUT_SCHEMA before calling the tool script | `jsonschema.validate()` pre-call; raises `ValidationError` converted to meaningful error message |
| TOOL-03 | `scripts/lint_tools.py` detects missing INPUT_SCHEMA across all tool scripts; exits non-zero on failure | Python script using `importlib.util` to load each tool file and check for `INPUT_SCHEMA` attribute |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `jsonschema` | 4.26.0 (latest) | Validate tool inputs against INPUT_SCHEMA | Industry-standard JSON Schema validator for Python; `jsonschema.validate()` raises `ValidationError` with detailed message. Not yet in `pyproject.toml` — must be added. |
| `importlib.util` | stdlib | Load agent.py modules at runtime | `spec_from_file_location` + `module_from_spec` is the canonical Python stdlib pattern for loading a module from an arbitrary file path. Zero new dependencies. |
| `pathlib.Path` | stdlib | Discover tool scripts in tools/ subdirectory | Already used throughout codebase for agent discovery. |
| `python-frontmatter` | 1.1.0 (already installed) | Parse AGENT.md frontmatter for both agent types | Already in `pyproject.toml`, already imported in `SubAgent.from_dir`. |
| `enum.Enum` | stdlib | AgentStatus: HEALTHY / DEGRADED / FAILED | Clean, type-safe status representation for health endpoint. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `dataclasses.dataclass` | stdlib | `AgentStatus` response model (or Pydantic) | Pydantic BaseModel preferred to match existing `app/api/models.py` pattern |
| `FastAPI APIRouter` | 0.135.2 (installed) | `GET /health/agents` route | Consistent with all other routes; no new web dependency needed |

### Installation
```bash
uv add jsonschema
```

**Version verification:** jsonschema 4.26.0 confirmed available on PyPI as of 2026-04-04.

---

## Architecture Patterns

### Recommended Project Structure Changes
```
app/
  orchestrator/
    agent.py          — EXTEND: HybridSubAgentRegistry replaces SubAgentRegistry
                        (or rename: SubAgentRegistry gains hybrid loading + health)
  api/
    routes/
      health.py       — NEW: GET /health/agents endpoint
    models.py         — ADD: AgentHealthEntry Pydantic model
  api/
    main.py           — REGISTER: health router in lifespan; store registry on app.state
agents/
  code-reviewer/
    AGENT.md          — unchanged
    agent.py          — NEW code-type example (code-reviewer gets a custom implementation)
  general-assistant/
    AGENT.md          — unchanged (folder-type, no agent.py)
  sql-analyst/
    AGENT.md          — unchanged (folder-type, no agent.py)
scripts/
  lint_tools.py       — NEW: CI lint script, exits non-zero if any tool missing INPUT_SCHEMA
tests/
  test_hybrid_registry.py   — NEW
  test_health_route.py      — NEW
  test_script_backend.py    — NEW (if ScriptBackend is introduced this phase)
  test_lint_tools.py        — NEW
```

### Pattern 1: Hybrid Agent Discovery

**What:** `SubAgentRegistry.__init__` iterates `agents/*/` directories. For each directory containing `AGENT.md`, it checks whether `agent.py` also exists. If yes, it loads the code-type agent via `importlib.util`; if no, it falls back to the current `SubAgent.from_dir()` folder-type instantiation.

**When to use:** Every startup — registry is built fresh per `OrchestratorHandler.handle()` call (existing pattern).

**Example:**
```python
# Source: stdlib importlib.util (Python 3.12 docs)
import importlib.util
from pathlib import Path

def _load_code_agent(agent_dir: Path, github_token: str) -> "SubAgent":
    spec = importlib.util.spec_from_file_location(
        f"agent_{agent_dir.name}",
        agent_dir / "agent.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # may raise ImportError, AttributeError
    agent_cls = module.SubAgent      # convention: code-type agents expose SubAgent class
    return agent_cls.from_dir(agent_dir, github_token)
```

### Pattern 2: Per-Agent Health Tracking

**What:** `SubAgentRegistry` stores a parallel `health: dict[str, AgentHealth]` alongside `agents: dict[str, SubAgent]`. Each entry is populated inside a per-agent `try/except` block during `__init__`. Successful load → `HEALTHY`. `ImportError` or missing dependency → `FAILED`. Partial-init (agent loaded but external check failed) → `DEGRADED`.

**When to use:** All registry construction — both at startup (via `app.state`) and per-job (OrchestratorHandler).

**Example:**
```python
from enum import Enum
from dataclasses import dataclass, field

class AgentStatusEnum(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"

@dataclass
class AgentHealth:
    name: str
    agent_type: str  # "folder" or "code"
    status: AgentStatusEnum
    error: str | None = None

# In SubAgentRegistry.__init__:
for agent_dir in Path(agent_dir_path).iterdir():
    if not (agent_dir / "AGENT.md").exists():
        continue
    try:
        if (agent_dir / "agent.py").exists():
            agent = _load_code_agent(agent_dir, github_token)
            agent_type = "code"
        else:
            agent = SubAgent.from_dir(agent_dir, github_token)
            agent_type = "folder"
        self.agents[agent.name] = agent
        self.health[agent.name] = AgentHealth(
            name=agent.name, agent_type=agent_type, status=AgentStatusEnum.HEALTHY
        )
    except Exception as e:
        name = agent_dir.name  # fallback name if AGENT.md unreadable
        self.health[name] = AgentHealth(
            name=name, agent_type="unknown",
            status=AgentStatusEnum.FAILED, error=str(e)
        )
```

**Critical:** the `except` block must NOT re-raise. This is the isolation guarantee for REGISTRY-03.

### Pattern 3: INPUT_SCHEMA Convention for Tool Scripts

**What:** Each tool script in `agents/<name>/tools/*.py` exposes a module-level constant `INPUT_SCHEMA` of type `dict` conforming to JSON Schema draft-7.

**When to use:** All new tool scripts. `ScriptBackend` reads this constant before invoking the script. `scripts/lint_tools.py` checks for its presence.

**Example:**
```python
# agents/code-reviewer/tools/lint_file.py
INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "file_path": {"type": "string"},
        "language": {"type": "string", "enum": ["python", "javascript", "typescript"]}
    },
    "required": ["file_path"],
    "additionalProperties": False,
}

def run(file_path: str, language: str = "python") -> dict:
    ...
```

### Pattern 4: ScriptBackend with jsonschema Validation

**What:** A `ScriptBackend` class (new module `app/orchestrator/script_backend.py`) dynamically loads a tool script module, validates the call arguments against `INPUT_SCHEMA`, then calls `module.run(**kwargs)`.

**Example:**
```python
# Source: jsonschema docs (https://python-jsonschema.readthedocs.io/)
import jsonschema
import importlib.util

class ScriptBackend:
    def call(self, script_path: Path, kwargs: dict) -> dict:
        spec = importlib.util.spec_from_file_location("tool", script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        schema = getattr(module, "INPUT_SCHEMA", None)
        if schema is not None:
            try:
                jsonschema.validate(instance=kwargs, schema=schema)
            except jsonschema.ValidationError as e:
                raise ValueError(f"Tool input validation failed: {e.message}")

        return module.run(**kwargs)
```

### Pattern 5: CI Lint Script

**What:** `scripts/lint_tools.py` iterates all `agents/*/tools/*.py`, imports each with `importlib.util`, and checks for `INPUT_SCHEMA`. Exits 1 if any are missing. Designed to be called from CI as `python scripts/lint_tools.py`.

**Example:**
```python
#!/usr/bin/env python3
import sys
import importlib.util
from pathlib import Path

errors = []
for tool_path in Path("agents").glob("*/tools/*.py"):
    spec = importlib.util.spec_from_file_location(tool_path.stem, tool_path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        errors.append(f"{tool_path}: import error — {e}")
        continue
    if not hasattr(mod, "INPUT_SCHEMA"):
        errors.append(f"{tool_path}: missing INPUT_SCHEMA constant")

if errors:
    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)

print(f"OK: {len(list(Path('agents').glob('*/tools/*.py')))} tool scripts validated")
```

### Pattern 6: Health Endpoint

**What:** `GET /health/agents` reads `app.state.registry` (registry stored at startup) and returns the full health list. This endpoint is NOT JWT-protected — health checks are internal/operational.

**Placement decision:** The registry needs to be built once at application startup (not per-job) for health reporting. This requires a change: the current `OrchestratorHandler` builds the registry per-job. The health registry at startup is a separate instance (metadata-only or lightweight), while OrchestratorHandler continues building per-job for multi-user token isolation.

**Alternative approach:** Store a metadata-only registry (no ChatCopilot instantiation) at startup just for health/discovery, and keep the per-job full registry for actual execution. This avoids needing github_token at startup for the health registry.

### Anti-Patterns to Avoid
- **Raising exceptions in registry __init__ for individual agents:** Stops the entire application. Use try/except per agent and record FAILED status instead.
- **Importing tool scripts at module level in agent.py:** Triggers import side effects on startup. Use `importlib.util.spec_from_file_location` lazily at call time (ScriptBackend) and eagerly but safely (lint script).
- **Using `exec(open(file).read())` instead of importlib:** Bypasses Python's import machinery; globals bleed between modules.
- **Making GET /health/agents JWT-protected:** Health endpoints are used by load balancers and ops tooling — they must not require auth cookies.
- **Glob pattern `**/AGENT.md` (recursive) for top-level agents only:** The current `SubAgentRegistry` uses `**/AGENT.md` which also matches nested subdirectories. For a flat `agents/*/` structure, `*/AGENT.md` is more precise and avoids accidental deep recursion. Consider whether to preserve recursive discovery.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON Schema validation | Custom type-checking code | `jsonschema.validate()` | Handles $ref, nested objects, required fields, additionalProperties, enum; edge cases are extensive |
| Dynamic module loading from file path | `exec(open(path).read())` | `importlib.util.spec_from_file_location` | Thread-safe, respects Python import system, returns real module object with `__file__` set |
| Health status enum | Plain string constants | `enum.Enum` (or `str, Enum` for JSON serialization) | Type safety, exhaustive matching, clean FastAPI serialization with `str, Enum` |

**Key insight:** The dynamic import problem (loading agent.py or tool scripts from arbitrary paths) is fully solved by `importlib.util` in the Python stdlib. No third-party plugin framework is needed for this scale.

---

## Common Pitfalls

### Pitfall 1: Registry Built Per-Job Has No Startup Health Data
**What goes wrong:** `OrchestratorHandler` builds `SubAgentRegistry` per job for token isolation. But `GET /health/agents` needs to show agent status at startup, before any job runs.
**Why it happens:** Health reporting requires a persistent registry, but execution requires per-job token injection.
**How to avoid:** Build two registry instances: (1) a metadata-only registry at app startup (no `github_token` needed, just parses AGENT.md and checks agent.py existence) stored on `app.state.agent_health`; (2) the full per-job registry in `OrchestratorHandler` as before. The health route reads from `app.state.agent_health`.
**Warning signs:** If the health route tries to instantiate `ChatCopilot` at startup without a github_token, it will fail with an auth error.

### Pitfall 2: Code-Type Agent Module Name Collision
**What goes wrong:** Two agents both have `agent.py` files. If loaded with the same module name (e.g., `"agent"`), Python's import system will cache the first and return it for the second.
**Why it happens:** `importlib.util.module_from_spec` doesn't automatically namespace by directory.
**How to avoid:** Use a unique module name per agent: `spec_from_file_location(f"agent_{agent_dir.name}", agent_dir / "agent.py")`. The `agent_dir.name` is the folder name (e.g., `"code-reviewer"`), which is unique.
**Warning signs:** Two code-type agents returning identical behavior.

### Pitfall 3: jsonschema.validate() Raises on Missing INPUT_SCHEMA
**What goes wrong:** If a tool script has no `INPUT_SCHEMA` and ScriptBackend calls `jsonschema.validate(instance, None)`, it raises `jsonschema.exceptions.SchemaError`.
**Why it happens:** `None` is not a valid schema.
**How to avoid:** In `ScriptBackend.call()`, guard with `if schema is not None:` before calling `validate()`. For tools without a schema (legacy or pre-TOOL-01), skip validation (permissive). The lint script enforces schema presence in CI; runtime is a best-effort safety net.
**Warning signs:** `SchemaError: None is not valid under any of the given schemas`.

### Pitfall 4: FAILED Agent Blocks Graph Compilation
**What goes wrong:** `build_orchestrator_graph()` iterates `registry.all()` to add nodes. If a FAILED agent is in `registry.agents`, its `agent.run` method doesn't exist and `graph.add_node(agent.name, agent.run)` raises.
**Why it happens:** The graph builder assumes all agents in `registry.all()` are fully initialized.
**How to avoid:** `registry.all()` should only return HEALTHY agents. FAILED/DEGRADED agents are tracked in `registry.health` but excluded from `registry.agents`. The health route reads `registry.health` (all statuses); the graph builder reads `registry.agents` (HEALTHY only).
**Warning signs:** `AttributeError: 'NoneType' object has no attribute 'run'` during graph compilation.

### Pitfall 5: Lint Script Fails on __init__.py or __pycache__
**What goes wrong:** `agents/*/tools/*.py` may match `__init__.py` files which have no `INPUT_SCHEMA` by design.
**Why it happens:** Glob includes all .py files.
**How to avoid:** Exclude `__init__.py` and files starting with `_` in the lint glob: `glob("*/tools/[!_]*.py")` or explicit name filter.
**Warning signs:** `CI ERROR: agents/code-reviewer/tools/__init__.py: missing INPUT_SCHEMA`.

### Pitfall 6: `app.state` Not Available in Worker Process
**What goes wrong:** Health route on `app.state.agent_health` is fine, but `OrchestratorHandler` runs in a separate arq worker process with no `app.state`.
**Why it happens:** arq worker is a separate process; FastAPI `app.state` is not shared.
**How to avoid:** Health registry lives in the FastAPI app process only. Worker builds its own full registry per job (unchanged current behavior). These are intentionally separate.
**Warning signs:** `AttributeError: 'dict' object has no attribute 'agent_health'` in worker logs.

---

## Code Examples

Verified patterns from official sources:

### Dynamic module loading (Python stdlib)
```python
# Source: https://docs.python.org/3.12/library/importlib.html#importlib.util.spec_from_file_location
import importlib.util

spec = importlib.util.spec_from_file_location("module_name", "/path/to/file.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
# module is now fully loaded; access attributes normally
```

### jsonschema validation
```python
# Source: https://python-jsonschema.readthedocs.io/en/stable/validate/
import jsonschema

schema = {
    "type": "object",
    "properties": {"name": {"type": "string"}},
    "required": ["name"],
}
# Raises jsonschema.ValidationError on failure, returns None on success
jsonschema.validate(instance={"name": "Alice"}, schema=schema)
```

### str Enum for FastAPI serialization
```python
# FastAPI serializes str Enum members as their string value automatically
from enum import Enum

class AgentStatusEnum(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
```

### Pydantic model for health response (matches existing models.py pattern)
```python
from pydantic import BaseModel
from typing import Optional

class AgentHealthEntry(BaseModel):
    name: str
    agent_type: str      # "folder" or "code"
    status: AgentStatusEnum
    error: Optional[str] = None
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single-type registry (AGENT.md only) | Hybrid: AGENT.md-only OR AGENT.md+agent.py | Phase 12 | Enables custom Python logic per agent while preserving zero-code-change folder-type path |
| No health status | HEALTHY/DEGRADED/FAILED per agent | Phase 12 | One broken agent no longer crashes startup |
| No input validation for tool scripts | INPUT_SCHEMA + jsonschema pre-call validation | Phase 12 | Early error detection; enables future LLM tool-calling (TOOL-04, v4.0) |

---

## Open Questions

1. **ScriptBackend scope in this phase**
   - What we know: TOOL-01 and TOOL-02 require INPUT_SCHEMA defined and validated. TOOL-02 says "ScriptBackend validates input before calling."
   - What's unclear: The current codebase has no tool scripts (no `tools/` subdirectory in any agent). Does ScriptBackend need to be wired into any agent execution path in Phase 12, or is it sufficient to define it as a standalone class and add test coverage?
   - Recommendation: Build ScriptBackend as a standalone class with tests, but do not wire it into SubAgent.run() yet (folder-type agents don't currently call tool scripts — they call the LLM directly). The lint script and INPUT_SCHEMA convention can be established with example tool scripts added to one agent for testing purposes.

2. **Startup vs per-job registry for health**
   - What we know: OrchestratorHandler builds a fresh SubAgentRegistry per job (by design for multi-user token isolation). GET /health/agents needs data available before any job runs.
   - What's unclear: Should the health registry at startup actually instantiate ChatCopilot (and thus require a token), or should it be metadata-only?
   - Recommendation: Health registry at startup is **metadata-only**: parse AGENT.md, detect agent.py presence, attempt the module load (without ChatCopilot instantiation), record HEALTHY/FAILED. This tests the Python import path without needing a github_token. A DEGRADED status could represent a successfully loaded module whose ChatCopilot initialization would fail at runtime.

3. **agent.py SubAgent interface contract**
   - What we know: The code-type agent in agent.py must expose something the registry can use. Current SubAgent has `.name`, `.description`, `.run()`, `.close()`.
   - What's unclear: Should agent.py expose a `SubAgent` class or a factory function? Should the registry enforce the interface via duck typing or a Protocol/ABC?
   - Recommendation: Convention-based: agent.py must expose a `SubAgent` class with `.from_dir(agent_dir, github_token)` classmethod. Enforce at load time with a clear error message if the class or method is missing.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | All | ✓ | 3.12.3 | — |
| `jsonschema` | TOOL-02, TOOL-03 | ✗ (not in pyproject.toml) | 4.26.0 on PyPI | None — must be added via `uv add jsonschema` |
| `importlib.util` | REGISTRY-02, TOOL-03 | ✓ (stdlib) | Python 3.12 stdlib | — |
| `python-frontmatter` | REGISTRY-01, REGISTRY-02 | ✓ | 1.1.0 | — |
| `pytest` + `pytest-asyncio` | All tests | ✓ | 8.x / 0.25.x | — |
| Docker Compose | Integration | ✓ | — | — |

**Missing dependencies with no fallback:**
- `jsonschema` — must be added before ScriptBackend can validate inputs; `uv add jsonschema` adds it to pyproject.toml and uv.lock

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.25.x |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `python3 -m pytest tests/test_hybrid_registry.py tests/test_health_route.py tests/test_lint_tools.py -x` |
| Full suite command | `python3 -m pytest tests/ --ignore=tests/test_orchestrator_graph.py -x` |

Note: `tests/test_orchestrator_graph.py` has an import error in the system Python environment due to `copilot` SDK version mismatch; this is a pre-existing environment issue, not a Phase 12 concern. The fix is to run tests inside Docker or with the project's `.venv`.

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REGISTRY-01 | Folder-type agent (AGENT.md only) auto-loads as HEALTHY | unit | `pytest tests/test_hybrid_registry.py::test_folder_type_agent_loads -x` | ❌ Wave 0 |
| REGISTRY-02 | Code-type agent (agent.py present) takes precedence, loads as HEALTHY | unit | `pytest tests/test_hybrid_registry.py::test_code_type_takes_precedence -x` | ❌ Wave 0 |
| REGISTRY-03 | Failed agent recorded as FAILED; other agents remain HEALTHY | unit | `pytest tests/test_hybrid_registry.py::test_failed_agent_isolated -x` | ❌ Wave 0 |
| REGISTRY-04 | GET /health/agents returns full status list | integration | `pytest tests/test_health_route.py -x` | ❌ Wave 0 |
| TOOL-01 | Tool script with INPUT_SCHEMA constant is accepted | unit | `pytest tests/test_script_backend.py::test_schema_present -x` | ❌ Wave 0 |
| TOOL-02 | ScriptBackend raises ValueError on schema violation | unit | `pytest tests/test_script_backend.py::test_validation_rejects_bad_input -x` | ❌ Wave 0 |
| TOOL-03 | lint_tools.py exits non-zero when tool missing INPUT_SCHEMA | unit | `pytest tests/test_lint_tools.py::test_missing_schema_exits_nonzero -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/test_hybrid_registry.py tests/test_health_route.py tests/test_script_backend.py tests/test_lint_tools.py -x`
- **Per wave merge:** `python3 -m pytest tests/ --ignore=tests/test_orchestrator_graph.py -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_hybrid_registry.py` — covers REGISTRY-01, REGISTRY-02, REGISTRY-03
- [ ] `tests/test_health_route.py` — covers REGISTRY-04 (FastAPI route test using ASGITransport pattern)
- [ ] `tests/test_script_backend.py` — covers TOOL-01, TOOL-02
- [ ] `tests/test_lint_tools.py` — covers TOOL-03

---

## Sources

### Primary (HIGH confidence)
- Python 3.12 stdlib `importlib.util` docs — `spec_from_file_location`, `module_from_spec`, `exec_module` patterns
- jsonschema 4.26.0 on PyPI (version verified via pypi.org/pypi/jsonschema/json API call)
- Existing codebase: `app/orchestrator/agent.py` (SubAgentRegistry current implementation)
- Existing codebase: `app/orchestrator/graph.py` (RouterNode, build_orchestrator_graph)
- Existing codebase: `app/jobs/handlers/orchestrator_handler.py` (per-job registry pattern)
- Existing codebase: `app/api/routes/agents.py` (existing agent metadata route pattern)
- Existing codebase: `tests/conftest.py` (test infrastructure patterns)
- Existing codebase: `pyproject.toml` (confirmed jsonschema is absent from deps)

### Secondary (MEDIUM confidence)
- jsonschema official docs at https://python-jsonschema.readthedocs.io — validate() API, ValidationError shape

### Tertiary (LOW confidence)
- None — all findings are based on direct codebase inspection and stdlib/official docs

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are stdlib or PyPI-verified; jsonschema version confirmed
- Architecture: HIGH — based on direct codebase reading, no speculation needed
- Pitfalls: HIGH — derived from reading actual code paths (graph builder, OrchestratorHandler, per-job registry pattern)

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (stable stdlib patterns; jsonschema is mature)
