"""Phase 38 Wave 0 risk-gate: AIMessage.additional_kwargs.attachments の AsyncPostgresSaver round-trip 検証。

VALIDATION.md Task ID マッピング:
- 38-01-01 → test_round_trip_postgres        (本 plan で実装 / GREEN)
- 38-04-03 → test_bundles_generated_files    (Plan 04 で実装 / skip scaffold)

設計根拠:
- patterns.md §"Wave 0 risk-gate — checkpointer round-trip を MVP 前に潰す" (L94-99)
- 38-RESEARCH.md §"Pattern 2: AIMessage.additional_kwargs.attachments で AI 生成ファイルを turn 単位で bundle"
- 38-RESEARCH.md §"Assumptions Log A2": HumanMessage 側の round-trip は Phase 36 Wave 0 で
  検証済だが、AIMessage 側は ADR-0038 の name 喪失問題に隣接するため独立検証が必要。

postgres 接続が利用できない CI / ローカルでは pytest.skip で逃がす。
"""
from __future__ import annotations

import os
import socket
import uuid

import pytest
from langchain_core.messages import AIMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing import Annotated, TypedDict


def _can_connect_postgres(host: str, port: int = 5432, timeout: float = 1.5) -> bool:
    """postgres host:port に TCP 接続できるか判定。"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _build_db_uri() -> str | None:
    """テスト用 DATABASE_URL を解決する。

    優先順位:
      1. PYTEST_DATABASE_URL 環境変数（テスト専用）
      2. DATABASE_URL 環境変数
      3. localhost:5432 (port-forward 環境)
      4. 172.17.0.1 / docker compose 内 postgres (CI フォールバック)
    """
    for env_key in ("PYTEST_DATABASE_URL", "DATABASE_URL"):
        uri = os.environ.get(env_key)
        if uri:
            return uri

    # 候補ホスト群: docker compose 経由で起動する場合の典型的アドレス
    candidates = [
        ("localhost", 5432),
        ("127.0.0.1", 5432),
        ("172.26.0.2", 5432),  # docker bridge subnet 既定値
    ]
    for host, port in candidates:
        if _can_connect_postgres(host, port):
            return (
                f"postgresql://postgres:postgres@{host}:{port}/postgres?sslmode=disable"
            )
    return None


# ---------------------------------------------------------------------------
# State schema (最小 graph 用)
# ---------------------------------------------------------------------------


class _State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def _make_generated_meta(name: str = "20260512T120000_chart.png") -> dict:
    """Phase 38 D-30 案 A 準拠の AttachmentMeta (kind='generated')。

    JSONB 経由 round-trip の対象。値・order・kind 全フィールド一致が assert 対象。
    """
    return {
        "kind": "generated",
        "name": name,
        "size": 123,
        "ext": ".png",
        "modified_at": 1.0,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_round_trip_postgres():
    """38-01-01 — AIMessage.additional_kwargs.attachments が AsyncPostgresSaver 経由で完全 round-trip する。

    patterns.md L94-99: 新規データを additional_kwargs に載せる場合、AsyncPostgresSaver の
    JSONB serialize/deserialize 経路で値・order・kind が壊れないことを Wave 0 で 1 plan で潰す。

    AIMessage 側に additional_kwargs.attachments を載せて 1 thread に invoke → checkpoint
    保存 → 別接続から get_state で復元 → 元と同一の dict が戻ることを assert する。
    """
    db_uri = _build_db_uri()
    if db_uri is None:
        pytest.skip(
            "PostgreSQL is not reachable on common candidates. "
            "Set PYTEST_DATABASE_URL or DATABASE_URL, or start `docker compose up postgres`."
        )

    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    generated_meta = _make_generated_meta()
    thread_id = f"rt-{uuid.uuid4().hex[:8]}"

    def _emit_ai(state: _State) -> _State:
        ai = AIMessage(
            content="ok",
            additional_kwargs={"attachments": [generated_meta]},
        )
        return {"messages": [ai]}

    # 1st connection: setup + invoke + checkpoint 保存
    async with AsyncPostgresSaver.from_conn_string(db_uri) as saver:
        await saver.setup()
        builder = StateGraph(_State)
        builder.add_node("emit_ai", _emit_ai)
        builder.add_edge(START, "emit_ai")
        builder.add_edge("emit_ai", END)
        graph = builder.compile(checkpointer=saver)

        config = {"configurable": {"thread_id": thread_id}}
        result = await graph.ainvoke({"messages": []}, config=config)

        # In-process 整合確認 — checkpoint 前に AIMessage が想定通り組み立てられているか
        last = result["messages"][-1]
        assert isinstance(last, AIMessage)
        assert last.additional_kwargs.get("attachments") == [generated_meta]

    # 2nd connection: 別 saver で復元 → JSONB serialize/deserialize 経路を通る
    async with AsyncPostgresSaver.from_conn_string(db_uri) as restored_saver:
        snapshot = await restored_saver.aget(
            {"configurable": {"thread_id": thread_id}}
        )
        assert snapshot is not None, (
            "checkpoint not found in postgres — was setup/invoke committed?"
        )
        # langgraph checkpoint API: returned shape is a CheckpointTuple-like dict
        # whose ['channel_values']['messages'] holds the persisted message list.
        # Compose graph では `messages` channel が add_messages reducer で list を保持。
        channel_values = snapshot.get("channel_values") or {}
        messages = channel_values.get("messages") or []
        assert messages, "messages channel is empty after restore"
        restored_ai = messages[-1]
        # Must be an AIMessage (BaseMessage subclass)
        assert getattr(restored_ai, "type", None) == "ai", (
            f"expected AI message after round-trip, got type={getattr(restored_ai, 'type', None)!r}"
        )
        restored_atts = restored_ai.additional_kwargs.get("attachments")
        assert restored_atts is not None, (
            "additional_kwargs.attachments was lost during JSONB round-trip"
        )
        # 値・order・kind すべて一致
        assert restored_atts == [generated_meta], (
            f"round-trip mismatch: got {restored_atts!r}, expected {[generated_meta]!r}"
        )
        # 個別 field の独立確認 (kind が enum 値として丸ごと残ること)
        assert restored_atts[0]["kind"] == "generated"
        assert restored_atts[0]["name"] == generated_meta["name"]
        assert restored_atts[0]["size"] == 123
        assert restored_atts[0]["ext"] == ".png"
        assert restored_atts[0]["modified_at"] == 1.0


@pytest.mark.skip(
    reason="Plan 04 で実装: turn 完了時に AIMessage.additional_kwargs.attachments へ bundle される"
)
@pytest.mark.asyncio
async def test_bundles_generated_files():
    """38-04-03 — turn 完了で LangGraphHandler が _generated/ delta を AI 最終 message に bundle。

    Plan 04 で `app/jobs/handlers/langgraph_handler.py` の final_state 確定直後に
    scan_thread_attachments 再 scan → kind=generated の delta を抽出 → AI 最終 message の
    additional_kwargs.attachments にマージする実装と同時に green 化する。

    本 plan (38-01) では skip scaffold のみ。
    """
    raise AssertionError("Plan 04 で実装")


@pytest.mark.skip(
    reason="Plan 04 で実装: handler が同じ generated ファイルを 2 回 bundle しないこと"
)
@pytest.mark.asyncio
async def test_handler_does_not_double_count():
    """38-04-03 補強 — 既に AI message に bundle 済の generated ファイルは再追加されないこと。

    Plan 04 の delta 抽出ロジック (snapshot diff) が前回 bundle 済のファイル名を
    除外することを assert する。本 plan では skip scaffold のみ。
    """
    raise AssertionError("Plan 04 で実装")
