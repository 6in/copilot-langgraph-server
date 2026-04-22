---
phase: 37
plan: 03
type: execute
wave: 1
depends_on: ["37-01", "37-02"]
files_modified:
  - mcp_server/tools/attachments.py
  - mcp_server/server.py
  - config/mcp_tools.yaml
  - mcp_server/tools/mcp_helper.py
  - mcp_server/tools/mcp_helper_utils.py
  - mcp_server/tools/execute_python.py
  - static/js/tool-catalog-generated.js
  - docs/mcp-tools.md
  - tests/test_attachments_extract.py
  - tests/test_attachments_list.py
  - tests/test_mcp_server.py
  - app/jobs/worker.py
  - app/jobs/handlers/langgraph_handler.py
  - .planning/phases/37-pdf-office-mcp/37-VALIDATION.md
autonomous: true
requirements: [FIN-03, FIN-04]
estimated_minutes: 140
tags: [mcp-tool, markitdown, security, rpc-context]

must_haves:
  truths:
    - "attachments_list / attachments_extract が @mcp.tool として登録され、FastMCP Client.list_tools() で 2 本とも返る"
    - "attachments_extract に basename 以外を渡すと error.code='corrupt' で拒否される (path traversal 対策)"
    - "RPCContext (thread_id / github_login) が tool 引数ではなく HTTP ヘッダー / sandbox 環境変数経由で mcp-server に届く (Plan 01 Verdict に従う 1 経路のみ実装)"
    - "execute_python sandbox から `list_attachments()` / `extract_attachment(fname)` を呼ぶと RPCContext が mcp-server 側で解決され、空でない結果 (または明示的な error) が返る (D-17 / ROADMAP SC-3 成立)"
    - "5 種のエラーコード (password / corrupt / size_over / unsupported / extract_timeout) が構造化戻り値で返る"
    - "config/mcp_tools.yaml から generate_mcp_artifacts.py --check が exit 0 (drift なし)"
    - "Plan 02 の Wave 0 xfail テストのうち attachments_extract/list 系 8 ケースが GREEN になる"
    - "Plan 01 の Verdict に従って Route A/B のどちらか 1 本道のコードだけが残り、他方のコードブロックはリポジトリに残らない"
  artifacts:
    - path: "mcp_server/tools/attachments.py"
      provides: "attachments_list + attachments_extract の実装 + 補助関数 (_safe_resolve / _extract_text)"
      contains: "def register_tools"
      min_lines: 150
    - path: "config/mcp_tools.yaml"
      provides: "attachments_list / attachments_extract の YAML エントリ"
      contains: "attachments_extract"
    - path: "mcp_server/tools/mcp_helper.py"
      provides: "list_attachments / extract_attachment Python ラッパー (自動生成)"
      contains: "def extract_attachment"
    - path: "static/js/tool-catalog-generated.js"
      provides: "iframe-rpc 向けカタログ (自動生成)"
      contains: "attachments_extract"
  key_links:
    - from: "mcp_server/tools/attachments.py"
      to: "markitdown.MarkItDown"
      via: "asyncio.to_thread + wait_for(60s)"
      pattern: "asyncio.to_thread"
    - from: "(Route A) app/jobs/handlers/langgraph_handler.py or (Route B) app/jobs/worker.py"
      to: "MultiServerMCPClient({..., 'headers': {...}}) or /internal/attachments_* via httpx"
      via: "RPCContext 伝播の唯一の経路 (Verdict が指す 1 本のみ)"
      pattern: "(headers=|x-thread-id)"
    - from: "mcp_server/tools/mcp_helper_utils.py"
      to: "mcp-server /internal/call_tool (or attachments_* REST)"
      via: "X-Thread-Id / X-Github-Login ヘッダー (execute_python subprocess の env 経由)"
      pattern: "X-Thread-Id|x-thread-id"
    - from: "mcp_server/tools/execute_python.py"
      to: "subprocess env"
      via: "_THREAD_ID / _GITHUB_LOGIN を subprocess に渡す"
      pattern: "_THREAD_ID|THREAD_ID"
    - from: "config/mcp_tools.yaml"
      to: "mcp_server/tools/mcp_helper.py"
      via: "scripts/generate_mcp_artifacts.py --target all"
      pattern: "extract_attachment|list_attachments"
---

<objective>
FIN-03 / FIN-04 の中核となる MCP ツール 2 本を実装し、Phase 30 SSoT フロー (YAML → generate → drift check) 経由で
カタログに登録する。Plan 01 の spike Verdict (Route A = MCP headers / Route B = /internal/attachments_* REST)
に従って **RPCContext 伝播経路を 1 本に絞って実装** する (W-02 対応)。

**本プランで D-17 / ROADMAP SC-3 を完了させる** (B-01/B-02/B-03/B-06 対応):
- Plan 03 Task 3 で RPCContext 伝播を動く状態で実装する (TODO コメントで先送りしない)
- execute_python sandbox / claude_code workspace から `list_attachments()` / `extract_attachment()` を呼んで
  空でない結果 (または thread 解決のうえでの明示的 error) が返ることを動作確認する (smoke integration レベル)

Purpose: LLM / execute_python sandbox の両方から `/shared/thread-files/<login>/<tid>/` 配下のファイルを
         参照・抽出できる MCP tool を本番投入する
Output:
  - `mcp_server/tools/attachments.py` (新規)
  - `config/mcp_tools.yaml` に 2 エントリ追加
  - `generate_mcp_artifacts.py --target all` による 3 生成物更新
  - Wave 0 xfail 8 ケースを GREEN に転換
  - RPCContext 伝播 (Route A or Route B、Verdict に従う 1 本)
  - VALIDATION.md Per-Task Map に 37-03-XX 行を追記
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
@.planning/phases/37-pdf-office-mcp/37-01-SUMMARY.md
@.planning/phases/37-pdf-office-mcp/37-02-SUMMARY.md
@docs/adr/0020-fastmcp-docker-service-infrastructure.md
@docs/adr/0023-mcp-db-query-and-claude-code-tools.md
@docs/adr/0044-mcp-tool-catalog-single-source-of-truth.md
@docs/mcp-tool-add-manual.md
@CLAUDE.md

<interfaces>
<!-- MarkItDown 公開 API (VERIFIED in RESEARCH.md) -->
From markitdown 0.1.5:
```python
from markitdown import MarkItDown, FileConversionException, UnsupportedFormatException

md = MarkItDown(enable_plugins=False)
result = md.convert(path)   # 同期!
text = result.text_content  # str
```

<!-- FastMCP CurrentHeaders DI (VERIFIED 3.2.3) -->
From fastmcp.dependencies:
```python
from fastmcp.dependencies import CurrentHeaders

@mcp.tool
async def some_tool(headers: dict = CurrentHeaders()) -> dict:
    thread_id = headers.get("x-thread-id", "")  # lowercase key
```

