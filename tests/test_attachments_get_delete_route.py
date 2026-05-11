"""Phase 36 D-07/D-23: GET/DELETE /api/threads/{tid}/attachments/{name}.

Plan 03 Task 3 RED → GREEN.

GET = inline raw bytes (FileResponse + Content-Disposition: inline)
DELETE = single file remove, idempotent (204), realpath guard

固定 jwt_cookie fixture (`tests/conftest.py`) は github_login=None の payload を
含むため、folder path は `/tmp_path/unknown/<thread>/` で組み立てられる前提.
"""
import os
import pytest
from httpx import AsyncClient


@pytest.fixture(autouse=True)
def patch_thread_files_dir(tmp_path, monkeypatch):
    from app.api.routes import attachments as attachments_module
    monkeypatch.setattr(attachments_module, "THREAD_FILES_DIR", str(tmp_path))
    yield


async def _upload(api_client: AsyncClient, jwt_cookie, tid: str, filename: str, data: bytes, mime: str) -> dict:
    api_client.cookies.set("session", jwt_cookie)
    resp = await api_client.post(
        f"/api/threads/{tid}/attachments",
        files={"files": (filename, data, mime)},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["attachments"][0]


# -------- GET raw --------

@pytest.mark.asyncio
async def test_get_attachment_returns_raw_bytes(api_client: AsyncClient, jwt_cookie):
    a = await _upload(api_client, jwt_cookie, "t-g1", "sample.txt", b"hello 36", "text/plain")
    resp = await api_client.get(f"/api/threads/t-g1/attachments/{a['storage_name']}")
    assert resp.status_code == 200, resp.text
    assert resp.content == b"hello 36"
    assert "text/plain" in resp.headers["content-type"]
    assert "inline" in resp.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_get_attachment_404_when_missing(api_client: AsyncClient, jwt_cookie):
    api_client.cookies.set("session", jwt_cookie)
    resp = await api_client.get("/api/threads/t-g2/attachments/nope_20260423T120000.txt")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_attachment_requires_auth(api_client: AsyncClient):
    api_client.cookies.clear()
    resp = await api_client.get("/api/threads/t-g3/attachments/x.txt")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_attachment_path_traversal_rejected(api_client: AsyncClient, jwt_cookie):
    api_client.cookies.set("session", jwt_cookie)
    # URL-encoded `../` を含む name
    import urllib.parse as up
    name = up.quote("../../../etc/passwd", safe="")
    resp = await api_client.get(f"/api/threads/t-g4/attachments/{name}")
    # 400 path traversal or 404 file not found のどちらかで、絶対に 200 じゃない
    assert resp.status_code in (400, 404), resp.text


# -------- DELETE single file --------

@pytest.mark.asyncio
async def test_delete_attachment_removes_file(api_client: AsyncClient, jwt_cookie):
    a = await _upload(api_client, jwt_cookie, "t-d1", "target.txt", b"x", "text/plain")
    assert os.path.isfile(a["path"])
    resp = await api_client.delete(f"/api/threads/t-d1/attachments/{a['storage_name']}")
    assert resp.status_code == 204, resp.text
    assert not os.path.isfile(a["path"])


@pytest.mark.asyncio
async def test_delete_attachment_missing_returns_204(api_client: AsyncClient, jwt_cookie):
    """idempotent: 存在しない name で DELETE → 204."""
    api_client.cookies.set("session", jwt_cookie)
    resp = await api_client.delete("/api/threads/t-d2/attachments/ghost.txt")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_attachment_path_traversal_rejected(api_client: AsyncClient, jwt_cookie):
    """`..%2Fx.txt` は Starlette path normalization で `../x.txt` に展開され
    別 route に外れる (405) — DELETE は実行されない. または basename guard で 400.
    どちらでも「path traversal による削除」は防げているので 200 だけは絶対に返さない.
    """
    import urllib.parse as up
    api_client.cookies.set("session", jwt_cookie)
    name = up.quote("../x.txt", safe="")
    resp = await api_client.delete(f"/api/threads/t-d3/attachments/{name}")
    # 200/204 (削除成功) は絶対 NG; 400 (basename guard) / 404 (not found) /
    # 405 (path normalization で route 外) のいずれかで防御
    assert resp.status_code in (400, 404, 405), resp.text
    assert resp.status_code not in (200, 204)


@pytest.mark.asyncio
async def test_delete_attachment_requires_auth(api_client: AsyncClient):
    api_client.cookies.clear()
    resp = await api_client.delete("/api/threads/t-d4/attachments/x.txt")
    assert resp.status_code == 401
