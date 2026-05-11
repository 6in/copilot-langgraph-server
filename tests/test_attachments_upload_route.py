"""Phase 36 D-03/D-07: POST /api/threads/{tid}/attachments の integration test.

Plan 03 Task 2 RED → GREEN.

固定 jwt_cookie fixture (`tests/conftest.py`) は github_login=None の payload を
含む (CopilotAuthManager の初期 token. Phase 36 では login=未指定 → "unknown" fallback)
ため、folder path は `/tmp_path/unknown/<thread>/` で組み立てられる前提.
"""
import os
import pytest
from httpx import AsyncClient


@pytest.fixture(autouse=True)
def patch_thread_files_dir(tmp_path, monkeypatch):
    """attachments route が見る THREAD_FILES_DIR を test 毎の tmp_path に差し替え。

    Phase 37 既存テスト (tests/test_attachments_list.py) と同じ monkeypatch pattern.
    """
    from app.api.routes import attachments as attachments_module
    monkeypatch.setattr(attachments_module, "THREAD_FILES_DIR", str(tmp_path))
    yield


def _expected_user_folder(tmp_path):
    """jwt_cookie fixture の payload['github_login'] に依存 — fixture が
    `create_jwt("ghu_test_token_for_chat")` を返すため、login claim は欠損 →
    route 内 `payload.get("github_login", "unknown")` で "unknown" に fallback する.
    """
    return os.path.join(str(tmp_path), "unknown")


@pytest.mark.asyncio
async def test_upload_single_text_file(api_client: AsyncClient, jwt_cookie, tmp_path):
    """11 byte text file を upload → 200 + D-14 dict 返却."""
    api_client.cookies.set("session", jwt_cookie)
    resp = await api_client.post(
        "/api/threads/t-1/attachments",
        files={"files": ("hello.txt", b"hello world", "text/plain")},
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert len(payload["attachments"]) == 1
    a = payload["attachments"][0]
    assert a["kind"] == "file"
    assert a["name"] == "hello.txt"
    assert a["size"] == 11
    assert a["ext"] == "txt"
    assert a["mime_type"] == "text/plain"
    # storage_name は YYYYMMDDTHHMMSS_hello.txt 形式
    import re
    assert re.match(r"^\d{8}T\d{6}_hello\.txt$", a["storage_name"]), a["storage_name"]
    # path が tmp_path 配下に実在
    assert os.path.isfile(a["path"])
    with open(a["path"], "rb") as fh:
        assert fh.read() == b"hello world"


@pytest.mark.asyncio
async def test_upload_multiple_files_single_request(api_client: AsyncClient, jwt_cookie):
    """3 ファイル同時 upload → 3 件の dict、順序は送信順."""
    api_client.cookies.set("session", jwt_cookie)
    resp = await api_client.post(
        "/api/threads/t-2/attachments",
        files=[
            ("files", ("a.txt", b"aaa", "text/plain")),
            ("files", ("b.txt", b"bbb", "text/plain")),
            ("files", ("c.md", b"# ccc", "text/markdown")),
        ],
    )
    assert resp.status_code == 200, resp.text
    names = [a["name"] for a in resp.json()["attachments"]]
    assert names == ["a.txt", "b.txt", "c.md"]


@pytest.mark.asyncio
async def test_upload_image_png(api_client: AsyncClient, jwt_cookie):
    """PNG bytes upload → mime_type='image/png', ext='png'."""
    api_client.cookies.set("session", jwt_cookie)
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 100
    resp = await api_client.post(
        "/api/threads/t-3/attachments",
        files={"files": ("sample.png", png, "image/png")},
    )
    assert resp.status_code == 200, resp.text
    a = resp.json()["attachments"][0]
    assert a["ext"] == "png"
    assert a["mime_type"] == "image/png"


@pytest.mark.asyncio
async def test_upload_exceeds_size_limit_returns_413(
    api_client: AsyncClient, jwt_cookie, monkeypatch, tmp_path,
):
    """サイズ超過 (10KB cap で 11KB 送信) → 413, 部分書き込みファイルが残らない."""
    from app.api.routes import attachments as attachments_module
    # 10KB 上限に縮める (テスト高速化)
    monkeypatch.setattr(attachments_module, "MAX_FILE_BYTES", 10 * 1024)
    monkeypatch.setattr(attachments_module, "IMAGE_MAX_BYTES", 10 * 1024)

    api_client.cookies.set("session", jwt_cookie)
    big = b"X" * (11 * 1024)
    resp = await api_client.post(
        "/api/threads/t-4/attachments",
        files={"files": ("big.txt", big, "text/plain")},
    )
    assert resp.status_code == 413, resp.text

    # 部分書き込みファイルが残っていないこと
    folder = os.path.join(_expected_user_folder(tmp_path), "t-4")
    if os.path.isdir(folder):
        # フォルダは作られていてもよいが、中に file があってはならない
        files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
        assert files == [], f"partial-write file leaked: {files}"


@pytest.mark.asyncio
async def test_upload_path_traversal_filename_rejected(api_client: AsyncClient, jwt_cookie):
    """filename に path separator が含まれた場合 → basename 化後に 200 + 平坦化された name で保存。

    `foo/bar.txt` → basename="bar.txt" として保存される (絶対に `/foo/bar.txt`
    にはならない). 保存後 path は thread folder 配下であること.
    """
    api_client.cookies.set("session", jwt_cookie)
    resp = await api_client.post(
        "/api/threads/t-5/attachments",
        files={"files": ("foo/bar.txt", b"x", "text/plain")},
    )
    assert resp.status_code == 200, resp.text
    a = resp.json()["attachments"][0]
    assert a["name"] == "bar.txt"
    assert "../" not in a["path"]
    assert "/foo/" not in a["path"]


@pytest.mark.asyncio
async def test_upload_requires_auth(api_client: AsyncClient):
    """cookie なし → 401."""
    # api_client fixture が共有のため、ここで cookie を確実にクリア
    api_client.cookies.clear()
    resp = await api_client.post(
        "/api/threads/t-6/attachments",
        files={"files": ("a.txt", b"a", "text/plain")},
    )
    assert resp.status_code == 401, resp.text


@pytest.mark.asyncio
async def test_upload_creates_thread_folder_if_missing(
    api_client: AsyncClient, jwt_cookie, tmp_path,
):
    """初回 upload で thread folder が自動生成 (os.makedirs(exist_ok=True))."""
    api_client.cookies.set("session", jwt_cookie)
    resp = await api_client.post(
        "/api/threads/t-7/attachments",
        files={"files": ("x.txt", b"x", "text/plain")},
    )
    assert resp.status_code == 200, resp.text
    folder = os.path.join(_expected_user_folder(tmp_path), "t-7")
    assert os.path.isdir(folder)


@pytest.mark.asyncio
async def test_upload_filename_with_japanese_chars(api_client: AsyncClient, jwt_cookie):
    """日本語 filename も保存できる (NFC 正規化はオプショナル)."""
    api_client.cookies.set("session", jwt_cookie)
    resp = await api_client.post(
        "/api/threads/t-8/attachments",
        files={"files": ("日本語ファイル.txt", b"ok", "text/plain")},
    )
    assert resp.status_code == 200, resp.text
    a = resp.json()["attachments"][0]
    assert "日本語ファイル" in a["name"]