<!-- 既存の mcp-server register_tools パターン -->
From mcp_server/server.py (L17-22, L49-53):
```python
from tools.claude_code import register_tools as register_claude_code_tools
register_claude_code_tools(mcp)
```

<!-- worker MCP client 接続 (Route A での修正点) -->
From app/jobs/worker.py (L78-88):
```python
mcp_url = os.environ.get("MCP_SERVER_URL", "http://mcp-server:8001") + "/mcp"
mcp_client = MultiServerMCPClient({
    "copilot-tools": {
        "transport": "streamable_http",
        "url": mcp_url,
    }
})
```

<!-- タイムアウト + structured return の先例 -->
From mcp_server/tools/claude_code.py:
```python
TIMEOUT_SECS: int = 60
OUTPUT_DIR: str = os.environ.get("CLAUDE_CODE_OUTPUT_DIR", "/shared/claude-code-outputs")
```

<!-- エラー戻り値の先例 -->
From mcp_server/tools/web_search.py:
```python
except Exception as e:
    return {"error": f"web_search failed: {e}"}
```

<!-- execute_python subprocess 先例 (env 伝播参考) -->
From mcp_server/tools/execute_python.py:
```python
env = {
    "PATH": "/usr/local/bin:/usr/bin",
    # ... allowlist ...
}
proc = await asyncio.create_subprocess_exec(..., env=env)
```
</interfaces>

<skills>
- `.claude/skills/add-mcp-tool` — YAML → `scripts/generate_mcp_artifacts.py --target all` フローの自動化スキル
</skills>
</context>

<tasks>

