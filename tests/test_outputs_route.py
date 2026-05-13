"""Phase 38 Plan 02 / Plan 04: GET /api/threads/{tid}/outputs/{name} route の integration test.

VALIDATION.md Task ID マッピング:
- 38-01-02 → test_isolation_other_user_blocked  (Plan 02 で green 化)
- 38-01-03 → test_path_traversal_rejected       (Plan 02 で green 化)
- 38-04-01 → test_get_output_returns_raw_bytes  (Plan 02 で green 化)
- 38-04-02 → test_get_output_works_for_claude_code (Plan 04 で green 化、本 plan では skip 維持)

Analog: tests/test_attachments_get_delete_route.py (jwt_cookie fixture + tmp_path monkeypatch + ASGI client)

D-19 整合スタンス: outputs.py は attachments.py の `_resolve_thread_folder` /
`_safe_resolve_file` / `_normalize_basename` を import で再利用する。Phase 38 では
isolation 単体テストを新規追加しない — Plan 01 scaffold の 2 ケース
(test_path_traversal_rejected / test_isolation_other_user_blocked) は Phase 36 helper
再利用の smoke 検証として位置づける。
"""
from __future__ import annotations

import os
import urllib.parse

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


@pytest.mark.asyncio
async def test_get_output_returns_raw_bytes(
    api_client: AsyncClient, jwt_cookie, tmp_path
):
    """38-04-01 — _generated/ に直接置いたファイルを GET → 200 + 内容一致 + Content-Disposition: inline。

    `tests/conftest.py::jwt_cookie` の payload は github_login=None のため、folder は
    `{tmp_path}/unknown/{thread_id}/` で組み立てられる前提 (tests/test_attachments_get_delete_route.py
    と同形)。
    """
    # _generated/ サブフォルダ配下に raw ファイルを直接配置 (worker が生成した想定)
    thread_dir = tmp_path / "unknown" / "t-o1" / "_generated"
    thread_dir.mkdir(parents=True)
    storage_name = "20260512T120000_chart.png"
    payload_bytes = b"\x89PNG\r\n\x1a\nFAKE_PNG_BYTES"
    (thread_dir / storage_name).write_bytes(payload_bytes)

    api_client.cookies.set("session", jwt_cookie)
    resp = await api_client.get(f"/api/threads/t-o1/outputs/{storage_name}")
    assert resp.status_code == 200, resp.text
    assert resp.content == payload_bytes
    # MIME 推定 (mimetypes.guess_type) が image/png を返す想定
    assert "image/png" in resp.headers["content-type"]
    # Content-Disposition: inline; filename="..."
    assert "inline" in resp.headers.get("content-disposition", "")
    assert storage_name in resp.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_path_traversal_rejected(api_client: AsyncClient, jwt_cookie):
    """38-01-03 — `../../../etc/passwd` を URL-encode した name で GET → 400 / 404 / 405 (200 は NG)。

    D-19 smoke 検証: attachments.py の `_safe_resolve_file` が basename 抽出 + realpath
    prefix guard で path traversal を弾く挙動を outputs route が継承していることを確認。
    """
    api_client.cookies.set("session", jwt_cookie)
    name = urllib.parse.quote("../../../etc/passwd", safe="")
    resp = await api_client.get(f"/api/threads/t-o2/outputs/{name}")
    # 400 (basename guard 経由) / 404 (file not found) / 405 (path normalization で route 外)
    # のいずれかで防御。絶対に 200 は返さない。
    assert resp.status_code in (400, 404, 405), resp.text
    assert resp.status_code != 200


@pytest.mark.asyncio
async def test_isolation_other_user_blocked(api_client: AsyncClient, jwt_cookie, tmp_path):
    """38-01-02 — 別 user の _generated/ にアクセス → 404 (FOUT-04 sc5)。

    Phase 36 で確立した `_resolve_thread_folder(github_login, thread_id)` の経路上、
    JWT payload の `github_login` で folder path が組み立てられる。別 user 名の
    folder が存在しても、ログイン user 名が違えば物理パスが別 segment になり 404 になる
    (D-19 — Phase 38 では isolation 単体テストを新規追加しない、helper 再利用が
    唯一の防御経路であることを smoke で確認)。
    """
    # 別 user の thread フォルダにファイルを置く (login が違うのでアクセス不可)
    other_user_dir = tmp_path / "other-user" / "t-o3" / "_generated"
    other_user_dir.mkdir(parents=True)
    storage_name = "20260512T120000_secret.txt"
    (other_user_dir / storage_name).write_bytes(b"secret")

    # jwt_cookie は github_login=None なので unknown/ folder にアクセスする想定
    api_client.cookies.set("session", jwt_cookie)
    # 別 user のフォルダにあるファイルへの GET を試みる
    resp = await api_client.get(f"/api/threads/t-o3/outputs/{storage_name}")
    # 物理的に unknown/t-o3/_generated/ には存在しないので 404 (helper 再利用による
    # path-segment 隔離が効いている証拠)
    assert resp.status_code in (401, 404), resp.text
    assert resp.status_code != 200

    # 認証なし時は 401
    api_client.cookies.clear()
    resp2 = await api_client.get(f"/api/threads/t-o3/outputs/{storage_name}")
    assert resp2.status_code == 401


@pytest.mark.asyncio
async def test_get_output_works_for_claude_code(
    api_client: AsyncClient, jwt_cookie, tmp_path
):
    """38-04-02 — claude_code が _generated/ 配下に出力したファイルも GET で同一経路で取得できる。

    Plan 03 で `claude_code` の cwd を `_generated/` に固定したので、execute_python
    経由のファイルと完全同型 path layout に揃う。本テストは「claude_code 起源を
    模した markdown 出力 (`{ts}_result.md`) を _generated/ 配下に直接配置し、
    outputs route で 200 + bytes 一致 + text/markdown MIME を返す」ことを assert する。
    """
    thread_dir = tmp_path / "unknown" / "t-cc" / "_generated"
    thread_dir.mkdir(parents=True)
    storage_name = "20260512T140000_result.md"
    payload_bytes = (
        b"# claude_code result\n\n"
        b"This file is generated by claude_code into `_generated/`.\n"
    )
    (thread_dir / storage_name).write_bytes(payload_bytes)

    api_client.cookies.set("session", jwt_cookie)
    resp = await api_client.get(f"/api/threads/t-cc/outputs/{storage_name}")
    assert resp.status_code == 200, resp.text
    assert resp.content == payload_bytes
    # markdown は text/markdown または text/* のいずれかで返る
    ct = resp.headers["content-type"]
    assert ct.startswith("text/"), f"unexpected content-type: {ct}"
    # Content-Disposition: inline で配信される (DL ではなくモーダル preview を想定)
    cd = resp.headers.get("content-disposition", "")
    assert "inline" in cd
    assert storage_name in cd
