"""Phase 38 Plan 02 / Plan 04: GET /api/threads/{tid}/outputs/{name} route の integration test scaffold.

VALIDATION.md Task ID マッピング:
- 38-01-02 → test_isolation_other_user_blocked  (Plan 02 で実装、本 plan は skip scaffold)
- 38-01-03 → test_path_traversal_rejected       (Plan 02 で実装、本 plan は skip scaffold)
- 38-04-01 → test_get_output_returns_raw_bytes  (Plan 04 で実装、本 plan は skip scaffold)
- 38-04-02 → test_get_output_works_for_claude_code (Plan 04 で実装、本 plan は skip scaffold)

Analog: tests/test_attachments_get_delete_route.py (jwt_cookie fixture + tmp_path monkeypatch + ASGI client)

Phase 38-PATTERNS.md §"Plan 06 Tests §tests/test_outputs_route.py" 参照。
本 plan (38-01) は shape (import + fixture + skip stub) のみ整備し、
Plan 02/04 の executor が skip マーカーを外して assertion 本体を書く運用。
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.fixture(autouse=True)
def patch_thread_files_dir(tmp_path, monkeypatch):
    """attachments module の THREAD_FILES_DIR を tmp_path に差し替える。

    outputs.py (Plan 02 で新設) が attachments.py から `_resolve_thread_folder` /
    `_safe_resolve_file` を import で再利用する設計なので、attachments_module の
    monkeypatch だけで outputs route の path 解決もカバーできる。
    """
    from app.api.routes import attachments as attachments_module

    monkeypatch.setattr(attachments_module, "THREAD_FILES_DIR", str(tmp_path))
    yield


@pytest.mark.skip(
    reason="Plan 04 (38-04) で outputs route 実装と同時に green 化 — 38-04-01"
)
@pytest.mark.asyncio
async def test_get_output_returns_raw_bytes(
    api_client: AsyncClient, jwt_cookie, tmp_path
):
    """38-04-01 — _generated/ に直接置いたファイルを GET → 200 + 内容一致 + Content-Disposition: inline。"""
    raise AssertionError("Plan 04 で実装")


@pytest.mark.skip(
    reason="Plan 02 (38-02) で outputs route + path traversal guard 実装と同時に green 化 — 38-01-03"
)
@pytest.mark.asyncio
async def test_path_traversal_rejected(api_client: AsyncClient, jwt_cookie):
    """38-01-03 — `../../../etc/passwd` を URL-encode した name で GET → 400 / 404 / 405 (200 は NG)。"""
    raise AssertionError("Plan 02 で実装")


@pytest.mark.skip(
    reason="Plan 02 (38-02) で multi-user isolation (Phase 36 helper 再利用) を outputs route に適用 — 38-01-02"
)
@pytest.mark.asyncio
async def test_isolation_other_user_blocked(api_client: AsyncClient):
    """38-01-02 — 別 user JWT で他人の _generated/ にアクセス → 401/404 (FOUT-04 sc5)。

    Phase 36 で確立した `_resolve_thread_folder` の realpath guard + JWT payload の
    github_login → folder path 解決経路をそのまま流用すれば、
    新規実装ゼロで isolation が担保される (CONTEXT.md D-19)。
    """
    raise AssertionError("Plan 02 で実装")


@pytest.mark.skip(
    reason="Plan 04 (38-04) で claude_code 生成物の取得経路を outputs route 経由に統合 — 38-04-02"
)
@pytest.mark.asyncio
async def test_get_output_works_for_claude_code(api_client: AsyncClient, jwt_cookie):
    """38-04-02 — claude_code が _generated/ 配下に出力したファイルも GET で同一経路で取得できる。"""
    raise AssertionError("Plan 04 で実装")
