---
phase: 37
plan: 04
type: execute
wave: 2
depends_on: ["37-02", "37-03"]
files_modified:
  - app/jobs/handlers/langgraph_handler.py
  - app/api/routes/chat.py
  - tests/test_api_chat.py
  - tests/test_langgraph_handler_attachments.py
  - .planning/phases/37-pdf-office-mcp/37-VALIDATION.md
autonomous: true
requirements: [FIN-03, FIN-04]
estimated_minutes: 75
tags: [handler, system-prompt, delete-hook, langgraph]

must_haves:
  truths:
    - "LangGraphHandler が thread フォルダを scan し、添付一覧を SystemMessage に prepend する (D-11)"
    - "AgentState.attachments フィールドが毎 turn の state_input に含まれる (D-12)"
    - "DELETE /api/threads/{id} が adelete_thread 直後に shutil.rmtree でフォルダを消す (D-03)"
    - "shutil.rmtree 呼び出し前に realpath prefix assert でパストラバーサルを遮断する (W-01: SHOULD → MUST)"
    - "フォルダが存在しない thread の削除でもエラーを起こさない (ignore_errors=True)"
    - "handler には shutil を import していない (W-05: scan 側は listdir/stat のみ)"
    - "Wave 0 で置いた test_delete_thread_removes_folder の xfail が外れて passed になる"
  artifacts:
    - path: "app/jobs/handlers/langgraph_handler.py"
      provides: "_scan_thread_attachments + _build_attachments_hint + system_prompt prepend ロジック"
      contains: "_scan_thread_attachments"
    - path: "app/api/routes/chat.py"
      provides: "delete_thread 関数での shutil.rmtree hook + realpath prefix assert"
      contains: "shutil.rmtree"
    - path: "tests/test_langgraph_handler_attachments.py"
      provides: "scan + SystemMessage prepend の unit test"
      contains: "def test_scan"
  key_links:
    - from: "app/jobs/handlers/langgraph_handler.py"
      to: "/shared/thread-files/<login>/<thread_id>/"
      via: "os.listdir + os.stat (scan only, no write)"
      pattern: "THREAD_FILES_DIR"
    - from: "app/api/routes/chat.py::delete_thread"
      to: "shutil.rmtree(thread_folder, ignore_errors=True)"
      via: "adelete_thread 直後の hook + realpath prefix guard"
      pattern: "shutil\\.rmtree.*ignore_errors=True"
    - from: "app/api/routes/chat.py::delete_thread"
      to: "os.path.realpath(thread_folder)"
      via: "traversal 防御のため rmtree 前に必ず prefix assert"
      pattern: "realpath"
    - from: "effective_system_prompt"
      to: "添付一覧 + hint 文字列"
      via: "attachments_hint を末尾に連結"
      pattern: "attachments_hint|添付ファイル"
---

<objective>
Plan 03 で整えた MCP ツール基盤を、worker handler と api ルートに実地で組み込む。
(1) worker LangGraphHandler が毎 turn に thread フォルダを scan し、一覧メタデータを
    SystemMessage に prepend する (D-11)。AgentState.attachments にも同じ一覧をセットする (D-12)。
(2) api delete_thread が adelete_thread 直後に `shutil.rmtree(thread_folder, ignore_errors=True)` を
    呼んで thread 削除と folder 削除を同期させる (D-03)。rmtree 前には必ず realpath prefix assert で
    パストラバーサル攻撃を遮断する (W-01: SHOULD → MUST)。

Purpose: ユーザーが thread フォルダに事前配置したファイルを、AI が scan と extract の両面から
         自然に使える体験に接続する