<task type="auto">
  <name>Task 1: mcp_server/tools/attachments.py を新規作成 (MarkItDown 抽出 + 構造化エラー + path traversal 防御)</name>
  <files>mcp_server/tools/attachments.py</files>
  <read_first>
    - .planning/phases/37-pdf-office-mcp/37-01-SUMMARY.md (Verdict: Route A / Route B — 実装経路を決定)
    - .planning/phases/37-pdf-office-mcp/37-PATTERNS.md mcp_server/tools/attachments.py セクション
    - .planning/phases/37-pdf-office-mcp/37-RESEARCH.md Pattern 1-6 / Libraries and APIs (MarkItDown 部分)
    - .planning/phases/37-pdf-office-mcp/37-CONTEXT.md D-07 / D-09 / D-13 / D-14 / D-17 / D-18 / D-19 / D-20
    - mcp_server/tools/claude_code.py (timeout + structured return + env の先例)
    - mcp_server/tools/web_search.py (error 戻り値パターン)
    - tests/test_attachments_extract.py (Wave 0 の 6 ケースの assertion を満たす形で実装)
    - tests/test_attachments_list.py (Wave 0 の 2 ケースの assertion を満たす形で実装)
  </read_first>
  <action>
  PATTERNS.md および RESEARCH.md のコード断片を直接組み立て、以下のセクションを持つモジュールを新規作成する。

  **(A) module-level 定数と docstring** (per D-07/D-09/D-13/D-19):
  ```python
  """Phase 37: attachments_list / attachments_extract MCP tools.

  FIN-03: PDF/Office テキスト抽出  /  FIN-04: MCP ツール参照
  設計: CONTEXT.md D-06..D-21 / RESEARCH.md Pattern 1-6.
  """
  from __future__ import annotations

  import asyncio
  import mimetypes
  import os
  from typing import TYPE_CHECKING

  if TYPE_CHECKING:
      from fastmcp import FastMCP

  TIMEOUT_SECS: int = 60
  MAX_FILE_BYTES: int = 100 * 1024 * 1024       # D-09: 100 MB
  MAX_CHARS_PER_FILE: int = 50_000              # D-13
  MAX_CHARS_TOTAL: int = 200_000                # D-13 (session 合算。本モジュールでは参考値)
  SUPPORTED_EXTS: frozenset[str] = frozenset({".pdf", ".docx", ".xlsx", ".pptx"})   # D-07
  THREAD_FILES_DIR: str = os.environ.get("THREAD_FILES_DIR", "/shared/thread-files")  # D-01/D-04
  ```

  **(B) thread folder 解決 + path traversal 防御** (per D-18, W-04 対応で PATTERNS.md と揃える):
  ```python
  def _resolve_thread_folder(thread_id: str, github_login: str) -> str:
      return os.path.join(THREAD_FILES_DIR, github_login, thread_id)


  def _safe_resolve(thread_folder: str, filename: str) -> str:
      basename = os.path.basename(filename)
      if not basename or basename != filename:
          raise ValueError(f"Invalid filename: {filename!r}")
      candidate = os.path.join(thread_folder, basename)
      real = os.path.realpath(candidate)
      real_folder = os.path.realpath(thread_folder)
      # W-04 対応: PATTERNS.md と揃える — `real.startswith(real_folder + os.sep)` のみで十分。
      # basename 抽出後は real == real_folder にはならないため、そのケースは不要。
      if not real.startswith(real_folder + os.sep):
          raise ValueError(f"Path traversal detected: {filename!r}")
      return real
  ```

  **(C) MarkItDown 抽出 + エラー分類** (per D-19):
  ```python
  async def _extract_text(path: str) -> str:
      from markitdown import MarkItDown
      md = MarkItDown(enable_plugins=False)

      def _sync() -> str:
          result = md.convert(path)
          return result.text_content or ""

      return await asyncio.wait_for(asyncio.to_thread(_sync), timeout=TIMEOUT_SECS)


  def _classify_error(exc: BaseException) -> tuple[str, str]:
      from markitdown import FileConversionException, UnsupportedFormatException

      if isinstance(exc, asyncio.TimeoutError):
          return ("extract_timeout", "抽出が 60 秒でタイムアウトしました")
      if isinstance(exc, UnsupportedFormatException):
          return ("unsupported", "サポート外のファイル形式です")
      if isinstance(exc, FileConversionException):
          for attempt in (getattr(exc, "attempts", None) or []):
              info = getattr(attempt, "exc_info", None)
              if not info:
                  continue
              exc_type = info[0] if len(info) > 0 else None
              exc_val = info[1] if len(info) > 1 else None
              type_name = (getattr(exc_type, "__name__", "") or "").lower()
              msg = (str(exc_val) if exc_val else "").lower()
              if "password" in type_name or "encrypt" in type_name or "password" in msg:
                  return ("password", "パスワード保護されたファイルです")
          return ("corrupt", f"ファイル変換に失敗しました: {exc}")
      return ("corrupt", f"ファイル処理エラー: {exc}")
  ```

  **(D) core 関数 (headers 非依存) + tool ラッパー** — Route A/B 両対応にするため core/tool を分離:
  ```python
  async def attachments_list_core(thread_id: str, github_login: str) -> list[dict]:
      if not thread_id or not github_login:
          return []
      folder = _resolve_thread_folder(thread_id, github_login)
      if not os.path.isdir(folder):
          return []
      out: list[dict] = []
      for fname in sorted(os.listdir(folder)):
          fpath = os.path.join(folder, fname)
          if not os.path.isfile(fpath):
              continue
          stat = os.stat(fpath)
          ext = os.path.splitext(fname)[1].lower()
          mime_type, _ = mimetypes.guess_type(fname)
          out.append({
              "name": fname,
              "size": stat.st_size,
              "modified_at": float(stat.st_mtime),  # S-03 対応: docstring と型を揃える (float epoch seconds)
              "ext": ext,
              "mime_type": mime_type or "application/octet-stream",
          })
      return out


  async def attachments_extract_core(thread_id: str, github_login: str, filename: str) -> dict:
      empty = {"filename": filename, "content": None, "truncated": False, "truncated_chars": 0}
      if not thread_id or not github_login:
          return {**empty, "error": {"code": "corrupt", "message": "context missing"}}

      folder = _resolve_thread_folder(thread_id, github_login)

      # D-18 path traversal
      try:
          safe_path = _safe_resolve(folder, filename)
      except ValueError as e:
          return {**empty, "error": {"code": "corrupt", "message": str(e)}}

      if not os.path.isfile(safe_path):
          return {**empty, "error": {"code": "unsupported", "message": "file not found"}}

      ext = os.path.splitext(safe_path)[1].lower()
      if ext not in SUPPORTED_EXTS:
          return {**empty, "error": {"code": "unsupported", "message": f"ext {ext} not supported"}}

      size = os.path.getsize(safe_path)
      if size > MAX_FILE_BYTES:
          return {**empty, "error": {"code": "size_over", "message": f"file size {size} exceeds 100MB"}}

      try:
          text = await _extract_text(safe_path)
      except BaseException as e:
          code, msg = _classify_error(e)
          return {**empty, "error": {"code": code, "message": msg}}

      # D-08: テキスト 0 文字は error ではなく content:"" で返す
      truncated = False
      truncated_chars = 0
      if len(text) > MAX_CHARS_PER_FILE:
          truncated = True
          truncated_chars = len(text) - MAX_CHARS_PER_FILE
          text = text[:MAX_CHARS_PER_FILE]

      return {
          "filename": filename,
          "content": text,
          "error": None,
          "truncated": truncated,
          "truncated_chars": truncated_chars,
      }
  ```

  **(E) FastMCP tool ラッパー (Route A/B 共通)** — `CurrentHeaders()` DI で headers を受ける。
  Route B 採用時は Task 3 でこの部分を minimum にし、実際の thread 解決は `/internal/attachments_*` REST で行う。

  ```python
  from fastmcp.dependencies import CurrentHeaders

  async def attachments_list(headers: dict = CurrentHeaders()) -> list[dict]:
      thread_id = headers.get("x-thread-id", "")
      github_login = headers.get("x-github-login", "")
      return await attachments_list_core(thread_id, github_login)


  async def attachments_extract(filename: str, headers: dict = CurrentHeaders()) -> dict:
      thread_id = headers.get("x-thread-id", "")
      github_login = headers.get("x-github-login", "")
      return await attachments_extract_core(thread_id, github_login, filename)


  def register_tools(mcp: "FastMCP") -> None:
      mcp.tool(attachments_list)
      mcp.tool(attachments_extract)
  ```

  **注意事項:**
  - `MarkItDown()` は **per-call 生成** — `magika` が stateful のため singleton 化禁止
  - asyncio.TimeoutError catch 後も Thread は走り続ける (キャンセル不可) — accept
  - `attempts` 構造は MarkItDown のバージョンで変わる可能性あり。getattr で安全に走査
  - lazy import (`from markitdown import ...` を関数内) にすることで `onnxruntime` の初回ロードを
    実際の tool call 時点まで遅延できる
  </action>
  <verify>
    <automated>uv run python -c "import sys; sys.path.insert(0, 'mcp_server'); from tools.attachments import register_tools, attachments_list_core, attachments_extract_core, _safe_resolve, SUPPORTED_EXTS, MAX_FILE_BYTES, MAX_CHARS_PER_FILE, TIMEOUT_SECS; assert MAX_FILE_BYTES == 100*1024*1024 and TIMEOUT_SECS == 60 and '.pdf' in SUPPORTED_EXTS"</automated>
  </verify>
  <acceptance_criteria>
    - `mcp_server/tools/attachments.py` が存在、150 行以上
    - `grep -E 'TIMEOUT_SECS.*=.*60' mcp_server/tools/attachments.py` でマッチ
    - `grep -E 'MAX_FILE_BYTES.*100.*1024.*1024' mcp_server/tools/attachments.py` でマッチ
    - `grep -E 'MAX_CHARS_PER_FILE.*50_?000' mcp_server/tools/attachments.py` でマッチ
    - `grep -E '\.pdf.*\.docx.*\.xlsx.*\.pptx|\.xlsx.*\.pptx|\.docx.*\.pdf' mcp_server/tools/attachments.py` で 4 拡張子のいずれかの組合せがマッチ
    - `grep -E 'os\.path\.realpath' mcp_server/tools/attachments.py` でマッチ (path traversal 防御)
    - **W-04 対応:** `grep -E 'real\.startswith\(real_folder \+ os\.sep\)' mcp_server/tools/attachments.py` で 1 行マッチ (PATTERNS.md の条件と完全一致)
    - `grep -E 'asyncio\.wait_for|asyncio\.to_thread' mcp_server/tools/attachments.py` で両方マッチ
    - `grep -c -E "password|extract_timeout|size_over|unsupported|corrupt" mcp_server/tools/attachments.py` ≥ 5 (5 エラーコード)
    - `grep "def register_tools" mcp_server/tools/attachments.py` でマッチ
    - **S-03 対応:** `grep -E 'float\(stat\.st_mtime\)|st_mtime.*float' mcp_server/tools/attachments.py` でマッチ (modified_at の型を float で明示)
    - inline python で `_safe_resolve("/tmp/t", "../../etc/passwd")` が ValueError を raise する
  </acceptance_criteria>
  <done>attachments.py が単体 import と path-traversal smoke で通る</done>
</task>

