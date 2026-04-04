# tests/test_rpc_context.py
"""Unit tests for RPCContext dataclass and _keep_first reducer."""
import dataclasses
import pytest

from app.orchestrator.context import RPCContext, _keep_first


class TestRPCContextFrozen:
    def test_rpccontext_frozen(self):
        """RPCContext is frozen — field assignment raises FrozenInstanceError."""
        ctx = RPCContext(user_id="u1")
        with pytest.raises(dataclasses.FrozenInstanceError):
            ctx.user_id = "x"  # type: ignore[misc]


class TestRPCContextDefaults:
    def test_rpccontext_defaults(self):
        """RPCContext(user_id='u1') has app_id='', thread_id='', and a non-empty UUID correlation_id."""
        ctx = RPCContext(user_id="u1")
        assert ctx.user_id == "u1"
        assert ctx.app_id == ""
        assert ctx.thread_id == ""
        assert ctx.correlation_id != ""
        assert len(ctx.correlation_id) == 36  # UUID4 string length

    def test_rpccontext_correlation_id_unique(self):
        """Two RPCContext instances have different correlation_ids."""
        ctx_a = RPCContext(user_id="u1")
        ctx_b = RPCContext(user_id="u1")
        assert ctx_a.correlation_id != ctx_b.correlation_id


class TestRPCContextFactories:
    def test_from_http_factory(self):
        """RPCContext.from_http() produces correct fields with auto-generated correlation_id."""
        ctx = RPCContext.from_http(user_id="alice", app_id="superchat", thread_id="t1")
        assert ctx.user_id == "alice"
        assert ctx.app_id == "superchat"
        assert ctx.thread_id == "t1"
        assert ctx.correlation_id != ""

    def test_from_slack_factory_with_thread_ts(self):
        """RPCContext.from_slack() uses thread_ts as thread_id when present."""
        event = {"user": "U123", "thread_ts": "ts1", "ts": "ts2"}
        ctx = RPCContext.from_slack(event)
        assert ctx.user_id == "U123"
        assert ctx.thread_id == "ts1"

    def test_from_slack_factory_falls_back_to_ts(self):
        """RPCContext.from_slack() falls back to ts when thread_ts is absent."""
        event = {"user": "U123", "ts": "ts2"}
        ctx = RPCContext.from_slack(event)
        assert ctx.user_id == "U123"
        assert ctx.thread_id == "ts2"


class TestKeepFirst:
    def test_keep_first_preserves_existing(self):
        """_keep_first(ctx_a, ctx_b) returns ctx_a."""
        ctx_a = RPCContext(user_id="alice")
        ctx_b = RPCContext(user_id="bob")
        result = _keep_first(ctx_a, ctx_b)
        assert result is ctx_a

    def test_keep_first_none_first_arg(self):
        """_keep_first(None, ctx_b) returns ctx_b — handles unset checkpoint case."""
        ctx_b = RPCContext(user_id="bob")
        result = _keep_first(None, ctx_b)
        assert result is ctx_b