Output: handler の prepend ロジック + delete_thread hook + 対応する unit test 追加
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/37-pdf-office-mcp/37-CONTEXT.md
@.planning/phases/37-pdf-office-mcp/37-RESEARCH.md
@.planning/phases/37-pdf-office-mcp/37-PATTERNS.md
@.planning/phases/37-pdf-office-mcp/37-VALIDATION.md
@.planning/phases/37-pdf-office-mcp/37-02-SUMMARY.md
@.planning/phases/37-pdf-office-mcp/37-03-SUMMARY.md
@docs/adr/0025-datetime-and-user-context-injection-into-agent-prompts.md
@docs/adr/0026-thread-deletion-also-removes-threads-table-row.md

<interfaces>
<!-- LangGraphHandler の effective_system_prompt 構築 (既存) -->
From app/jobs/handlers/langgraph_handler.py L118-144:
```python
# 現在のシステムプロンプト構築 (L126-134):
datetime_prefix = get_datetime_context()
effective_system_prompt = datetime_prefix + "\n\n" + (system_prompt or "") + AUQ_PROTOCOL
config = {
    "configurable": {
        "thread_id": thread_id,
        "github_login": github_login,
        "system_prompt": effective_system_prompt,
    }
}

# HumanMessage のみ state に追加 (L139):
messages_input: list = [HumanMessage(content=prompt)]
state_input = {"messages": messages_input}
```

<!-- delete_thread の現在の実装 (L345-385) -->
From app/api/routes/chat.py L380-385:
```python
checkpointer = request.app.state.checkpointer
try:
    await checkpointer.adelete_thread(thread_id)
except Exception:
    # Silently succeed if thread doesn't exist
    pass
```

<!-- AgentState (Plan 02 で attachments フィールド追加済み) -->
From app/orchestrator/state.py:
```python
class AgentState(TypedDict):
    ...
    context_messages: list[dict] | None
    attachments: list[dict] | None   # Phase 37 Plan 02 で追加
```