<task type="auto">
  <name>Task 2: server.py 登録 + YAML 追加 + generate_mcp_artifacts.py --target all で 3 生成物を同期</name>
  <files>mcp_server/server.py, config/mcp_tools.yaml, mcp_server/tools/mcp_helper.py, static/js/tool-catalog-generated.js, docs/mcp-tools.md, tests/test_mcp_server.py</files>
  <read_first>
    - mcp_server/server.py L1-55 (register_*_tools の既存呼び出しパターン)
    - config/mcp_tools.yaml (既存 ping / web_search / db_query のスキーマ)
    - docs/mcp-tool-add-manual.md (YAML 追加手順)
    - .planning/phases/37-pdf-office-mcp/37-PATTERNS.md `config/mcp_tools.yaml (変更)` セクションの正確な YAML 本文
    - .planning/phases/37-pdf-office-mcp/37-CONTEXT.md D-14 / D-15 / D-16
    - scripts/generate_mcp_artifacts.py (`--target all` / `--check` の usage)
    - tests/test_mcp_server.py L28 (EXPECTED_TOOLS セット)
    - .planning/phases/37-pdf-office-mcp/37-01-SUMMARY.md (Route A or B — Route B なら `/internal/attachments_*` エンドポイントも本 Task で追加)
  </read_first>
  <action>
  **(A) mcp_server/server.py の import と登録呼び出しを追加**

  L17-22 末尾に:
  ```python
  from tools.attachments import register_tools as register_attachments_tools
  ```

  L49-53 末尾に:
  ```python
  register_attachments_tools(mcp)
  ```

  **(A') Plan 01 SUMMARY.md の Verdict が Route B の場合のみ** mcp-server に `/internal/attachments_*` エンドポイントを追加する。
  Route A の場合はこのブロックは実装しない (スキップ):

  ```python
  # Route B 専用 — Plan 01 SUMMARY.md の Verdict が Route B の場合のみ実装
  @mcp.custom_route("/internal/attachments_list", methods=["POST"])
  async def _route_attachments_list(request: Request) -> JSONResponse:
      from tools.attachments import attachments_list_core
      thread_id = request.headers.get("x-thread-id", "")
      github_login = request.headers.get("x-github-login", "")
      data = await attachments_list_core(thread_id, github_login)
      return JSONResponse({"result": data})

  @mcp.custom_route("/internal/attachments_extract", methods=["POST"])
  async def _route_attachments_extract(request: Request) -> JSONResponse:
      from tools.attachments import attachments_extract_core
      body = await request.json()
      thread_id = request.headers.get("x-thread-id", "")
      github_login = request.headers.get("x-github-login", "")
      filename = body.get("filename", "")
      data = await attachments_extract_core(thread_id, github_login, filename)
      return JSONResponse({"result": data})
  ```

  **(B) tests/test_mcp_server.py の EXPECTED_TOOLS を更新** (L28 付近):
  ```python
  EXPECTED_TOOLS = {"ping", "web_search", "db_query", "claude_code", "execute_python",
                    "get_current_datetime", "attachments_list", "attachments_extract"}  # Phase 37
  ```

  **(C) config/mcp_tools.yaml に 2 エントリ追加** — PATTERNS.md の本文を既存 `tools:` 配列の末尾
  (`get_current_datetime` の後) に転記する。インデントは 2 スペース (既存エントリと揃える)。

  ```yaml
    - name: attachments_list
      description: 現在の thread に添付されたファイルの一覧 (名前・サイズ・更新日時・拡張子) を返す
      privileged: false
      sandbox_exposed: true
      python_wrapper:
        function_name: list_attachments
        args: []
        return_type: "list[dict]"
        docstring: |
          添付ファイル一覧を返す。引数なし (thread は RPCContext 解決)。

          Returns:
              [{"name": "report.pdf", "size": 1234, "modified_at": <float epoch sec>, "ext": ".pdf", "mime_type": "..."}, ...]
              ファイルが存在しない場合は []

          Example:
              from mcp_helper import list_attachments
              files = list_attachments()
              for f in files:
                  print(f["name"], f["size"])
        mcp_args_mapping: {}
        result_transform:
          mode: passthrough

    - name: attachments_extract
      description: 指定ファイル (PDF/docx/xlsx/pptx) のテキストを MarkItDown で抽出して返す (最大 50,000 文字、60 秒タイムアウト)
      privileged: false
      sandbox_exposed: true
      python_wrapper:
        function_name: extract_attachment
        args:
          - name: filename
            type: str
            description: "抽出するファイル名 (basename のみ)"
        return_type: dict
        docstring: |
          添付ファイルのテキストを抽出する。

          Args:
              filename: ファイル名 (basename のみ。パス区切り文字不可)

          Returns:
              {"filename": "...", "content": "...", "error": null, "truncated": false, "truncated_chars": 0}
              エラー時: {"filename": "...", "content": null, "error": {"code": "...", "message": "..."}, ...}
              error.code: password | corrupt | size_over | unsupported | extract_timeout

          Example:
              from mcp_helper import extract_attachment
              r = extract_attachment("report.pdf")
              if r["error"] is None:
                  print(r["content"][:500])
        mcp_args_mapping:
          filename: filename
        result_transform:
          mode: passthrough
  ```

  **(D) 自動生成スクリプト実行**
  ```bash
  python3 scripts/generate_mcp_artifacts.py --target all
  ```

  これにより以下が自動更新される:
  - `mcp_server/tools/mcp_helper.py` (`list_attachments()` / `extract_attachment(filename)` ラッパー追加)
  - `static/js/tool-catalog-generated.js` (iframe-rpc 用カタログに 2 ツール追加)
  - `docs/mcp-tools.md` (人間向けドキュメントに 2 ツール追加)

  **(E) drift 確認**
  ```bash
  python3 scripts/generate_mcp_artifacts.py --check
  # exit 0 = drift なし
  ```

  **絶対に手編集しないファイル** (DO NOT EDIT ヘッダー付):
  - mcp_server/tools/mcp_helper.py
  - static/js/tool-catalog-generated.js
  - docs/mcp-tools.md
  </action>
  <verify>
    <automated>grep -q "register_attachments_tools" mcp_server/server.py && grep -q "^  - name: attachments_list$" config/mcp_tools.yaml && grep -q "^  - name: attachments_extract$" config/mcp_tools.yaml && grep -q "def list_attachments" mcp_server/tools/mcp_helper.py && grep -q "def extract_attachment" mcp_server/tools/mcp_helper.py && grep -q "attachments_extract" static/js/tool-catalog-generated.js && grep -q "attachments_extract" docs/mcp-tools.md && grep -q "attachments_list.*attachments_extract\|attachments_extract.*attachments_list" tests/test_mcp_server.py && python3 scripts/generate_mcp_artifacts.py --check</automated>
  </verify>
  <acceptance_criteria>
    - `grep "register_attachments_tools" mcp_server/server.py` で 2 行以上 (import + 呼び出し)
    - `grep "^  - name: attachments_list$" config/mcp_tools.yaml` で 1 行マッチ
    - `grep "^  - name: attachments_extract$" config/mcp_tools.yaml` で 1 行マッチ
    - `grep "def list_attachments" mcp_server/tools/mcp_helper.py` で 1 行マッチ
    - `grep "def extract_attachment" mcp_server/tools/mcp_helper.py` で 1 行マッチ
    - `grep "attachments_extract" static/js/tool-catalog-generated.js` で 1 件以上
    - `grep "attachments_extract" docs/mcp-tools.md` で 1 件以上
    - `python3 scripts/generate_mcp_artifacts.py --check` が exit 0 (drift なし)
    - `grep "EXPECTED_TOOLS" tests/test_mcp_server.py | grep "attachments_list" | grep "attachments_extract"` でマッチ
    - **Route B 採用時のみ:** `grep "/internal/attachments_list\|/internal/attachments_extract" mcp_server/server.py` で 2 行以上マッチ。Route A 採用時は該当行が **0 件** であること (W-02: 片方の経路のみ残す)
  </acceptance_criteria>
  <done>MCP ツールカタログの SSoT と 3 生成物が Phase 30 drift-check を通過する</done>
</task>

<task type="auto">
  <name>Task 3: RPCContext 伝播を Verdict に従って 1 本道で実装 + Wave 0 試験テスト 8 ケースを GREEN にする (B-01/B-02/B-03/B-06/W-02 対応)</name>
  <files>app/jobs/worker.py, app/jobs/handlers/langgraph_handler.py, mcp_server/tools/mcp_helper_utils.py, mcp_server/tools/execute_python.py, tests/test_attachments_extract.py, tests/test_attachments_list.py</files>
  <read_first>
    - **.planning/phases/37-pdf-office-mcp/37-01-SUMMARY.md (CRITICAL: Verdict が Route A か Route B かをまず読む — 以下のコードブロックはどちらか一方のみ実装する)**
    - app/jobs/worker.py L70-105 (MCP client 初期化、RPCContext が無い場合の DEGRADED 処理)
    - app/jobs/handlers/langgraph_handler.py L51-108 (RPCContext 構築箇所)
    - app/orchestrator/context.py (RPCContext.from_http シグネチャ)
    - mcp_server/tools/mcp_helper_utils.py (execute_python sandbox から `/internal/call_tool` を呼ぶ共通 HTTP クライアント)
    - mcp_server/tools/execute_python.py (subprocess env allowlist、`_THREAD_ID` / `_GITHUB_LOGIN` 追加対象)
    - tests/test_attachments_extract.py (Wave 0 xfail 6 ケース)
    - tests/test_attachments_list.py (Wave 0 xfail 2 ケース)
    - .planning/phases/37-pdf-office-mcp/37-RESEARCH.md Pattern 4 / Open Question Q1
  </read_first>
  <action>
  **W-02 / B-01 対応: 最初に Plan 01 SUMMARY.md を読んで Verdict を確認する。**

  以下は Route A / Route B の両方の実装を記載するが、**Verdict で示された方のみを実装する**。
  他方のコードブロックは削除する (リポジトリに両方残してはいけない)。

  ----

  ### ■ 経路 1: Route A 採用時 — MultiServerMCPClient headers 経由

  **Route A が動く条件:** Plan 01 Task 1 の実接続テストで、`MultiServerMCPClient({..., "headers": {...}})` を
  指定したときに mcp-server の `CurrentHeaders()` が `x-thread-id` / `x-github-login` を受け取れた場合。

  **(A-1) app/jobs/handlers/langgraph_handler.py** (L72 付近、`llm = ChatCopilot(...)` の直後) に per-request MCP client を構築:

  ```python
  # Phase 37 Route A: per-request MCP client with RPCContext headers
  # (worker startup の mcp_client は RPCContext を持てないため、handler 内で都度作る)
  from langchain_mcp_adapters.client import MultiServerMCPClient

  _mcp_url = os.environ.get("MCP_SERVER_URL", "http://mcp-server:8001") + "/mcp"
  _mcp_client_for_job = MultiServerMCPClient({
      "copilot-tools": {
          "transport": "streamable_http",
          "url": _mcp_url,
          "headers": {
              "x-thread-id": context.thread_id,
              "x-github-login": context.user_id,  # RPCContext.user_id = github_login (RESEARCH.md Pitfall 6)
          },
      }
  })
  mcp_tools_for_job = await _mcp_client_for_job.get_tools()
  # この mcp_tools_for_job を以降の ReAct ループ / ctx["mcp_tools"] の差し替えに使う
  # (既存コードで ctx["mcp_tools"] を使うパスがある場合のみ上書きする)
  ```

  **(A-2) execute_python sandbox への RPCContext 伝播:**

  execute_python の subprocess は内部で `mcp_helper.list_attachments()` / `extract_attachment()` を呼ぶ。
  これらは `mcp_helper_utils._call_tool()` が `http://mcp-server:8001/internal/call_tool` に POST する。
  Route A の場合、`/internal/call_tool` ハンドラが受け取った request headers を forward する必要があるため、
  subprocess 環境変数 → HTTP ヘッダーの変換を `mcp_helper_utils.py` で行う。

  `mcp_server/tools/execute_python.py` の subprocess env allowlist に 2 変数を追加:
  ```python
  # Phase 37 D-17: sandbox から mcp_helper 経由で attachments_* を呼ぶ際に RPCContext を伝搬
  env = {
      # ...既存 allowlist...
      "X_THREAD_ID": os.environ.get("X_THREAD_ID", ""),
      "X_GITHUB_LOGIN": os.environ.get("X_GITHUB_LOGIN", ""),
  }
  ```

  `mcp_server/tools/mcp_helper_utils.py` の `_call_tool` に headers 付与を追加:
  ```python
  # Phase 37 D-17: RPCContext を HTTP ヘッダーで下流に伝搬
  headers = {"Content-Type": "application/json"}
  _thread_id = os.environ.get("X_THREAD_ID", "")
  _github_login = os.environ.get("X_GITHUB_LOGIN", "")
  if _thread_id:
      headers["X-Thread-Id"] = _thread_id
  if _github_login:
      headers["X-Github-Login"] = _github_login

  response = httpx.post(url, json=payload, headers=headers, timeout=...)
  ```

  worker 側では execute_python tool を呼ぶとき、その subprocess env に X_THREAD_ID / X_GITHUB_LOGIN を
  注入する必要がある。これは `execute_python.py` の subprocess 起動箇所で `context` から取得する:
  ```python
  # execute_python のエントリ (mcp-server 側、tool 関数内)
  async def execute_python(code: str, headers: dict = CurrentHeaders()) -> dict:
      _thread_id = headers.get("x-thread-id", "")
      _github_login = headers.get("x-github-login", "")
      env = {
          # ... 既存 allowlist ...
          "X_THREAD_ID": _thread_id,
          "X_GITHUB_LOGIN": _github_login,
      }
      # subprocess.create_subprocess_exec(..., env=env)
  ```

  **(A-3) worker.py には変更なし** — startup の mcp_client は tool 一覧確認用のみ。

  ----

  ### ■ 経路 2: Route B 採用時 — /internal/attachments_* REST + httpx 直接呼び出し

  **Route B が動く条件:** Plan 01 Task 1 で MultiServerMCPClient headers が届かない / サポートされていないと判明した場合。

  **(B-1) app/jobs/worker.py** (L78-88 付近) の mcp_client 設定は変更せず、追加で httpx import を用意:
  ```python
  import httpx

  _MCP_INTERNAL_URL = os.environ.get("MCP_SERVER_URL", "http://mcp-server:8001")
  ```

  **(B-2) 以下 2 つのラッパー関数を worker.py に追加** (LangGraph ToolNode に登録できる形):
  ```python
  from langchain_core.tools import tool
  from typing import Annotated

  def _make_attachments_tools(thread_id: str, github_login: str) -> list:
      """Route B: per-request tool factory. handler 側で context が決まった後に呼ぶ。"""
      _headers = {"X-Thread-Id": thread_id, "X-Github-Login": github_login}

      @tool
      async def attachments_list() -> list[dict]:
          """現在の thread の添付ファイル一覧を返す。"""
          async with httpx.AsyncClient() as cli:
              r = await cli.post(f"{_MCP_INTERNAL_URL}/internal/attachments_list",
                                  headers=_headers, timeout=10)
              return r.json().get("result", [])

      @tool
      async def attachments_extract(filename: str) -> dict:
          """指定ファイルを抽出する (basename のみ)。"""
          async with httpx.AsyncClient() as cli:
              r = await cli.post(f"{_MCP_INTERNAL_URL}/internal/attachments_extract",
                                  headers=_headers, json={"filename": filename}, timeout=90)
              return r.json().get("result", {"error": {"code": "corrupt", "message": "no result"}})

      return [attachments_list, attachments_extract]
  ```

  **(B-3) app/jobs/handlers/langgraph_handler.py** で `_make_attachments_tools(context.thread_id, context.user_id)` を呼び、
  戻り値のツールを ReAct ループの tools 配列に足す。

  **(B-4) execute_python sandbox への RPCContext 伝播 (Route A と同一構造):**

  A-2 と同じく `mcp_helper_utils.py` の `_call_tool` に `X-Thread-Id` / `X-Github-Login` ヘッダー付与を追加。
  execute_python tool 関数内で subprocess env に注入。`/internal/call_tool` を /internal/attachments_* に差し替える
  バリエーションがあるが、Route B でも mcp_helper ラッパー経由では通常の `/internal/call_tool` を通すため
  A-2 と同じ実装でよい。

  ----

  ### ■ 共通タスク (Route A/B 両方で必須): Wave 0 xfail を解除し 8 ケースを GREEN にする

  **(C) tests/test_attachments_extract.py の完成** — xfail 解除 + 本実装:

  以下の型で各 test を書き換える:
  ```python
  @pytest.mark.asyncio
  async def test_extract_pdf(tmp_path, monkeypatch):
      import sys, os
      sys.path.insert(0, str(Path(__file__).parent.parent / "mcp_server"))
      # THREAD_FILES_DIR を tmp に差し替え
      thread_dir = tmp_path / "user-a" / "thread-1"
      thread_dir.mkdir(parents=True)
      sample_pdf = thread_dir / "report.pdf"
      sample_pdf.write_bytes(b"%PDF-1.4\n...dummy...")  # MarkItDown を mock するので中身は任意

      from tools import attachments
      monkeypatch.setattr(attachments, "THREAD_FILES_DIR", str(tmp_path))

      # MarkItDown を mock して "extracted text" を返す
      async def _fake_extract(path):
          return "extracted content"
      monkeypatch.setattr(attachments, "_extract_text", _fake_extract)

      result = await attachments.attachments_extract_core("thread-1", "user-a", "report.pdf")
      assert result["error"] is None
      assert "extracted content" in result["content"]
      assert result["truncated"] is False


  @pytest.mark.asyncio
  async def test_extract_password_protected(tmp_path, monkeypatch):
      from tools import attachments
      from markitdown import FileConversionException

      thread_dir = tmp_path / "u" / "t"
      thread_dir.mkdir(parents=True)
      (thread_dir / "locked.pdf").write_bytes(b"x")
      monkeypatch.setattr(attachments, "THREAD_FILES_DIR", str(tmp_path))

      class _FakeAttempt:
          exc_info = (type("PDFPasswordIncorrect", (), {}), Exception("password required"), None)

      async def _fake_extract(path):
          raise FileConversionException("locked", [_FakeAttempt()])

      monkeypatch.setattr(attachments, "_extract_text", _fake_extract)
      result = await attachments.attachments_extract_core("t", "u", "locked.pdf")
      assert result["error"]["code"] == "password"


  @pytest.mark.asyncio
  async def test_extract_size_over(tmp_path, monkeypatch):
      from tools import attachments
      thread_dir = tmp_path / "u" / "t"
      thread_dir.mkdir(parents=True)
      big = thread_dir / "huge.pdf"
      with open(big, "wb") as f:
          f.seek(101 * 1024 * 1024)
          f.write(b"\x00")
      monkeypatch.setattr(attachments, "THREAD_FILES_DIR", str(tmp_path))
      result = await attachments.attachments_extract_core("t", "u", "huge.pdf")
      assert result["error"]["code"] == "size_over"


  @pytest.mark.asyncio
  async def test_extract_timeout(tmp_path, monkeypatch):
      import asyncio
      from tools import attachments
      thread_dir = tmp_path / "u" / "t"
      thread_dir.mkdir(parents=True)
      (thread_dir / "slow.pdf").write_bytes(b"x")
      monkeypatch.setattr(attachments, "THREAD_FILES_DIR", str(tmp_path))

      async def _fake_extract(path):
          raise asyncio.TimeoutError()
      monkeypatch.setattr(attachments, "_extract_text", _fake_extract)
      result = await attachments.attachments_extract_core("t", "u", "slow.pdf")
      assert result["error"]["code"] == "extract_timeout"


  @pytest.mark.asyncio
  async def test_path_traversal(tmp_path, monkeypatch):
      from tools import attachments
      (tmp_path / "u" / "t").mkdir(parents=True)
      monkeypatch.setattr(attachments, "THREAD_FILES_DIR", str(tmp_path))
      result = await attachments.attachments_extract_core("t", "u", "../../etc/passwd")
      assert result["error"]["code"] == "corrupt"
      assert "traversal" in result["error"]["message"].lower() or "invalid" in result["error"]["message"].lower()


  @pytest.mark.asyncio
  async def test_truncation(tmp_path, monkeypatch):
      from tools import attachments
      thread_dir = tmp_path / "u" / "t"
      thread_dir.mkdir(parents=True)
      (thread_dir / "long.pdf").write_bytes(b"x")
      monkeypatch.setattr(attachments, "THREAD_FILES_DIR", str(tmp_path))

      async def _fake_extract(path):
          return "A" * (attachments.MAX_CHARS_PER_FILE + 1234)
      monkeypatch.setattr(attachments, "_extract_text", _fake_extract)

      result = await attachments.attachments_extract_core("t", "u", "long.pdf")
      assert result["truncated"] is True
      assert result["truncated_chars"] == 1234
      assert len(result["content"]) == attachments.MAX_CHARS_PER_FILE
  ```

  **(D) tests/test_attachments_list.py の完成**:
  ```python
  @pytest.mark.asyncio
  async def test_list_returns_metadata(tmp_path, monkeypatch):
      import sys
      sys.path.insert(0, str(Path(__file__).parent.parent / "mcp_server"))
      from tools import attachments
      thread_dir = tmp_path / "user-a" / "thread-1"
      thread_dir.mkdir(parents=True)
      (thread_dir / "20260421T120000_report.pdf").write_bytes(b"x" * 100)
      monkeypatch.setattr(attachments, "THREAD_FILES_DIR", str(tmp_path))

      result = await attachments.attachments_list_core("thread-1", "user-a")
      assert len(result) == 1
      assert result[0]["name"] == "20260421T120000_report.pdf"
      assert result[0]["size"] == 100
      assert result[0]["ext"] == ".pdf"
      # S-03: modified_at は float (epoch seconds)
      assert isinstance(result[0]["modified_at"], float)


  @pytest.mark.asyncio
  async def test_list_empty_folder(tmp_path, monkeypatch):
      from tools import attachments
      monkeypatch.setattr(attachments, "THREAD_FILES_DIR", str(tmp_path))
      result = await attachments.attachments_list_core("nope", "nope")
      assert result == []
  ```

  ----

  ### ■ E2E integration smoke (B-03 / ROADMAP SC-3 閉じ)

  **(E) docker compose 環境での integration smoke**:

  本 Task 完了前に以下を手元で実行し、execute_python sandbox / worker 経由で
  `list_attachments` / `extract_attachment` が thread フォルダの結果を返すことを確認する。
  結果を一時 log として記録する。

  ```bash
  # 1. compose 起動
  docker compose up -d --build mcp-server api worker postgres redis

  # 2. テスト thread フォルダにサンプル PDF を配置
  docker compose exec api mkdir -p /shared/thread-files/testuser/testthread
  echo "hello" | docker compose exec -T api tee /tmp/hello.txt >/dev/null
  # 4 形式のいずれかの軽量 sample をコピー (docx が最小で済む)
  docker compose cp samples/sample.docx api:/shared/thread-files/testuser/testthread/20260421T000000_sample.docx

  # 3. execute_python 経由呼び出し (最小 POST テスト):
  curl -X POST http://localhost:8001/internal/call_tool \
      -H "Content-Type: application/json" \
      -H "X-Thread-Id: testthread" \
      -H "X-Github-Login: testuser" \
      -d '{"tool_name": "attachments_list", "args": {}}'
  # 期待: {"result": [{"name": "20260421T000000_sample.docx", ...}]}

  curl -X POST http://localhost:8001/internal/call_tool \
      -H "Content-Type: application/json" \
      -H "X-Thread-Id: testthread" \
      -H "X-Github-Login: testuser" \
      -d '{"tool_name": "attachments_extract", "args": {"filename": "20260421T000000_sample.docx"}}'
  # 期待: {"result": {"content": "...", "error": null, ...}}

  # 4. cleanup
  docker compose down
  ```

  smoke 結果を `work/phase-37/integration-smoke-plan03.md` に 5-10 行で記録する (FULL integration check は Plan 05 Task 3)。
  </action>
  <verify>
    <automated>uv run pytest tests/test_attachments_extract.py tests/test_attachments_list.py -x -q --no-header 2>&1 | tail -20 | grep -E "(passed|failed)" && uv run pytest tests/test_attachments_extract.py tests/test_attachments_list.py -x -q --no-header 2>&1 | tail -3 | grep -qE "([0-9]+) passed" && ! (uv run pytest tests/test_attachments_extract.py tests/test_attachments_list.py -x -q --no-header 2>&1 | tail -3 | grep -qE "([0-9]+) failed")</automated>
  </verify>
  <acceptance_criteria>
    - `tests/test_attachments_extract.py` から全 `@pytest.mark.xfail` が除去されている (`grep -c "xfail" tests/test_attachments_extract.py` が 0)
    - `tests/test_attachments_list.py` から全 `@pytest.mark.xfail` が除去されている
    - `uv run pytest tests/test_attachments_extract.py tests/test_attachments_list.py -v` で全 8 ケースが passed
    - `test_path_traversal` で `result["error"]["code"] == "corrupt"` (または同等の拒否) を確認
    - `test_truncation` で `MAX_CHARS_PER_FILE` に切り詰められ `truncated_chars` が正確
    - **B-01/B-02 対応 (RPCContext 伝播の実装):** 以下のいずれか 1 つが成立する
      - Route A: `grep -E 'headers.*x-thread-id|"x-thread-id"' app/jobs/handlers/langgraph_handler.py` で 1 行以上マッチ、かつ `grep "MultiServerMCPClient" app/jobs/handlers/langgraph_handler.py` で 1 行以上マッチ
      - Route B: `grep "/internal/attachments_" app/jobs/worker.py` で 1 行以上マッチ、かつ `grep "X-Thread-Id\|x-thread-id" app/jobs/worker.py` で 1 行以上マッチ
    - **D-17 (execute_python sandbox 伝播):** `grep "X_THREAD_ID\|X-Thread-Id" mcp_server/tools/mcp_helper_utils.py` で 1 行以上マッチ、かつ `grep "X_THREAD_ID" mcp_server/tools/execute_python.py` で 1 行以上マッチ
    - **B-03 / ROADMAP SC-3 閉じ (integration smoke):** `work/phase-37/integration-smoke-plan03.md` が存在し、
      `attachments_list` / `attachments_extract` の両方が `"result"` フィールドで空でないレスポンスを返した 2 つの curl 出力が貼付されている
    - **W-02 対応 (片方の経路のみ):** Route A なら `grep "/internal/attachments_list\|/internal/attachments_extract" mcp_server/server.py` が 0 件、Route B なら `grep "headers=.*x-thread-id\|headers=.*X-Thread-Id" app/jobs/handlers/langgraph_handler.py` が 0 件 (他方のコードが残っていない)
  </acceptance_criteria>
  <done>Wave 0 で置いた xfail 8 ケースが実装と同期して全 passed になり、RPCContext 伝播が動作し、SC-3 が成立する</done>
</task>

<task type="auto">
  <name>Task 4: VALIDATION.md Per-Task Map に Wave 1 (37-03-XX) 行を追記 (B-07 段階更新 2 回目)</name>
  <files>.planning/phases/37-pdf-office-mcp/37-VALIDATION.md</files>
  <read_first>
    - .planning/phases/37-pdf-office-mcp/37-VALIDATION.md (Plan 02 Task 4 で Wave 0 行が入った状態)
    - 本 Plan Task 1-3 の `<verify>` / `<acceptance_criteria>`
  </read_first>
  <action>
  VALIDATION.md の Per-Task Verification Map テーブル末尾に、本 Plan の Task 1-3 に対応する行を追記する:

  ```markdown
  | 37-03-01 | 03 | 1 | FIN-03 | T-37-03-01 | path traversal 拒否 | unit | `uv run pytest tests/test_attachments_extract.py::test_path_traversal -x` | ✅ | ⬜ pending |
  | 37-03-02 | 03 | 1 | FIN-03 | T-37-03-03 | size_over 拒否 | unit | `uv run pytest tests/test_attachments_extract.py::test_extract_size_over -x` | ✅ | ⬜ pending |
  | 37-03-03 | 03 | 1 | FIN-03 | T-37-03-04 | 60 秒 timeout | unit | `uv run pytest tests/test_attachments_extract.py::test_extract_timeout -x` | ✅ | ⬜ pending |
  | 37-03-04 | 03 | 1 | FIN-03 | — | password 検出 | unit | `uv run pytest tests/test_attachments_extract.py::test_extract_password_protected -x` | ✅ | ⬜ pending |
  | 37-03-05 | 03 | 1 | FIN-03 | — | truncation | unit | `uv run pytest tests/test_attachments_extract.py::test_truncation -x` | ✅ | ⬜ pending |
  | 37-03-06 | 03 | 1 | FIN-04 | — | SSoT drift clean | smoke | `python3 scripts/generate_mcp_artifacts.py --check` | ✅ | ⬜ pending |
  | 37-03-07 | 03 | 1 | FIN-04 | — | list メタデータ | unit | `uv run pytest tests/test_attachments_list.py -x` | ✅ | ⬜ pending |
  | 37-03-08 | 03 | 1 | FIN-04 | T-37-03-02 | RPCContext 伝播 smoke | integration | `test -s work/phase-37/integration-smoke-plan03.md && grep -E '"result":' work/phase-37/integration-smoke-plan03.md` | ✅ | ⬜ pending |
  ```
  </action>
  <verify>
    <automated>grep -c "^| 37-03-" .planning/phases/37-pdf-office-mcp/37-VALIDATION.md | awk '{if ($1 >= 6) exit 0; else exit 1}'</automated>
  </verify>
  <acceptance_criteria>
    - VALIDATION.md の Per-Task Verification Map に `37-03-` で始まる行が 6 件以上
    - 各行に Automated Command 列が埋まっている (空欄なし)
    - 37-03-08 (RPCContext 伝播 smoke) の行が存在する
  </acceptance_criteria>
  <done>Plan 03 分の Per-Task Map が VALIDATION.md に追記され、Plan 04 で続けて追記できる状態になる</done>
</task>

</tasks>

<threat_model>

## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| LLM prompt / user message → MCP tool 引数 | 悪意ある prompt が `filename` に traversal を仕込む |
| LLM prompt / user message → MCP tool thread 選択 | `thread_id` が tool 引数に含まれると他 thread を参照される |
| mcp-server filesystem → `/shared/thread-files/<login>/<tid>/` | path traversal / symlink 経由で thread 外ファイルを読まれる |
| MarkItDown の内部 parser (pdfminer / mammoth / pptx / openpyxl) | 悪意あるファイルで DoS / 情報漏洩 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-37-03-01 | Tampering / Information Disclosure | `attachments_extract(filename)` with `../../../etc/passwd` → thread フォルダ外のファイルを読める | **mitigate (HIGH)** | `_safe_resolve` で `os.path.basename` で `/` `\` を拒否 + `os.path.realpath` 後に `realpath.startswith(real_folder + os.sep)` で prefix assert。Task 1 実装 + Task 3 test_path_traversal で検証 |
| T-37-03-02 | Information Disclosure | LLM prompt が `thread_id` を偽装して他 thread を読む | **mitigate (HIGH)** | tool 引数に thread_id を含めない (D-17)。RPCContext は HTTP ヘッダー / sandbox env 経由で mcp-server 側が解決する。Task 1 `attachments_extract_core(thread_id, github_login, filename)` は core 関数 (純関数) であり MCP tool として直接公開されない |
| T-37-03-03 | DoS | 100MB 超の巨大ファイルで MarkItDown が長時間 CPU / メモリを消費する | mitigate (MEDIUM) | size_check を MarkItDown 呼び出し前に配置。`os.path.getsize(safe_path) > MAX_FILE_BYTES` で早期 reject (D-09) |
| T-37-03-04 | DoS | 不正な構造の PDF で MarkItDown が無限ループする | mitigate (MEDIUM) | `asyncio.wait_for(..., timeout=60)` で 60 秒でタイムアウト (D-19) |
| T-37-03-05 | Elevation of Privilege | worker が mcp-server の `/internal/call_tool` に直接アクセスして `x-thread-id` を偽装する | accept (LOW) | mcp-server はホストポート非公開 (ADR-0020)。worker コンテナ自体が compromise されるならより深刻な経路がある |
| T-37-03-06 | Information Disclosure | 一時 spike ログ (Plan 01) が本番コードに残存して trace に RPCContext が漏れる | mitigate | Plan 01 Task 1 の受け入れ基準で `git diff mcp_server/server.py` クリーンを要求済み。Plan 03 開始時点で revert されていることを Task 2 Read で確認 |
| T-37-03-07 | Tampering | symlink を `/shared/thread-files/<login>/<tid>/` に仕込んで realpath が外に逃げる | mitigate (HIGH) | `os.path.realpath` 後の prefix assert で吸収される |

</threat_model>

<verification>
- `python3 scripts/generate_mcp_artifacts.py --check` が exit 0
- `uv run pytest tests/test_mcp_server.py -k attachments -v` (FastMCP Client.list_tools() に 2 本が出現)
- `uv run pytest tests/test_attachments_extract.py tests/test_attachments_list.py -v` が 8 件全 passed
- `grep "xfail" tests/test_attachments_extract.py tests/test_attachments_list.py` で 0 ヒット
- `mcp_server/tools/attachments.py` の行数が 150 以上
- **B-03 閉じ:** `work/phase-37/integration-smoke-plan03.md` に `"result":` を含む curl レスポンスが 2 件以上貼付
- **W-02 閉じ:** Route A or Route B のどちらか 1 本だけがリポジトリに残っている
- VALIDATION.md に `^| 37-03-` 行が 6 件以上追記されている
</verification>

<success_criteria>
- attachments_list / attachments_extract が SSoT 登録済み・生成物 drift なし・8 テスト全 passed
- RPCContext 伝播が Route A/B のどちらか 1 経路で動作し、execute_python sandbox から呼んで空でない結果が返る (D-17 / ROADMAP SC-3 成立)
- Plan 04 (handler 修正) が attachments.py / mcp_helper.list_attachments / mcp_helper.extract_attachment をそのまま参照できる状態
- FIN-03 SC-1/2/4 および FIN-04 SC-3 の実装側 artifact が揃う (ADR 化は Plan 05)
</success_criteria>

<output>
After completion, create `.planning/phases/37-pdf-office-mcp/37-03-SUMMARY.md`.
</output>
