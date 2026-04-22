"""Phase 37 Wave 0 spike follow-up: RPCContext propagation smoke test.

Verdict from work/phase-37/spike-mcp-headers.md determines which route to exercise.

Spike result (2026-04-21):
  Verdict: Route A 採用
  - langchain-mcp-adapters 0.2.2 の StreamableHttpConnection TypedDict に
    headers フィールドが存在し、httpx.AsyncClient(headers=...) 経由で
    各 tool call リクエストに x-thread-id / x-github-login が付与される。
  - FastMCP 3.2.3 の CurrentHeaders() dependency injection で受け取り可能。

このファイルは Wave 0 の骨組みであり、Wave 1 (Plan 03) で
attachments_list / attachments_extract の本実装が入ったタイミングで
xfail アノテーションを外して実テストに昇格させる。
"""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
@pytest.mark.xfail(reason="Phase 37 Wave 1 で本実装が入るまで保留", strict=False)
async def test_mcp_context_headers_smoke():
    """Route A 採用: MultiServerMCPClient が x-thread-id を転送し、
    mcp-server 側の @mcp.tool が CurrentHeaders() で受け取れる前提の smoke test。

    Wave 1 (Plan 03) 完了後、以下を実テストに差し替える:
    1. mcp-server の attachments_list ツールを in-process で起動
    2. MultiServerMCPClient(headers={"x-thread-id": "t1", "x-github-login": "u1"}) で接続
    3. attachments_list を invoke して CurrentHeaders() に x-thread-id が届くことを検証
    """
    assert True  # Wave 1 で実装置換


@pytest.mark.asyncio
@pytest.mark.xfail(reason="Phase 37 Wave 1 で本実装が入るまで保留", strict=False)
async def test_streamable_http_connection_accepts_headers_field():
    """StreamableHttpConnection TypedDict の headers フィールドが
    MultiServerMCPClient に渡せることの型レベル検証。

    Wave 1 で attachments_list が実装されたら実接続テストへ移行する。
    """
    from langchain_mcp_adapters.sessions import StreamableHttpConnection

    conn: StreamableHttpConnection = {
        "transport": "streamable_http",
        "url": "http://localhost:8001/mcp",
        "headers": {"x-thread-id": "smoke-t", "x-github-login": "smoke-u"},
    }
    # TypedDict の型チェックのみ — 接続は行わない
    assert conn["headers"] == {"x-thread-id": "smoke-t", "x-github-login": "smoke-u"}
