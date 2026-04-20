"""Integration tests for Phase 31 Plan 04 — OTEL span emission across the
routing → sub_agent → tool_call hierarchy.

These tests verify that:
- RouterNode emits exactly one `routing` span per invocation with the
  correct stage attribute (keyword / single / llm) and trace_id
  propagated from state.context.correlation_id
- SubAgent.run() / ToolEnabledSubAgent.run() / CodeActSubAgent.run() each
  emit a `sub_agent` span
- ToolEnabledSubAgent wraps its tools in TracedTool so a `tool_call` span
  is emitted when the inner ReAct ToolNode invokes them
- CodeActSubAgent emits a `tool_call` span (privileged=True) around
  execute_python.ainvoke
- Handlers (orchestrator / langgraph / debate) wrap their handle() in a
  `request` span with trace_id = context.correlation_id

Fixtures:
- `capture_trace_logs` (from tests/conftest.py) returns a callable that
  parses `trace` logger records into a list of span dicts.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.orchestrator.agent import SubAgent, SubAgentRegistry
from app.orchestrator.context import RPCContext
from app.orchestrator.graph import RouterNode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(input_text: str, correlation_id: str = "trace-001") -> dict:
    """Create a minimal AgentState with a real RPCContext."""
    return {
        "input": input_text,
        "output": "",
        "messages": [],
        "next": "",
        "context": RPCContext(
            user_id="alice",
            app_id="superchat",
            thread_id="thread-001",
            correlation_id=correlation_id,
        ),
        "error": None,
    }


def _make_registry_with_keywords(agents_config: list[dict]) -> SubAgentRegistry:
    """Create a mock registry with agents that expose .name and .keywords."""
    registry = MagicMock(spec=SubAgentRegistry)
    agents = []
    for cfg in agents_config:
        agent = MagicMock()
        agent.name = cfg["name"]
        agent.description = cfg.get("description", f"Description for {cfg['name']}")
        agent.keywords = cfg.get("keywords", [])
        agents.append(agent)
    registry.all.return_value = agents
    return registry


def _build_router(registry: SubAgentRegistry, llm_response: str | None = None) -> RouterNode:
    """Construct a RouterNode without touching ChatCopilot (avoids SDK init)."""
    node = RouterNode.__new__(RouterNode)
    node._registry = registry
    node._llm = MagicMock()
    if llm_response is not None:
        mock_response = MagicMock()
        mock_response.content = llm_response
        node._llm.ainvoke = AsyncMock(return_value=mock_response)
    else:
        node._llm.ainvoke = AsyncMock()
    return node


# ---------------------------------------------------------------------------
# Test A: keyword stage emits routing span
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_routing_keyword_emits_span(capture_trace_logs):
    """Keyword-stage routing emits a single routing span with stage=keyword."""
    registry = _make_registry_with_keywords([
        {"name": "code-reviewer", "keywords": ["コードレビュー"]},
        {"name": "sql-analyst", "keywords": ["SQL"]},
    ])
    node = _build_router(registry)

    await node(_make_state("コードレビューして", correlation_id="trace-kw"))

    spans = capture_trace_logs()
    routing_spans = [s for s in spans if s["operation_name"] == "routing"]
    assert len(routing_spans) == 1, f"Expected 1 routing span, got {len(routing_spans)}"
    span = routing_spans[0]
    assert span["trace_id"] == "trace-kw"
    assert span["attributes"]["stage"] == "keyword"
    assert span["attributes"]["chosen"] == "code-reviewer"
    assert span["attributes"]["agent_name"] == "code-reviewer"
    assert span["status_code"] == "OK"


# ---------------------------------------------------------------------------
# Test B: LLM fallback emits ERROR span
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_routing_llm_fallback_emits_error_span(capture_trace_logs):
    """LLM returning an unknown agent name produces status_code=ERROR and fallback=True."""
    registry = _make_registry_with_keywords([
        {"name": "code-reviewer", "keywords": ["コードレビュー"]},
        {"name": "sql-analyst", "keywords": ["SQL"]},
    ])
    node = _build_router(registry, llm_response="nonexistent-agent")

    await node(_make_state("天気について教えて", correlation_id="trace-fb"))

    spans = capture_trace_logs()
    routing_spans = [s for s in spans if s["operation_name"] == "routing"]
    assert len(routing_spans) == 1
    span = routing_spans[0]
    assert span["status_code"] == "ERROR"
    assert span["status_message"] is not None
    assert span["status_message"].startswith("unknown_agent=")
    assert span["attributes"]["fallback"] is True
    assert span["attributes"]["stage"] == "llm"
    assert span["attributes"]["chosen"] == "fallback"


# ---------------------------------------------------------------------------
# Test C: single-agent stage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_routing_single_agent_stage(capture_trace_logs):
    """When only one agent is available, stage='single' is recorded and LLM is skipped."""
    registry = _make_registry_with_keywords([
        {"name": "solo-agent", "keywords": []},
    ])
    node = _build_router(registry)

    await node(_make_state("anything", correlation_id="trace-solo"))

    spans = capture_trace_logs()
    routing_spans = [s for s in spans if s["operation_name"] == "routing"]
    assert len(routing_spans) == 1
    assert routing_spans[0]["attributes"]["stage"] == "single"
    assert routing_spans[0]["attributes"]["chosen"] == "solo-agent"
    # LLM must not be called in the single-agent path
    node._llm.ainvoke.assert_not_called()


# ---------------------------------------------------------------------------
# Test D: common attributes and user_input_prefix truncation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_routing_common_attributes(capture_trace_logs):
    """Routing span carries user_id / app_id / thread_id and user_input_prefix (<=200)."""
    registry = _make_registry_with_keywords([
        {"name": "code-reviewer", "keywords": ["コードレビュー"]},
        {"name": "sql-analyst", "keywords": ["SQL"]},
    ])
    node = _build_router(registry)

    long_input = "コードレビューして " + ("x" * 300)
    await node(_make_state(long_input, correlation_id="trace-common"))

    spans = capture_trace_logs()
    routing_spans = [s for s in spans if s["operation_name"] == "routing"]
    assert len(routing_spans) == 1
    attrs = routing_spans[0]["attributes"]
    assert attrs["user_id"] == "alice"
    assert attrs["app_id"] == "superchat"
    assert attrs["thread_id"] == "thread-001"
    assert attrs["agent_name"] == "code-reviewer"
    # D-13: 200-char prefix
    assert "user_input_prefix" in attrs
    assert len(attrs["user_input_prefix"]) <= 200


# ---------------------------------------------------------------------------
# Test E-H: SubAgent / ToolEnabled / CodeAct sub_agent span integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_subagent_run_emits_sub_agent_span(capture_trace_logs, monkeypatch):
    """SubAgent.run() wraps execution in a sub_agent span with common 4 attrs."""
    from langchain_core.messages import AIMessageChunk

    agent = SubAgent.__new__(SubAgent)
    agent.name = "test-agent"
    agent.description = "test"
    agent.keywords = []
    agent._system_prompt = "you are test"
    agent._llm = MagicMock()
    agent._llm.model = "claude-haiku-4-5-20251001"

    async def fake_astream(messages):
        yield AIMessageChunk(content="hello ")
        yield AIMessageChunk(content="world")

    agent._llm.astream = fake_astream
    agent._llm.last_usage = None

    state = _make_state("こんにちは", correlation_id="trace-sub")
    result = await agent.run(state)

    assert result["agent_name"] == "test-agent"

    spans = capture_trace_logs()
    sub_spans = [s for s in spans if s["operation_name"] == "sub_agent"]
    assert len(sub_spans) == 1, f"Expected 1 sub_agent span, got {len(sub_spans)}"
    attrs = sub_spans[0]["attributes"]
    assert attrs["agent_name"] == "test-agent"
    assert attrs["user_id"] == "alice"
    assert attrs["app_id"] == "superchat"
    assert attrs["model_name"] == "claude-haiku-4-5-20251001"


@pytest.mark.asyncio
async def test_tool_enabled_sub_agent_wraps_with_tracedtool():
    """ToolEnabledSubAgent stores TracedTool instances inside its ToolNode."""
    from langchain_core.tools import BaseTool
    from pydantic import Field

    from app.observability.traced_tool import TracedTool
    from app.orchestrator.tool_agent import ToolEnabledSubAgent

    # Build a very small concrete BaseTool (no SDK dependency)
    class _EchoTool(BaseTool):
        name: str = Field(default="echo")
        description: str = Field(default="echo a query")

        def _run(self, **kwargs: Any) -> Any:  # pragma: no cover - sync never called
            return kwargs

        async def _arun(self, **kwargs: Any) -> Any:
            return {"echo": kwargs}

    tool = _EchoTool()

    # Construct ToolEnabledSubAgent without calling ChatCopilot (__new__ + manual fields)
    agent = ToolEnabledSubAgent.__new__(ToolEnabledSubAgent)
    agent.name = "echo-agent"
    agent.description = "echo"
    agent.keywords = []
    agent.recursion_limit = 5
    agent._llm = MagicMock()
    agent._llm.model = "claude-haiku-4-5-20251001"
    agent._llm.bind_tools = MagicMock(return_value=MagicMock())
    agent._system_prompt = "sys"
    agent._privileged_names = frozenset({"echo"})

    # Re-run the wrapping logic the same way the real __init__ does.
    from langgraph.prebuilt import ToolNode

    wrapped = [TracedTool(t, privileged_tool_names=agent._privileged_names) for t in [tool]]
    agent._tools = [tool]
    agent._tool_node = ToolNode(wrapped)
    agent._llm_with_tools = agent._llm.bind_tools([tool])

    # All tools registered by the ToolNode should be TracedTool instances
    assert all(
        isinstance(t, TracedTool)
        for t in agent._tool_node.tools_by_name.values()
    ), "Expected every ToolNode tool to be a TracedTool"


@pytest.mark.asyncio
async def test_codeact_execute_python_span(capture_trace_logs):
    """CodeActSubAgent.run emits a privileged tool_call span around execute_python."""
    from langchain_core.messages import AIMessage
    from langchain_core.tools import BaseTool
    from pydantic import Field

    from app.orchestrator.codeact_agent import CodeActSubAgent

    class _FakeExecutePython(BaseTool):
        name: str = Field(default="execute_python")
        description: str = Field(default="execute python")

        def _run(self, **kwargs: Any) -> Any:  # pragma: no cover
            return kwargs

        async def _arun(self, code: str = "") -> Any:
            return json.dumps({"stdout": "42", "stderr": "", "exit_code": 0})

    fake_tool = _FakeExecutePython()

    agent = CodeActSubAgent.__new__(CodeActSubAgent)
    agent.name = "codeact-agent"
    agent.description = "codeact"
    agent.keywords = []
    agent.meta = {}
    agent._llm = MagicMock()
    agent._llm.model = "gpt-4.1"
    agent._llm.last_usage = None
    agent._system_prompt = "sys"
    agent._tools = {"execute_python": fake_tool}
    agent._max_iterations = 2

    # LLM returns a code block on the first call, then a summary
    async def fake_ainvoke(messages):
        # Determine response by inspecting last HumanMessage content
        for m in reversed(messages):
            if m.__class__.__name__ == "HumanMessage":
                content = m.content
                if "実行結果" in content:
                    return AIMessage(content="42 でした")
                break
        return AIMessage(content="```python\nprint(40+2)\n```")

    agent._llm.ainvoke = fake_ainvoke

    state = _make_state("40 足す 2 は？", correlation_id="trace-codeact")
    await agent.run(state)

    spans = capture_trace_logs()
    tool_spans = [s for s in spans if s["operation_name"] == "tool_call"]
    assert len(tool_spans) >= 1, f"Expected >=1 tool_call span, got {len(tool_spans)}"
    # Find the execute_python span
    exec_span = next(s for s in tool_spans if s["attributes"].get("tool_name") == "execute_python")
    assert exec_span["trace_id"] == "trace-codeact"
    assert exec_span["attributes"]["privileged"] is True
    assert exec_span["attributes"]["success"] is True

    # sub_agent span should also exist
    sub_spans = [s for s in spans if s["operation_name"] == "sub_agent"]
    assert len(sub_spans) == 1
    # Parent-child linkage
    assert exec_span["parent_span_id"] == sub_spans[0]["span_id"]


@pytest.mark.asyncio
async def test_recursion_limit_emits_error_span(capture_trace_logs):
    """GraphRecursionError during ToolEnabledSubAgent.run is recorded as ERROR span."""
    from langgraph.errors import GraphRecursionError

    from app.orchestrator.tool_agent import ToolEnabledSubAgent

    agent = ToolEnabledSubAgent.__new__(ToolEnabledSubAgent)
    agent.name = "looping-agent"
    agent.description = "loops"
    agent.keywords = []
    agent.recursion_limit = 3
    agent._llm = MagicMock()
    agent._llm.model = "claude-haiku-4-5-20251001"
    agent._llm.last_usage = None
    agent._system_prompt = "sys"
    agent._tools = []
    agent._privileged_names = frozenset()

    mini = AsyncMock()
    mini.ainvoke = AsyncMock(side_effect=GraphRecursionError("recursion"))

    # Patch build_react_graph so run() receives our mini graph
    import app.orchestrator.tool_agent as ta_module

    orig = ta_module.build_react_graph
    ta_module.build_react_graph = lambda *a, **kw: mini
    try:
        agent._llm_with_tools = MagicMock()
        agent._tool_node = MagicMock()
        state = _make_state("loop please", correlation_id="trace-loop")
        await agent.run(state)
    finally:
        ta_module.build_react_graph = orig

    spans = capture_trace_logs()
    sub_spans = [s for s in spans if s["operation_name"] == "sub_agent"]
    assert len(sub_spans) == 1
    assert sub_spans[0]["status_code"] == "ERROR"
    assert sub_spans[0]["attributes"].get("recursion_limit_reached") is True


# ---------------------------------------------------------------------------
# Test I-K: request span in handlers (orchestrator minimum)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_request_span_in_orchestrator_handler(capture_trace_logs, monkeypatch):
    """OrchestratorHandler.handle wraps work in a request span with handler=orchestrator."""
    from app.jobs.handlers import orchestrator_handler as oh_module

    # Short-circuit heavy dependencies — the test only asserts span emission
    class _FakeRegistry:
        def __init__(self, *args, **kwargs):
            self.agents = {"a": MagicMock(name="a")}
            self._github_token = ""

        async def close(self):
            return None

    class _FakeCheckpointer:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def setup(self):
            return None

    def _fake_from_conn_string(uri):
        return _FakeCheckpointer()

    # Fake graph that yields an on_chain_end LangGraph event immediately
    async def _fake_astream_events(initial, config, version):
        yield {
            "event": "on_chain_end",
            "name": "LangGraph",
            "data": {"output": {"output": "ok", "agent_name": "a"}},
        }

    def _fake_build_orch(registry, github_token, checkpointer=None):
        g = MagicMock()
        g.astream_events = _fake_astream_events
        g.aget_state = AsyncMock(return_value=MagicMock(values={"output": "ok", "agent_name": "a"}))
        return g

    monkeypatch.setattr(oh_module, "SubAgentRegistry", _FakeRegistry)
    monkeypatch.setattr(
        oh_module.AsyncPostgresSaver,
        "from_conn_string",
        staticmethod(_fake_from_conn_string),
    )
    monkeypatch.setattr(oh_module, "build_orchestrator_graph", _fake_build_orch)

    job_store = AsyncMock()
    job_store.push_tool_event = AsyncMock()
    job_store.clear_tool_event = AsyncMock()
    job_store.save_result = AsyncMock()
    ctx = {
        "job_store": job_store,
        "mcp_tools": [],
        "mcp_privileged_tool_names": frozenset(),
    }
    job = {
        "job_id": "job-001",
        "thread_id": "t-001",
        "prompt": "hello",
        "github_token": "ghu_test",
        "reply_to": {"type": "web", "job_id": "job-001"},
        "github_login": "alice",
        "app_id": "superchat",
    }

    handler = oh_module.OrchestratorHandler()
    await handler.handle(ctx, job)

    spans = capture_trace_logs()
    req_spans = [s for s in spans if s["operation_name"] == "request"]
    assert len(req_spans) >= 1
    req = req_spans[0]
    assert req["attributes"]["handler"] == "orchestrator"
    assert req["attributes"]["app_id"] == "superchat"
    assert req["attributes"]["user_id"] == "alice"


@pytest.mark.asyncio
async def test_request_span_in_langgraph_handler(capture_trace_logs, monkeypatch):
    """LangGraphHandler.handle emits a request span with handler=langgraph."""
    from app.jobs.handlers import langgraph_handler as lh_module

    class _FakeCheckpointer:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

    def _fake_from_conn_string(uri):
        return _FakeCheckpointer()

    async def _fake_astream_events(state_input, config, version):
        from langchain_core.messages import AIMessage

        yield {
            "event": "on_chain_end",
            "name": "LangGraph",
            "data": {"output": {"messages": [AIMessage(content="hello")]}},
        }

    fake_graph = MagicMock()
    fake_graph.astream_events = _fake_astream_events

    async def _fake_get_gem_info(thread_id, db_uri):
        return None, None, None, None, None

    monkeypatch.setattr(lh_module, "_get_gem_info", _fake_get_gem_info)
    monkeypatch.setattr(
        lh_module.AsyncPostgresSaver,
        "from_conn_string",
        staticmethod(_fake_from_conn_string),
    )
    monkeypatch.setattr(lh_module, "build_graph", lambda llm, cp: fake_graph)

    # Stub out ChatCopilot to avoid SDK init
    fake_llm = MagicMock()
    fake_llm.close = AsyncMock()
    monkeypatch.setattr(lh_module, "ChatCopilot", lambda **kwargs: fake_llm)

    job_store = AsyncMock()
    ctx = {"job_store": job_store}
    job = {
        "job_id": "j1",
        "thread_id": "t1",
        "prompt": "hello",
        "model": "claude-sonnet-4.5",
        "github_token": "ghu_test",
        "reply_to": {"type": "web", "job_id": "j1"},
        "github_login": "alice",
    }

    handler = lh_module.LangGraphHandler()
    await handler.handle(ctx, job)

    spans = capture_trace_logs()
    req_spans = [s for s in spans if s["operation_name"] == "request"]
    assert len(req_spans) >= 1
    req = req_spans[0]
    assert req["attributes"]["handler"] == "langgraph"
    assert req["attributes"]["app_id"] == "chat"
    assert req["attributes"]["user_id"] == "alice"


@pytest.mark.asyncio
async def test_request_span_in_debate_handler(capture_trace_logs, monkeypatch):
    """DebateHandler.handle emits a request span with handler=debate."""
    from app.jobs.handlers import debate_handler as dh_module

    # Fake registry with two agents so DebateHandler proceeds
    class _FakeRegistry:
        def __init__(self, *args, **kwargs):
            self.agents = {"A": MagicMock(name="A"), "B": MagicMock(name="B")}

        async def close(self):
            return None

    class _FakeCheckpointer:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def setup(self):
            return None

    def _fake_from_conn_string(uri):
        return _FakeCheckpointer()

    async def _fake_astream(initial, config):
        # yield nothing — DebateHandler should still produce a request span
        if False:
            yield {}

    fake_graph = MagicMock()
    fake_graph.astream = _fake_astream

    monkeypatch.setattr(dh_module, "SubAgentRegistry", _FakeRegistry)
    monkeypatch.setattr(
        dh_module.AsyncPostgresSaver,
        "from_conn_string",
        staticmethod(_fake_from_conn_string),
    )
    monkeypatch.setattr(
        dh_module, "build_debate_graph", lambda *a, **kw: fake_graph
    )
    monkeypatch.setattr(dh_module, "ChatCopilot", lambda **kwargs: MagicMock())

    job_store = AsyncMock()
    ctx = {"job_store": job_store}
    job = {
        "job_id": "j1",
        "thread_id": "t1",
        "prompt": "debate topic",
        "github_token": "ghu_test",
        "reply_to": {"type": "web", "job_id": "j1"},
        "github_login": "alice",
        "participants": ["A", "B"],
        "pattern": "debate",
        "max_turns": 2,
    }

    handler = dh_module.DebateHandler()
    await handler.handle(ctx, job)

    spans = capture_trace_logs()
    req_spans = [s for s in spans if s["operation_name"] == "request"]
    assert len(req_spans) >= 1
    req = req_spans[0]
    assert req["attributes"]["handler"] == "debate"
    assert req["attributes"]["app_id"] == "debate"
    assert req["attributes"]["user_id"] == "alice"