<!-- 既存 test fixture (tests/test_api_chat.py `test_delete_thread_calls_adelete`) -->
From tests/test_api_chat.py (既存):
```python
@pytest.fixture
def api_client(monkeypatch):
    # JWT cookie 注入 + AsyncMock checkpointer を request.app.state に差し込む TestClient fixture
    ...

@pytest.mark.asyncio
async def test_delete_thread_calls_adelete(api_client):
    # Example: api_client.delete("/api/threads/test-thread-123") → 204
    # AsyncMock checkpointer の adelete_thread が呼ばれたか assert
    ...
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: LangGraphHandler に thread フォルダ scan + SystemMessage prepend + AgentState.attachments 注入を追加</name>
  <files>app/jobs/handlers/langgraph_handler.py, tests/test_langgraph_handler_attachments.py</files>
  <read_first>
    - app/jobs/handlers/langgraph_handler.py (全ファイル 1-220 行)
    - .planning/phases/37-pdf-office-mcp/37-PATTERNS.md `app/jobs/handlers/langgraph_handler.py (変更)` セクション
    - .planning/phases/37-pdf-office-mcp/37-CONTEXT.md D-11 / D-12
    - .planning/phases/37-pdf-office-mcp/37-RESEARCH.md Pattern 5 (SystemMessage prepend)
    - docs/adr/0025-datetime-and-user-context-injection-into-agent-prompts.md (既存 SystemMessage 注入パターン)
    - .planning/patterns.md `エージェントプロンプトへの日時・ユーザー自動注入` (ADR-0025)
  </read_first>
  <action>
  **(A) ファイル冒頭 import / 定数の追加** (既存 L1-20 付近):

  既存 import セクション確認 — `os` は既に import されているはず。
  **W-05 対応:** handler 側で `shutil` は不要 (scan のみで書き込みしない)。`import shutil` を追加しない。

  `DB_URI = ...` の定義 (L19) の直後に定数を追加:
  ```python
  # Phase 37 D-01/D-04: thread フォルダの base path。api/worker/mcp-server で共通。
  THREAD_FILES_DIR: str = os.environ.get("THREAD_FILES_DIR", "/shared/thread-files")
  ```

  **(B) ファイル上部にヘルパー関数を 2 本追加** (`extract_html` の近く、クラス定義の前):

  ```python
  def _scan_thread_attachments(thread_id: str, github_login: str) -> list[dict]:
      """thread フォルダを scan してメタデータ一覧を返す (Phase 37 D-11/D-12)。

      worker は RO mount (docker-compose.yml) のため scan のみ。
      フォルダ不在 / 権限エラー / 空フォルダはすべて [] として扱う。
      """
      if not thread_id or not github_login:
          return []
      folder = os.path.join(THREAD_FILES_DIR, github_login, thread_id)
      if not os.path.isdir(folder):
          return []
      result: list[dict] = []
      try:
          names = sorted(os.listdir(folder))
      except OSError:
          return []
      for fname in names:
          fpath = os.path.join(folder, fname)
          if not os.path.isfile(fpath):
              continue
          try:
              stat = os.stat(fpath)
          except OSError:
              continue
          ext = os.path.splitext(fname)[1].lower()
          result.append({
              "name": fname,
              "size": stat.st_size,
              "modified_at": float(stat.st_mtime),  # S-03: float epoch seconds
              "ext": ext,
          })
      return result


  def _build_attachments_hint(attachments: list[dict]) -> str:
      """scan 結果を LLM 向けの hint 文字列に整形する (D-11)。

      内容本体は含めず、ファイル名・サイズ・拡張子・"ツール呼べ" の指示のみ。
      """
      if not attachments:
          return ""
      lines: list[str] = []
      for a in attachments:
          size_kb = a["size"] / 1024
          size_str = f"{size_kb:.1f}KB" if size_kb < 1024 else f"{size_kb / 1024:.2f}MB"
          lines.append(f"- {a['name']} ({size_str}, {a['ext']})")
      body = "\n".join(lines)
      return (
          body
          + "\n\n"
          + "内容を読むには `attachments_extract` ツール (引数: filename) を、"
          + "一覧を再取得するには `attachments_list` ツールを使うこと。"
      )
  ```

  **(C) `_handle_inner` 内の effective_system_prompt 構築 + state_input を改修**

  現在 (L126-134 + L144):
  ```python
  datetime_prefix = get_datetime_context()
  effective_system_prompt = datetime_prefix + "\n\n" + (system_prompt or "") + AUQ_PROTOCOL
  config = {
      "configurable": {
          "thread_id": thread_id,
          "github_login": github_login,
          "system_prompt": effective_system_prompt,
      }
  }
  ...
  state_input = {"messages": messages_input}
  ```

  変更後:
  ```python
  datetime_prefix = get_datetime_context()

  # Phase 37 D-11/D-12: thread フォルダを scan し、メタデータ一覧を SystemMessage に prepend する
  attachments_meta = _scan_thread_attachments(thread_id, github_login)
  attachments_hint = _build_attachments_hint(attachments_meta)

  if attachments_hint:
      effective_system_prompt = (
          datetime_prefix + "\n\n"
          + (system_prompt or "")
          + AUQ_PROTOCOL
          + "\n\n## 添付ファイル\n"
          + attachments_hint
      )
  else:
      effective_system_prompt = datetime_prefix + "\n\n" + (system_prompt or "") + AUQ_PROTOCOL

  config = {
      "configurable": {
          "thread_id": thread_id,
          "github_login": github_login,
          "system_prompt": effective_system_prompt,
      }
  }

  # ... (既存コード) ...

  # Phase 37 D-12: state に attachments メタデータを持たせる (last-wins reducer なし)
  state_input = {"messages": messages_input, "attachments": attachments_meta or None}
  ```

  **(D) 新規 test ファイル: tests/test_langgraph_handler_attachments.py**

  ```python
  """Phase 37: LangGraphHandler の thread フォルダ scan + SystemMessage prepend の unit test."""
  from __future__ import annotations

  import os
  import pytest


  def test_scan_returns_sorted_metadata(tmp_path, monkeypatch):
      """_scan_thread_attachments が name/size/modified_at/ext を返す。"""
      from app.jobs.handlers import langgraph_handler
      folder = tmp_path / "user-a" / "t-1"
      folder.mkdir(parents=True)
      (folder / "20260421T120000_report.pdf").write_bytes(b"x" * 100)
      (folder / "20260421T120500_data.xlsx").write_bytes(b"y" * 200)
      monkeypatch.setattr(langgraph_handler, "THREAD_FILES_DIR", str(tmp_path))

      result = langgraph_handler._scan_thread_attachments("t-1", "user-a")
      assert len(result) == 2
      names = [r["name"] for r in result]
      assert names == sorted(names)   # 時系列 prefix により sorted と一致
      assert result[0]["size"] == 100
      assert result[0]["ext"] == ".pdf"
      # S-03: modified_at は float (epoch seconds)
      assert isinstance(result[0]["modified_at"], float)


  def test_scan_empty_folder(tmp_path, monkeypatch):
      """フォルダ不在時は [] を返す。"""
      from app.jobs.handlers import langgraph_handler
      monkeypatch.setattr(langgraph_handler, "THREAD_FILES_DIR", str(tmp_path))
      assert langgraph_handler._scan_thread_attachments("nope", "nope") == []


  def test_scan_missing_context(monkeypatch):
      """thread_id/github_login が空文字の場合は即 []。"""
      from app.jobs.handlers import langgraph_handler
      assert langgraph_handler._scan_thread_attachments("", "user") == []
      assert langgraph_handler._scan_thread_attachments("t", "") == []


  def test_build_hint_empty():
      from app.jobs.handlers import langgraph_handler
      assert langgraph_handler._build_attachments_hint([]) == ""


  def test_build_hint_contains_filename_and_tool_instruction():
      from app.jobs.handlers import langgraph_handler
      meta = [{"name": "report.pdf", "size": 1500, "modified_at": 0.0, "ext": ".pdf"}]
      hint = langgraph_handler._build_attachments_hint(meta)
      assert "report.pdf" in hint
      assert "attachments_extract" in hint
      assert "attachments_list" in hint
  ```
  </action>
  <verify>
    <automated>grep -q "_scan_thread_attachments" app/jobs/handlers/langgraph_handler.py && grep -q "_build_attachments_hint" app/jobs/handlers/langgraph_handler.py && grep -q "THREAD_FILES_DIR" app/jobs/handlers/langgraph_handler.py && grep -q "attachments_hint" app/jobs/handlers/langgraph_handler.py && grep -q '"attachments":' app/jobs/handlers/langgraph_handler.py && test "$(grep -c '^import shutil' app/jobs/handlers/langgraph_handler.py)" -eq 0 && uv run pytest tests/test_langgraph_handler_attachments.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep "_scan_thread_attachments" app/jobs/handlers/langgraph_handler.py` で 2 行以上 (定義 + 呼び出し)
    - `grep "_build_attachments_hint" app/jobs/handlers/langgraph_handler.py` で 2 行以上
    - `grep "THREAD_FILES_DIR" app/jobs/handlers/langgraph_handler.py` で 2 行以上 (定数定義 + helper 内使用)
    - `grep "## 添付ファイル" app/jobs/handlers/langgraph_handler.py` で 1 行マッチ
    - `grep '"attachments": attachments_meta' app/jobs/handlers/langgraph_handler.py` で 1 行マッチ
    - **W-05 対応:** `grep -c "^import shutil" app/jobs/handlers/langgraph_handler.py` が **0** (handler は scan のみで shutil 不要)
    - `uv run pytest tests/test_langgraph_handler_attachments.py -v` で 5 件全 passed
    - 既存テスト `uv run pytest tests/test_api_chat.py -x -q` が引き続き passed (regression なし)
  </acceptance_criteria>
  <done>worker handler が thread フォルダ scan を毎 turn 実行し、LLM に hint を送り届ける</done>
</task>

<task type="auto">
  <name>Task 2: delete_thread に shutil.rmtree hook + realpath prefix assert を追加し、Wave 0 xfail test を GREEN にする</name>
  <files>app/api/routes/chat.py, tests/test_api_chat.py</files>
  <read_first>
    - **tests/test_api_chat.py 全体 (既存 test_delete_thread_calls_adelete の fixture 構成をコピーする)**
    - app/api/routes/chat.py L1-50 (既存 import) + L345-395 (delete_thread 全体)
    - .planning/phases/37-pdf-office-mcp/37-PATTERNS.md `app/api/routes/chat.py (変更 — delete_thread フック)` セクション
    - .planning/phases/37-pdf-office-mcp/37-CONTEXT.md D-03 / D-18
    - docs/adr/0026-thread-deletion-also-removes-threads-table-row.md (削除の原子性思想)
  </read_first>
  <action>
  **(A) app/api/routes/chat.py の冒頭 import に `shutil` と `os` を追加** (`os` は通常既に import されているはず)

  **(B) ファイル冒頭 (import セクションの直下) に定数追加:**
  ```python
  # Phase 37 D-01/D-03/D-04: thread フォルダ base path。api:RW mount で削除可能。
  THREAD_FILES_DIR = os.environ.get("THREAD_FILES_DIR", "/shared/thread-files")
  ```

  **(C) delete_thread 関数 (L345-385) の `adelete_thread` 直後に rmtree hook + realpath guard を追加**

  既存 L380-385:
  ```python
  checkpointer = request.app.state.checkpointer
  try:
      await checkpointer.adelete_thread(thread_id)
  except Exception:
      # Silently succeed if thread doesn't exist
      pass
  ```

  これを以下に変更 (**W-01 対応: realpath prefix assert を MUST として常時実行**):
  ```python
  checkpointer = request.app.state.checkpointer
  try:
      await checkpointer.adelete_thread(thread_id)
  except Exception:
      # Silently succeed if thread doesn't exist
      pass

  # Phase 37 D-03 + D-18 W-01: thread フォルダを同期削除 (RW mount, api container)。
  # パストラバーサルを遮断するため必ず realpath prefix assert を通す。
  thread_folder = os.path.join(THREAD_FILES_DIR, github_login, thread_id)
  try:
      real_folder = os.path.realpath(thread_folder)
      root = os.path.realpath(THREAD_FILES_DIR)
      if not real_folder.startswith(root + os.sep):
          # path traversal 検出: github_login / thread_id に `..` 等が混入した場合
          # 204 は返すが削除はしない
          raise ValueError(f"path traversal attempt: {thread_folder}")
      shutil.rmtree(real_folder, ignore_errors=True)
  except ValueError:
      pass   # traversal 検出 — ログだけ残して無視 (thread の論理削除は既に完了)
  except Exception:
      pass   # 予期せぬエラーも握り潰す
  ```

  `github_login` は L354 (`github_login = payload.get("github_login", "")`) で取得済み。

  **(D) tests/test_api_chat.py の `test_delete_thread_removes_folder` xfail を外して本実装**

  **B-05 対応: 既存 `test_delete_thread_calls_adelete` の fixture 構成を具体コードとして展開する。**
  以下は tests/test_api_chat.py に既存する fixture パターンを明示的にコピーした実装例。
  実ファイルで既存 fixture の命名と微差があれば合わせて調整すること。

  ```python
  import shutil
  from unittest.mock import patch, AsyncMock, MagicMock
  import pytest
  from fastapi.testclient import TestClient


  @pytest.mark.asyncio
  async def test_delete_thread_removes_folder(monkeypatch):
      """FIN-04 SC-5 / D-03: DELETE /api/threads/{id} が shutil.rmtree を呼ぶ。

      フォルダが存在しない thread を削除しても 204 を返す (ignore_errors=True)。
      既存 test_delete_thread_calls_adelete と同じ AsyncMock checkpointer / TestClient / JWT
      cookie の fixture 構成を本関数内にインライン展開する。
      """
      # --- fixture setup (既存 test_delete_thread_calls_adelete と同構造) ---
      from app.api.main import create_app

      app = create_app()

      # AsyncMock checkpointer を差し込む
      mock_checkpointer = AsyncMock()
      mock_checkpointer.adelete_thread = AsyncMock(return_value=None)
      app.state.checkpointer = mock_checkpointer

      # DB ownership チェックを通過させるため、threads テーブル行が所有者として存在する fixture を
      # 既存 test で使っている mock DB 層に差し込む (同テストで使われている pg mock があればそれを使う)
      # 簡略化のため ownership 検査を monkeypatch で bypass:
      # monkeypatch で threads テーブル所有者確認関数を常に True にする (既存 test がやっている箇所に合わせる)
      monkeypatch.setattr("app.api.routes.chat.check_thread_owner",
                          lambda *a, **kw: True, raising=False)

      # JWT cookie を含む TestClient
      client = TestClient(app)
      # 既存 test が使う jwt payload (github_login, jti, exp) を encode して cookie にセット
      from app.auth.jwt_utils import encode_jwt
      token = encode_jwt({"github_login": "testuser", "jti": "jti-1"})
      client.cookies.set("access_token", token)

      # --- patch shutil.rmtree (app.api.routes.chat の名前空間で patch) ---
      with patch("app.api.routes.chat.shutil.rmtree") as mock_rm:
          resp = client.delete("/api/threads/test-thread-123")

      assert resp.status_code == 204
      # rmtree が 1 回呼ばれた (フォルダ不在でも ignore_errors=True で吸収)
      mock_rm.assert_called_once()
      # 第 1 引数が /shared/thread-files/testuser/test-thread-123 の prefix を持つ (realpath 解決後でも同じ)
      call_args = mock_rm.call_args
      called_path = call_args.args[0] if call_args.args else call_args.kwargs.get("path", "")
      assert "testuser" in called_path
      assert "test-thread-123" in called_path
      # ignore_errors=True が kwargs に含まれる
      assert call_args.kwargs.get("ignore_errors") is True


  @pytest.mark.asyncio
  async def test_delete_thread_rejects_path_traversal(monkeypatch):
      """W-01: thread_id / github_login に `..` が混入しても rmtree が実行されず 204 を返す。"""
      from app.api.main import create_app

      app = create_app()
      mock_checkpointer = AsyncMock()
      mock_checkpointer.adelete_thread = AsyncMock(return_value=None)
      app.state.checkpointer = mock_checkpointer
      monkeypatch.setattr("app.api.routes.chat.check_thread_owner",
                          lambda *a, **kw: True, raising=False)

      client = TestClient(app)
      from app.auth.jwt_utils import encode_jwt
      token = encode_jwt({"github_login": "../../etc", "jti": "jti-t"})
      client.cookies.set("access_token", token)

      with patch("app.api.routes.chat.shutil.rmtree") as mock_rm:
          resp = client.delete("/api/threads/malicious")

      assert resp.status_code == 204
      # realpath prefix assert が失敗 → rmtree は呼ばれない
      mock_rm.assert_not_called()
  ```

  **注意:**
  - `check_thread_owner` / `encode_jwt` / `create_app` の正確な symbol 名は本リポジトリの既存 test と一致させること。
    異なる場合は既存 `test_delete_thread_calls_adelete` のコピーをベースにして名前を直す。
  - `shutil.rmtree` の patch scope は `app.api.routes.chat.shutil.rmtree` として指定する
    (patch target は import された場所で行う必要がある)。
  - `test_delete_thread_rejects_path_traversal` は W-01 の MUST 化を validate する最小検証。
    `mock_rm.assert_not_called()` が MUST。
  </action>
  <verify>
    <automated>grep -q "shutil.rmtree" app/api/routes/chat.py && grep -q "THREAD_FILES_DIR" app/api/routes/chat.py && grep -q "ignore_errors=True" app/api/routes/chat.py && grep -q "realpath" app/api/routes/chat.py && grep -qE "startswith\(root \+ os\.sep\)|startswith\(.*THREAD_FILES_DIR" app/api/routes/chat.py && ! grep -q "xfail.*delete_thread_removes_folder" tests/test_api_chat.py && uv run pytest tests/test_api_chat.py::test_delete_thread_removes_folder tests/test_api_chat.py::test_delete_thread_rejects_path_traversal -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep "shutil.rmtree" app/api/routes/chat.py` で 1 件以上
    - `grep "ignore_errors=True" app/api/routes/chat.py` で 1 件以上
    - `grep "THREAD_FILES_DIR" app/api/routes/chat.py` で 2 件以上 (定数定義 + 使用)
    - `grep -c "import shutil\|^import shutil\|, shutil$" app/api/routes/chat.py` が 1 以上
    - **W-01 MUST 化:** `grep "realpath" app/api/routes/chat.py` で 2 件以上 (thread_folder + THREAD_FILES_DIR の両方 realpath)
    - **W-01 MUST 化:** `grep -E "startswith.*os\.sep" app/api/routes/chat.py` で 1 件以上
    - tests/test_api_chat.py に `test_delete_thread_removes_folder` が残り、xfail decorator が **除去** されている
    - tests/test_api_chat.py に `test_delete_thread_rejects_path_traversal` が新規追加されている
    - `uv run pytest tests/test_api_chat.py::test_delete_thread_removes_folder -v` が passed
    - `uv run pytest tests/test_api_chat.py::test_delete_thread_rejects_path_traversal -v` が passed
    - `uv run pytest tests/test_api_chat.py -x -q` (既存 test 全体) が passed (regression なし)
    - delete_thread 関数の実装が adelete_thread → realpath check → shutil.rmtree の順序で書かれている
  </acceptance_criteria>
  <done>delete_thread が論理削除 + realpath gate + 物理削除の 3 ステップを同期実行し、Wave 0 の xfail が GREEN になる</done>
</task>

<task type="auto">
  <name>Task 3: VALIDATION.md Per-Task Map に Wave 2 (37-04-XX) 行を追記 (B-07 段階更新 3 回目)</name>
  <files>.planning/phases/37-pdf-office-mcp/37-VALIDATION.md</files>
  <read_first>
    - .planning/phases/37-pdf-office-mcp/37-VALIDATION.md (Plan 02/03 で追記された状態)
    - 本 Plan Task 1-2 の `<verify>` / `<acceptance_criteria>`
  </read_first>
  <action>
  VALIDATION.md の Per-Task Verification Map テーブル末尾に、本 Plan の Task 1-2 に対応する行を追記する:

  ```markdown
  | 37-04-01 | 04 | 2 | FIN-03 | T-37-04-04 | scan metadata | unit | `uv run pytest tests/test_langgraph_handler_attachments.py -x` | ✅ | ⬜ pending |
  | 37-04-02 | 04 | 2 | FIN-04 | T-37-04-01 | delete folder hook | unit | `uv run pytest tests/test_api_chat.py::test_delete_thread_removes_folder -x` | ✅ | ⬜ pending |
  | 37-04-03 | 04 | 2 | FIN-04 | T-37-04-01 | path traversal guard (W-01 MUST) | unit | `uv run pytest tests/test_api_chat.py::test_delete_thread_rejects_path_traversal -x` | ✅ | ⬜ pending |
  ```
  </action>
  <verify>
    <automated>grep -c "^| 37-04-" .planning/phases/37-pdf-office-mcp/37-VALIDATION.md | awk '{if ($1 >= 3) exit 0; else exit 1}'</automated>
  </verify>
  <acceptance_criteria>
    - VALIDATION.md の Per-Task Verification Map に `37-04-` で始まる行が 3 件以上
    - 37-04-03 (path traversal guard) 行が存在する (W-01 の MUST 化が追跡可能)
  </acceptance_criteria>
  <done>Plan 04 分の Per-Task Map が VALIDATION.md に追記され、Plan 05 で最終 sign-off ができる状態になる</done>
</task>

</tasks>

<threat_model>

## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| JWT (github_login) → DELETE /api/threads/{id} | ユーザーが他ユーザーの thread を削除する経路 |
| worker (RO mount) → thread フォルダ | RO なので write 攻撃経路はない |
| api コンテナ (RW mount) → `shutil.rmtree` | rmtree でサーバー側の任意パスを消せる可能性 |
| LangGraph checkpoint 復元 → attachments フィールド | stale データが注入される懸念 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-37-04-01 | Tampering / Elevation | `shutil.rmtree(thread_folder)` で `thread_id = "../../../"` を渡されて他 thread / システムパスを消される | **mitigate (HIGH, MUST)** | **W-01 対応で SHOULD → MUST に格上げ。** `thread_folder = os.path.join(THREAD_FILES_DIR, github_login, thread_id)` の直後に `os.path.realpath(thread_folder).startswith(os.path.realpath(THREAD_FILES_DIR) + os.sep)` assertion を **必ず実行**。失敗時は rmtree を skip (204 は返す)。Task 2 acceptance_criteria + test_delete_thread_rejects_path_traversal で検証 |
| T-37-04-02 | Information Disclosure | ユーザー A のフォルダをユーザー B が削除する | mitigate | 既存の `SELECT github_login FROM threads WHERE thread_id = %s` 所有権検証 (L361-367) + `DELETE FROM threads WHERE thread_id = %s AND github_login = %s` で保護済み。本 Plan は既存防御の下流で動く |
| T-37-04-03 | Information Disclosure | LangGraph checkpoint から復元された stale `attachments` がフレッシュ scan を汚染する | accept (LOW) | reducer なし = last-writer-wins。handler が毎 turn scan で上書きするため stale は即座に置換される |
| T-37-04-04 | DoS | 巨大なフォルダ (数万ファイル) の scan で毎 turn I/O が重くなる | accept (LOW) | 200 名規模 + on-demand 抽出設計。scan は `os.listdir` のみで O(n)。100 ファイルでも ms オーダー |
| T-37-04-05 | Tampering | worker が RO mount で rmtree を呼ぼうとすると PermissionError | mitigate | rmtree は api container のみ実装。worker の handler は scan のみ (listdir/stat = read-only)。W-05 で handler の `import shutil` 禁止を acceptance に追加済み |

</threat_model>

<verification>
- `uv run pytest tests/test_langgraph_handler_attachments.py -v` が全 passed
- `uv run pytest tests/test_api_chat.py -v` が全 passed (test_delete_thread_removes_folder + test_delete_thread_rejects_path_traversal 含む)
- `grep "## 添付ファイル" app/jobs/handlers/langgraph_handler.py` で hint テンプレートが存在
- `grep "shutil.rmtree.*ignore_errors" app/api/routes/chat.py` でマッチ
- `grep "realpath" app/api/routes/chat.py` で 2 件以上 (W-01 MUST 化)
- 既存 `tests/test_agent_state.py::test_attachments_field_accepted` が引き続き passed
- `grep -c "^import shutil" app/jobs/handlers/langgraph_handler.py` が 0 (W-05)
- VALIDATION.md に `^| 37-04-` 行が 3 件以上追記されている
</verification>

<success_criteria>
- thread フォルダに配置したファイルが自動的に SystemMessage に hint として出現する
- thread 削除時にフォルダが同期削除される (realpath guard 経由)
- handler には shutil が import されていない (scan only / W-05)
- Wave 0 で設定したテストスケルトンがすべて GREEN (`test_attachments_extract.py` + `test_attachments_list.py` + `test_delete_thread_removes_folder` + `test_attachments_field_accepted` + `test_delete_thread_rejects_path_traversal`)
</success_criteria>

<output>
After completion, create `.planning/phases/37-pdf-office-mcp/37-04-SUMMARY.md`.
</output>
