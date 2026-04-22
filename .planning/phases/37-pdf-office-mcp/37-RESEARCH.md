# Phase 37: ファイル入力 — PDF/Office 抽出 + MCP ツール参照 - Research

**Researched:** 2026-04-21
**Domain:** PDF/Office テキスト抽出 (MarkItDown) + FastMCP コンテキスト注入 + Docker named volume + LangGraph SystemMessage prepend
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**フォルダ規約・ライフサイクル**
- D-01: `/shared/thread-files/<github_login>/<thread_id>/` 2 階層
- D-02: `YYYYMMDDTHHMMSS_<original_name>.<ext>` タイムスタンプ prefix 命名
- D-03: thread 削除と同期で `rm -rf`。`app/api/routes/chat.py::delete_thread` の `adelete_thread()` 直後に hook
- D-04: Docker named volume `thread-files` を新規作成。api: RW / mcp-server: RW / worker: RO
- D-05: フォルダ規約を本 phase で ADR 化。`.planning/patterns.md` に `Data・Persistence` カテゴリで 1 エントリ追記

**抽出ライブラリ・対応フォーマット**
- D-06: **MarkItDown (Microsoft)** 単独採用。OS パッケージ追加なし
- D-07: `.pdf / .docx / .xlsx / .pptx` 4 種のみ。ODF/OCR は非対応
- D-08: OCR 非対応。テキスト 0 文字 PDF は `content: ""` + メタ情報返却
- D-09: 1 ファイル 100 MB 上限。超過は抽出前に `size_over` エラーで拒否

**抽出処理・LLM 注入**
- D-10: 抽出は MCP tool 経由の on-demand。worker での事前抽出なし
- D-11: worker handler がスレッドフォルダを scan し、**添付一覧メタデータのみ** を SystemMessage として `messages[0]` に prepend。hint 付き ("内容を読むには attachments_extract を呼ぶこと")
- D-12: `AgentState` に `attachments: list[dict]` フィールド追加 (last-writer-wins reducer)
- D-13: 抽出テキスト上限 1 ファイル 50,000 文字 / スレッド合計 200,000 文字。truncate + `truncated: true, truncated_chars: N` 通知

**MCP ツール設計**
- D-14: 新規 MCP ツール 2 本
  - `attachments_list`: 引数なし (RPCContext 解決)、`[{name, size, modified_at, ext}, ...]`
  - `attachments_extract`: `filename: str`、`{content, error:{code,message}|null, truncated, truncated_chars, filename}`
- D-15: `/add-mcp-tool` スラッシュコマンド経由で登録。YAML SSoT + `generate_mcp_artifacts.py --target all`
- D-16: 両ツールとも `privileged: false`、`sandbox_exposed: true`
- D-17: thread_id/github_login は **RPCContext 経由で mcp-server 側が解決**。tool 引数に含めない
- D-18: `filename` は basename のみ受付。mcp-server 側で `os.path.realpath` + prefix assert

**失敗ハンドリング**
- D-19: 5 カテゴリ構造化エラー: `password` / `corrupt` / `size_over` / `unsupported` / `extract_timeout` (60 秒)
- D-20: 失敗は戻り値の `error: {code, message}` で返す。例外 raise なし
- D-21: 再試行ロジックなし。agent が必要なら再呼び出し

### Claude's Discretion

- ADR 本文の書き振り (具体パス例の数、Phase 36/38 接続 interface 記述粒度)
- Docker Compose の volume 定義書式・bind mount との切り替え可能性
- `attachments_list` の戻り値追加フィールド (MIME type・ハッシュ等)
- SystemMessage のテンプレート文言
- MarkItDown の subprocess 実行 vs in-process 呼び出し
- MarkItDown pin バージョン
- Thread state に抽出キャッシュを持たせるかどうか

### Deferred Ideas (OUT OF SCOPE)

- Phase 36 のアップロード UI / API
- Phase 38 の生成ファイル保持・ダウンロード UI
- OCR (スキャン PDF 対応)
- ODF (odt/ods/odp) 対応
- バイナリ読み出し tool (attachments_read_bytes)
- 抽出結果のキャッシュ層
- UI エラー表示 (Phase 36 責務)
- マルチモーダル画像 (Phase 36 責務)

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FIN-03 | PDF / Office ファイルを添付でき、サーバー側で抽出したテキストを LLM が参照できる | MarkItDown API・SystemMessage prepend 設計・worker handler 統合 |
| FIN-04 | 添付ファイルが MCP ツール (execute_python / claude_code 等) からも参照できる | `attachments_list`/`attachments_extract` MCP ツール設計・Docker volume・RPCContext 解決 |

</phase_requirements>

---

## Summary

Phase 37 は 4 つのソフトウェア構成要素を同時に実装するフェーズ。**（1）Docker named volume `thread-files`** の追加とサービス別 mount 権限設定、**（2）worker handler における SystemMessage prepend** でのファイル一覧 hint 注入、**（3）MarkItDown を使った MCP ツール 2 本の実装** (on-demand テキスト抽出)、**（4）thread 削除フックへのフォルダ rm 追加** の 4 領域から成る。

MarkItDown は Microsoft 製 OSS で pip only。`markitdown[pdf,docx,pptx,xlsx]` でインストールすれば OS パッケージ追加なしに `.pdf/.docx/.xlsx/.pptx` の 4 形式を Markdown に変換できる。**同期 API のみ** (非同期なし) のため、60 秒タイムアウトは `asyncio.wait_for(asyncio.to_thread(md.convert, path), timeout=60)` でラップする。

最大の設計課題は **RPCContext (thread_id/github_login) を mcp-server 側に届ける手段**。現在の `MultiServerMCPClient` 経由 MCP プロトコル呼び出しでは HTTP ヘッダーへの注入が難しい。最も実装コストが低い解法は、既存の `/internal/call_tool` エンドポイントを拡張して `attachments_*` 専用に `X-Thread-Id` / `X-Github-Login` ヘッダーを付与する **専用 HTTP 呼び出し経路** を mcp_server 側に追加すること（或いは mcp_server の新規 REST エンドポイントとして実装）。

**Primary recommendation:** `attachments_list` / `attachments_extract` は FastMCP `@mcp.tool` として登録するが、mcp-server には別途 `/internal/attachments_list` と `/internal/attachments_extract` の REST エンドポイントも提供し、worker から `X-Thread-Id` / `X-Github-Login` ヘッダー付きで直接 HTTP 呼び出しする。これにより path-traversal 対策を mcp-server 側で完結させ、agent 側の LangChain ToolNode 呼び出しは MCP protocol 経由のまま維持できる。

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| フォルダ作成・命名 | mcp-server (抽出時) | api (削除時) | Phase 36 までは mcp-server が RW で create |
| PDF/Office テキスト抽出 | mcp-server | — | MarkItDown は mcp-server コンテナにのみインストール |
| 添付ファイル一覧 scan | worker handler | mcp-server tool | handler は起動時 scan → SystemMessage; tool は on-demand |
| SystemMessage prepend | worker (LangGraphHandler) | — | LangGraph 実行前の config 構築ロジックを拡張 |
| AgentState.attachments | worker | — | handler が毎 turn scan してセット、last-wins reducer |
| RPCContext 解決 | mcp-server | — | HTTP ヘッダー経由で受け取り、path 構築 |
| Path traversal 対策 | mcp-server | — | `os.path.realpath` + prefix assert |
| Thread フォルダ削除 | api (delete_thread hook) | — | `adelete_thread()` 直後に `shutil.rmtree` |
| Docker volume 宣言 | Infra (docker-compose.yml) | — | named volume `thread-files` 新規定義 |
| ツール登録 (YAML SSoT) | mcp-server (config) | — | `config/mcp_tools.yaml` → `generate_mcp_artifacts.py` |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `markitdown` | 0.1.5 [VERIFIED: pip index] | PDF/docx/xlsx/pptx → Markdown テキスト抽出 | Microsoft 製 OSS、pip only、OS パッケージ不要 |
| `markitdown[pdf]` extras | 0.1.5 | PDF 抽出 (`pdfminer-six>=20251230`, `pdfplumber>=0.11.9`) | 同上 |
| `markitdown[docx]` extras | 0.1.5 | docx 抽出 (`mammoth~=1.11.0`, `lxml`) | 同上 |
| `markitdown[pptx]` extras | 0.1.5 | pptx 抽出 (`python-pptx`) | 同上 |
| `markitdown[xlsx]` extras | 0.1.5 | xlsx 抽出 (`openpyxl`, `pandas`) | 同上 |
| `fastmcp` | 3.2.3 [VERIFIED: mcp_server venv] | MCP サーバーフレームワーク | プロジェクト既存。`CurrentHeaders()` で HTTP ヘッダー取得可能 |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `asyncio.to_thread` | stdlib | 同期 MarkItDown を非同期ラップ | MCP tool 関数は async だが MarkItDown は sync |
| `asyncio.wait_for` | stdlib | 60 秒タイムアウト | `extract_timeout` エラー実装 |
| `os.path.realpath` | stdlib | path traversal 防御 | `attachments_extract` の filename 検証 |
| `shutil.rmtree` | stdlib | フォルダ削除 | `delete_thread` hook |
| `magika` | ~0.6.1 | MarkItDown 内部の MIME type 検出 | MarkItDown の必須依存 (pip only、OS 不要) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `markitdown` | `pypdf` + `python-docx` + `openpyxl` + `python-pptx` 個別 | 手組み実装が必要、LLM 向け Markdown 正規化なし |
| `markitdown` | LibreOffice CLI | OS パッケージ必須 (image 肥大)、D-06 で除外 |
| in-process 実行 | subprocess 実行 | subprocess はタイムアウト + kill が確実だが image 複雑化。in-process + asyncio.to_thread + wait_for が簡潔 |

**Installation (mcp_server/pyproject.toml に追記):**
```toml
"markitdown[pdf,docx,pptx,xlsx]>=0.1.5,<0.2.0",
```

> **注意:** `magika~=0.6.1` は MarkItDown の必須依存。onnxruntime を引き込む (純 Python + バイナリ wheel のみ、OS パッケージ不要)。mcp-server Dockerfile でビルド時間が増加する可能性があるが再現性に問題なし。

---

## Architecture Patterns

### System Architecture Diagram

```
Worker (arq job)
  │
  ├─[起動時 scan]─→ /shared/thread-files/<login>/<thread_id>/
  │                   ├─ 20260421T120000_report.pdf
  │                   └─ 20260421T120100_data.xlsx
  │
  ├─ SystemMessage prepend: "添付ファイル: report.pdf (1.2MB), data.xlsx (45KB)\n内容を読むには attachments_extract を呼ぶこと"
  │
  └─ LangGraph invoke
       │
       ├─ LLM: "report.pdf の内容を教えて"
       │
       └─→ [MCP tool call] attachments_extract(filename="report.pdf")
                │
                └─→ mcp-server /internal/attachments_extract
                      X-Thread-Id: <thread_id>
                      X-Github-Login: <github_login>
                      │
                      ├─ path: /shared/thread-files/<login>/<thread_id>/20260421T120000_report.pdf
                      ├─ size check (100MB)
                      ├─ asyncio.to_thread(MarkItDown().convert, path)  [timeout 60s]
                      └─ return {content: "...", error: null, truncated: false, truncated_chars: 0, filename: "report.pdf"}

API (delete_thread)
  └─ shutil.rmtree(/shared/thread-files/<login>/<thread_id>/)
```

### Recommended Project Structure

```
mcp_server/tools/
├── attachments_list.py      # 新規: attachments_list MCP tool 実装
├── attachments_extract.py   # 新規: attachments_extract MCP tool 実装  
└── (既存ツール)

mcp_server/server.py         # register_attachments_*_tools() 呼び出し追加

config/mcp_tools.yaml        # attachments_list / attachments_extract エントリ追加
app/orchestrator/state.py    # attachments: list[dict] フィールド追加
app/jobs/handlers/langgraph_handler.py  # scan + SystemMessage prepend 追加
app/api/routes/chat.py       # delete_thread: shutil.rmtree hook 追加
docker-compose.yml           # thread-files volume + service mount 追加
```

### Pattern 1: MarkItDown 同期 → 非同期ラップ + タイムアウト

**What:** 同期ブロッキングな `MarkItDown().convert()` を asyncio スレッドプール経由で実行し、60 秒でタイムアウト
**When to use:** `attachments_extract` MCP tool 実装のコア

```python
# Source: [VERIFIED: markitdown/_markitdown.py, asyncio stdlib]
import asyncio
from markitdown import MarkItDown, FileConversionException, UnsupportedFormatException

TIMEOUT_SECS = 60

async def _extract_text(path: str) -> str:
    """MarkItDown 変換を asyncio.to_thread 経由で非同期実行 (タイムアウト付き)。"""
    md = MarkItDown(enable_plugins=False)

    def _sync_convert() -> str:
        result = md.convert(path)
        return result.text_content or ""

    try:
        text = await asyncio.wait_for(
            asyncio.to_thread(_sync_convert),
            timeout=TIMEOUT_SECS,
        )
        return text
    except asyncio.TimeoutError:
        raise  # caller が extract_timeout エラーに変換
```

### Pattern 2: 構造化エラー戻り値 (web_search.py パターンを踏襲)

**What:** 例外を raise せず `error: {code, message}` フィールドで返す
**When to use:** `attachments_extract` の全エラーケース

```python
# Source: [VERIFIED: mcp_server/tools/web_search.py (existing pattern)]
async def attachments_extract(filename: str) -> dict:
    try:
        # path resolution, size check, MarkItDown call
        ...
        return {
            "filename": filename,
            "content": text,
            "error": None,
            "truncated": truncated,
            "truncated_chars": truncated_chars,
        }
    except asyncio.TimeoutError:
        return {
            "filename": filename,
            "content": None,
            "error": {"code": "extract_timeout", "message": "抽出が 60 秒でタイムアウトしました"},
            "truncated": False,
            "truncated_chars": 0,
        }
    except Exception as e:
        return {
            "filename": filename,
            "content": None,
            "error": {"code": "corrupt", "message": str(e)},
            "truncated": False,
            "truncated_chars": 0,
        }
```

### Pattern 3: FastMCP CurrentHeaders() による RPCContext 解決

**What:** FastMCP 3.2.3 の `CurrentHeaders()` 依存性注入で `X-Thread-Id` / `X-Github-Login` ヘッダーを受け取る
**When to use:** `attachments_list` / `attachments_extract` のフォルダパス解決

```python
# Source: [VERIFIED: fastmcp 3.2.3 mcp_server/.venv/lib/.../fastmcp/server/dependencies.py]
from fastmcp import FastMCP
from fastmcp.dependencies import CurrentHeaders

@mcp.tool
async def attachments_list(headers: dict = CurrentHeaders()) -> list[dict]:
    """添付ファイル一覧を返す (thread は HTTP ヘッダーで解決)。"""
    thread_id = headers.get("x-thread-id", "")
    github_login = headers.get("x-github-login", "")
    if not thread_id or not github_login:
        return []
    
    folder = _resolve_thread_folder(thread_id, github_login)
    # ... os.listdir + stat ...
```

**重要:** `CurrentHeaders()` はデフォルトで `authorization`, `mcp-session-id`, `content-length` 等の一部ヘッダーを除外する。`x-thread-id` / `x-github-login` はカスタムプレフィックス `x-` を使えば通過する (`get_http_headers()` の `exclude_headers` に含まれない)。

### Pattern 4: Worker から mcp-server への ヘッダー付き内部 HTTP 呼び出し

**What:** `langchain-mcp-adapters` 経由の MCP ツール呼び出しはヘッダー注入が困難。既存の `/internal/call_tool` パターンを拡張して RPCContext ヘッダーを付与する
**When to use:** `LangGraphHandler._handle_inner` 内での直接 HTTP 呼び出しは不要。LangGraph ToolNode 経由の MCP 呼び出し時にヘッダーを届ける方法が課題。

**解決策: MCP セッション初期化時に `X-Thread-Id`/`X-Github-Login` ヘッダーを注入する**

```python
# MultiServerMCPClient の接続設定に headers を追加
# Source: [ASSUMED - langchain_mcp_adapters の Connection 型の headers サポートを要確認]
mcp_client = MultiServerMCPClient({
    "copilot-tools": {
        "transport": "streamable_http",
        "url": mcp_url,
        "headers": {
            "x-thread-id": thread_id,
            "x-github-login": github_login,
        }
    }
})
```

> **[ASSUMED]** `langchain_mcp_adapters.client.MultiServerMCPClient` が `headers` キーを `streamable_http` 接続設定でサポートしているかは未確認。代替案: mcp-server に `/internal/attachments_list` と `/internal/attachments_extract` の専用 REST エンドポイントを作り、worker から `httpx.AsyncClient` で直接呼び出す（ヘッダー付与が確実）。

**推奨実装方針 (planner への指示):**
- Wave 0: mcp-server に `/internal/attachments_list` / `/internal/attachments_extract` を REST エンドポイントとして追加。worker から `httpx` 直接呼び出し。
- Wave 1 以降: MCP プロトコル経由のヘッダー注入が確認できれば通常 `@mcp.tool` に統一。

### Pattern 5: SystemMessage prepend (ADR-0025 パターン踏襲)

**What:** `LangGraphHandler._handle_inner` 内の `effective_system_prompt` 構築に添付ファイル hint を追加
**When to use:** D-11 の実装。`HumanMessage` の前に添付情報を持つ `SystemMessage` を作るのではなく、`config["configurable"]["system_prompt"]` に追記する

```python
# Source: [VERIFIED: app/jobs/handlers/langgraph_handler.py L118-134 (既存パターン)]
# 変更前:
effective_system_prompt = datetime_prefix + "\n\n" + (system_prompt or "") + AUQ_PROTOCOL

# 変更後 (D-11):
attachments_hint = _scan_thread_attachments(thread_id, github_login)
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
```

### Pattern 6: path traversal 防御

**What:** `filename` basename を受け取り `os.path.realpath` 後に thread フォルダ prefix を assert
**When to use:** `attachments_extract` の必須検証

```python
# Source: [CITED: D-18, ASSUMED: standard os.path.realpath pattern]
import os

def _safe_resolve(thread_folder: str, filename: str) -> str:
    """basename のみ受け付け、path traversal を防ぐ。"""
    # basename のみ抽出 (os.sep / ../ を排除)
    basename = os.path.basename(filename)
    if not basename or basename != filename:
        raise ValueError(f"Invalid filename: {filename!r}")
    
    candidate = os.path.join(thread_folder, basename)
    real = os.path.realpath(candidate)
    real_folder = os.path.realpath(thread_folder)
    
    if not real.startswith(real_folder + os.sep):
        raise ValueError(f"Path traversal detected: {filename!r}")
    
    return real
```

### Pattern 7: Docker named volume (既存 `claude-code-outputs` パターンを踏襲)

**What:** `docker-compose.yml` に新規 named volume を追加し、サービス別に RW/RO で mount
**When to use:** D-04 の実装

```yaml
# Source: [VERIFIED: docker-compose.yml L151 (claude-code-outputs の前例)]
volumes:
  thread-files:   # Phase 37: PDF/Office 添付ファイル共有ボリューム

services:
  api:
    volumes:
      - thread-files:/shared/thread-files       # RW (削除 + 将来のアップロード書き込み)
  
  mcp-server:
    volumes:
      - thread-files:/shared/thread-files       # RW (抽出 + 将来の派生ファイル)
  
  worker:
    volumes:
      - thread-files:/shared/thread-files:ro    # RO (将来の scan 用途のみ)
```

### Pattern 8: delete_thread フック (ADR-0026 パターン踏襲)

**What:** `app/api/routes/chat.py::delete_thread` の `adelete_thread()` 直後にフォルダ rm を追加
**When to use:** D-03 の実装。フォルダが存在しない場合も `ignore_errors=True` で安全に通過

```python
# Source: [VERIFIED: app/api/routes/chat.py L380-385 (adelete_thread の位置)]
import shutil

# 既存コード (L382):
try:
    await checkpointer.adelete_thread(thread_id)
except Exception:
    pass

# 追加 (D-03):
thread_folder = f"/shared/thread-files/{github_login}/{thread_id}"
try:
    if os.path.isdir(thread_folder):
        shutil.rmtree(thread_folder, ignore_errors=True)
except Exception:
    pass  # フォルダが存在しない場合は無視
```

> **環境変数化の推奨:** `THREAD_FILES_DIR = os.environ.get("THREAD_FILES_DIR", "/shared/thread-files")` として api / worker / mcp-server で共通の env var から base path を取得する。ハードコードを避け、テスト時の tmpdir 差し替えが容易になる。

### Pattern 9: AgentState フィールド追加 (last-wins reducer)

**What:** `AgentState` に `attachments: list[dict]` を追加。reducer は `last-wins` で handler が毎 turn 上書き
**When to use:** D-12 の実装

```python
# Source: [VERIFIED: app/orchestrator/state.py (既存 AgentState)]
# patterns.md「Checkpointer 復元を想定した state reducer 設計」(ADR-0046) に従い
# `attachments` は handler が毎 turn fresh scan するため last-wins (reducer 不要 = TypedDict デフォルト)

class AgentState(TypedDict):
    input: str
    output: str
    messages: Annotated[list[BaseMessage], operator.add]
    next: str
    context: Annotated[RPCContext, _keep_first]  # 実際は _keep_fresh (ADR-0046 参照)
    error: str | None
    agent_name: str | None
    context_messages: list[dict] | None
    attachments: list[dict] | None  # 追加: [{name, size, modified_at, ext}, ...]
```

### Anti-Patterns to Avoid

- **`thread_id` を tool 引数に含める:** D-17 で明示禁止。プロンプト汚染攻撃の経路になる
- **MarkItDown をメインスレッドで同期呼び出し:** FastMCP の async event loop をブロックする。必ず `asyncio.to_thread` でラップ
- **`shutil.rmtree` をエラー raise で実装:** フォルダが存在しない thread の削除でエラーになる。`ignore_errors=True` または存在チェック後に実行
- **MarkItDown インスタンスをモジュールレベルでシングルトン化:** `MarkItDown()` は stateful (magika インスタンス等) のため per-call 生成が安全
- **path traversal 検証で `os.path.basename` のみ使用:** `realpath` + prefix assert のセットで実施

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF テキスト抽出 | 独自 pypdf ラッパー | `markitdown[pdf]` | LLM 向け Markdown 正規化 (テーブル変換等) + pdfminer/pdfplumber フォールバック実装済み |
| docx 抽出 | `python-docx` 直接解析 | `markitdown[docx]` (mammoth) | スタイル保持 + HTML 経由 Markdown 変換 |
| pptx スライド抽出 | `python-pptx` 直接解析 | `markitdown[pptx]` | ノート・表・図の注釈を自動処理 |
| xlsx セル抽出 | `openpyxl` 直接解析 | `markitdown[xlsx]` | Markdown テーブル変換済み |
| path traversal 対策 | URL encode/decode チェック | `os.path.realpath` + prefix assert | シンボリックリンク・`../` 等すべての攻撃ベクトルに対処 |

**Key insight:** 各 Office 形式は独自のエラーケース (パスワード保護、破損、不正バイト) を持ち、自前実装は膨大なエッジケース対応が必要。MarkItDown は `FileConversionException` に統一してこれらを吸収する。

---

## Existing Code (統合ポイント)

### Area 1: docker-compose.yml — thread-files volume 追加

**File:** `docker-compose.yml`  
**Change:** `volumes:` セクションに `thread-files:` 追加 + 3 サービス各 `volumes:` に mount 追加  
**Reference line:** L151 (`claude-code-outputs:` の直下 or 末尾)

既存パターン (L111):
```yaml
- claude-code-outputs:/shared/claude-code-outputs:ro   # Phase 23 Plan 02: read-only
```

### Area 2: mcp_server/pyproject.toml — MarkItDown 依存追加

**File:** `mcp_server/pyproject.toml`  
**Change:** `dependencies` リストに `"markitdown[pdf,docx,pptx,xlsx]>=0.1.5,<0.2.0"` 追加  
**Current state:** fastmcp, langchain-community, psycopg, pyyaml の 4 依存のみ

### Area 3: app/orchestrator/state.py — attachments フィールド追加

**File:** `app/orchestrator/state.py`  
**Current:** L10-18: `AgentState` TypedDict (input/output/messages/next/context/error/agent_name/context_messages)  
**Change:** `attachments: list[dict] | None` フィールドを末尾に追加。reducer 不要 (TypedDict デフォルト = last-wins)

### Area 4: app/jobs/handlers/langgraph_handler.py — scan + SystemMessage prepend

**File:** `app/jobs/handlers/langgraph_handler.py`  
**Target:** `_handle_inner()` L118-134 (effective_system_prompt 構築ブロック)  
**Change:** `effective_system_prompt` 構築の前に `_scan_thread_attachments(thread_id, github_login)` を呼び、結果を system_prompt 末尾に追記。`state_input` に `attachments` も含める。

**現在のシステムプロンプト構築 (L126-133):**
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
```

### Area 5: app/api/routes/chat.py::delete_thread — フォルダ rm hook

**File:** `app/api/routes/chat.py`  
**Target:** L380-385 (`await checkpointer.adelete_thread(thread_id)` の直後、関数終端)  
**Change:** `shutil.rmtree` 呼び出し追加。`github_login` は L354 (`payload.get("github_login", "")`) で既に利用可能

### Area 6: mcp_server/server.py — attachments ツール登録

**File:** `mcp_server/server.py`  
**Change:** `from tools.attachments_list import register_tools as register_attachments_list_tools` 等の import + `register_attachments_list_tools(mcp)` / `register_attachments_extract_tools(mcp)` 呼び出し追加

### Area 7: config/mcp_tools.yaml + generated artifacts

**File:** `config/mcp_tools.yaml`  
**Change:** `tools:` 配列末尾に `attachments_list` / `attachments_extract` の 2 エントリを追加  
**Follow-up:** `python3 scripts/generate_mcp_artifacts.py --target all` で `mcp_helper.py` / `tool-catalog-generated.js` / `docs/mcp-tools.md` を再生成

---

## Libraries and APIs (完全な呼び出しシグネチャ)

### MarkItDown 0.1.5

```python
# [VERIFIED: markitdown-0.1.5-py3-none-any.whl から直接確認]
from markitdown import (
    MarkItDown,
    DocumentConverterResult,   # .text_content: str
    FileConversionException,   # 変換失敗 (password/corrupt を含む)
    UnsupportedFormatException, # 非対応形式 (accepts() が全 converter で False)
    MissingDependencyException, # optional deps 未インストール
)

# インスタンス生成
md = MarkItDown(enable_plugins=False)  # plugins=False でサードパーティプラグインを無効化

# 変換 (同期)
result: DocumentConverterResult = md.convert(source)
# source: str (ローカルパス), Path, requests.Response, BinaryIO
# .convert() → .convert_local() / .convert_uri() / .convert_stream() に振り分け

text: str = result.text_content  # 変換後 Markdown テキスト

# エラー例外の詳細:
# - FileConversionException: pdfminer/pdfplumber/mammoth 等が raise した例外を
#   FailedConversionAttempt リストに包んで再 raise する。
#   パスワード保護 PDF は pdfminer が PDFPasswordIncorrect を raise →
#   FileConversionException.attempts[0].exc_info[0] が PDFPasswordIncorrect になる
# - UnsupportedFormatException: 全 converter が accepts() False の場合
#   (例: .odt を convert() に渡す)
```

**PDF パスワード保護の検出:**
MarkItDown は pdfminer.six を使用。パスワード保護の検出は `FileConversionException` を catch して `attempts` を検査する:

```python
# [VERIFIED: _markitdown.py L600-625 + pdfminer behavior - ASSUMED: pdfminer exception type name]
from markitdown import FileConversionException

try:
    result = md.convert(path)
except FileConversionException as e:
    if e.attempts:
        for attempt in e.attempts:
            exc_type = attempt.exc_info[0] if attempt.exc_info else None
            exc_msg = str(attempt.exc_info[1]) if attempt.exc_info and attempt.exc_info[1] else ""
            if exc_type is not None and (
                "password" in exc_type.__name__.lower()
                or "encrypt" in exc_type.__name__.lower()
                or "password" in exc_msg.lower()
            ):
                return {"error": {"code": "password", "message": "パスワード保護されたファイルです"}}
    return {"error": {"code": "corrupt", "message": str(e)}}
```

> **[ASSUMED]** パスワード保護 PDF での具体的な exception type は `pdfminer.pdfencrypt.PDFPasswordIncorrect` または `pypdf.errors.FileNotDecryptedError` と考えられるが、実環境でのテストで確認が必要。exception name の文字列マッチ ("password" / "encrypt") が最も堅牢な detection 方法。

### FastMCP 3.2.3 — `CurrentHeaders()` 依存性注入

```python
# [VERIFIED: fastmcp 3.2.3 mcp_server/.venv/lib/.../fastmcp/dependencies.py]
from fastmcp.dependencies import CurrentHeaders

@mcp.tool
async def attachments_list(headers: dict = CurrentHeaders()) -> list[dict]:
    """引数なし tool。HTTP ヘッダー経由で thread context を取得。"""
    thread_id = headers.get("x-thread-id", "")
    github_login = headers.get("x-github-login", "")
    ...
```

**重要な動作:**
- `get_http_headers()` はデフォルトで `authorization`/`mcp-session-id`/`content-length` 等を除外するが、`x-thread-id`/`x-github-login` はカスタムヘッダーなので通過する [VERIFIED: fastmcp/server/dependencies.py `exclude_headers` セット確認]
- `CurrentHeaders()` は `Dependency` で、ツール関数のスキーマから除外される (LLM には引数として見えない)
- HTTP リクエストがない場合は空 dict `{}` を返す (RuntimeError にならない)

### langchain-mcp-adapters MultiServerMCPClient — headers 注入

```python
# [ASSUMED: streamable_http 接続設定に headers が渡せるか未確認]
# 現行 worker.py の接続設定 (L81-87):
mcp_client = MultiServerMCPClient({
    "copilot-tools": {
        "transport": "streamable_http",
        "url": mcp_url,
    }
})

# 提案: RPCContext ヘッダーを追加 (planner が動作確認すること)
mcp_client = MultiServerMCPClient({
    "copilot-tools": {
        "transport": "streamable_http",
        "url": mcp_url,
        "headers": {
            "x-thread-id": context.thread_id,
            "x-github-login": context.user_id,
        }
    }
})
```

> **Alternative (確実な実装):** `mcp_server/server.py` に専用 REST エンドポイントを追加し、worker から `httpx.AsyncClient` で直接呼び出す。`MultiServerMCPClient` のヘッダーサポートを前提にしない安全な実装。

---

## Approach Analysis

### MarkItDown 実行方式: in-process vs subprocess

| 方式 | 利点 | 欠点 |
|------|------|------|
| **in-process + asyncio.to_thread** (推奨) | シンプル、image サイズ増加なし | MarkItDown のメモリリーク・内部クラッシュが worker プロセスに影響 |
| subprocess (python3 -c "from markitdown import MarkItDown; ...") | 完全分離 | 起動コスト、serialization overhead、pdfplumber の subprocess 禁止制約なし |

**推奨: in-process + asyncio.to_thread**。200 名規模の社内利用では in-process の simplicity が勝る。MarkItDown は成熟した OSS で内部クラッシュリスクは低い。タイムアウトは `asyncio.wait_for` で制御し、60 秒後は `asyncio.to_thread` の thread は完走させて捨てる（スレッドキャンセルは Python では不可）。

### RPCContext 解決: HTTP ヘッダー vs tool 引数

| 方式 | 利点 | 欠点 |
|------|------|------|
| **HTTP ヘッダー** (D-17, 採用) | path traversal 遮断、LLM に thread_id を渡さない | `MultiServerMCPClient` の headers 対応が未確認 |
| tool 引数 (禁止) | 実装容易 | プロンプト汚染で他 thread のファイルを読める |
| 専用 REST エンドポイント | ヘッダー注入が確実、デバッグ容易 | MCP プロトコルを迂回、ToolNode 経由呼び出しに乗らない |

**最終判断:** MCP プロトコル経由の agent 呼び出しを維持しつつ、HTTP ヘッダー注入で解決する。`MultiServerMCPClient` の `headers` 対応確認を Wave 0 のスパイクタスクとして計画する。確認できない場合は専用 REST エンドポイントにフォールバック。

### MarkItDown バージョン固定

`mcp_server/pyproject.toml` では `>=0.1.5,<0.2.0` で固定することを推奨。マイナーバージョン上限 `<0.2.0` を付ける理由: MarkItDown は 0.0.x → 0.1.0 の移行で `convert_stream()` 引数型が破壊的変更されており、マイナー版での API 安定性が保証されていない。

---

## Common Pitfalls

### Pitfall 1: asyncio.to_thread でタイムアウト後もスレッドが走り続ける

**What goes wrong:** `asyncio.wait_for(..., timeout=60)` が `asyncio.TimeoutError` を raise した後も、`asyncio.to_thread` で起動したスレッドは MarkItDown の処理を続ける。大量の大ファイルが来た場合にスレッドが積み重なる。
**Why it happens:** Python の `Thread` は cancel できない。
**How to avoid:** タイムアウト後は `error: extract_timeout` を返して処理を終了する。MarkItDown スレッドは eventually 完走するが結果は捨てられる。重大なリソース問題になるようなら subprocess 方式に切り替える (Claude's Discretion 範囲)。
**Warning signs:** mcp-server のメモリ使用量が増加し続ける

### Pitfall 2: `CurrentHeaders()` がスキーマに出現して LLM が混乱する

**What goes wrong:** `headers: dict = CurrentHeaders()` を通常の引数のように定義すると、FastMCP がスキーマ生成時に `headers` を tool 引数として expose してしまう可能性がある。
**Why it happens:** FastMCP の DI (Dependency Injection) が正しく型ヒントを認識しない場合。
**How to avoid:** FastMCP 3.2.3 では `CurrentHeaders()` は `Dependency` インスタンスを返す `uncalled_for` ベースの DI で、スキーマから自動除外されることを[VERIFIED: fastmcp/dependencies.py]確認済み。ただし動作確認は Wave 0 スパイクで実施すること。
**Warning signs:** `mcp.call_tool("attachments_list", {})` が "unexpected argument 'headers'" エラーを返す

### Pitfall 3: path traversal 検証の順序ミス

**What goes wrong:** `os.path.basename(filename)` の前に `os.path.join(thread_folder, filename)` を実行すると、`../../../../etc/passwd` のような入力でも join してしまう。
**Why it happens:** basename チェックより先に join する実装ミス。
**How to avoid:** `basename = os.path.basename(filename)` → `basename == filename` チェック → `os.path.join` → `os.path.realpath` → prefix assert の順番を厳守する。
**Warning signs:** unit test `test_safe_resolve_path_traversal` を必ず書くこと

### Pitfall 4: Docker volume mount 権限と既存ファイル

**What goes wrong:** `thread-files` volume を `:ro` で worker に mount した状態で、worker コードから `shutil.rmtree` を呼ぼうとした場合に `PermissionError`。
**Why it happens:** フォルダ削除は api コンテナの責務 (D-03)。worker の `:ro` mount では書き込み不可。
**How to avoid:** `delete_thread` hook は `app/api/routes/chat.py` (api コンテナ) に実装する。worker からは絶対にフォルダ操作しない。
**Warning signs:** `OSError: [Errno 30] Read-only file system` in worker logs

### Pitfall 5: MarkItDown の `magika` 依存 (onnxruntime) による起動時間増加

**What goes wrong:** mcp-server の起動時間が大幅に増加し、Docker healthcheck の `start_period: 30s` を超える可能性。
**Why it happens:** `magika` は onnxruntime (ML 推論エンジン) を依存として持ち、初回 import 時にモデルファイルをロードする。
**How to avoid:** `MarkItDown` インスタンスはモジュールレベルで 1 回だけ作成し、tool 関数間で共有する (per-call 生成は避ける)。初回 import のオーバーヘッドは unavoidable だが、`start_period: 30s` を `60s` に延ばすことで対処。
**Warning signs:** `mcp-server` コンテナが `start_period` 内に `/health` を返せず再起動ループ

### Pitfall 6: RPCContext の `user_id` フィールドは `github_login`

**What goes wrong:** `RPCContext.user_id` と思って参照すると、実は `github_login` として設定されている値を取得しているのに、変数名の混同でバグが生じる。
**Why it happens:** RPCContext は `user_id` フィールドだが、github_login の値を格納 (`context = RPCContext.from_http(user_id=github_login, ...)`)。
**How to avoid:** `X-Github-Login: context.user_id` ヘッダーで送信。mcp-server 側は `headers.get("x-github-login")` で受け取り。

### Pitfall 7: OrchestratorHandler と DebateHandler への波及

**What goes wrong:** `LangGraphHandler` のみに scan + prepend を追加して、`OrchestratorHandler` / `DebateHandler` に対応漏れ。
**Why it happens:** Phase 37 は LangGraph (chat/gem/canvas) のみを対象とする前提だが、SuperChat も同じ `thread-files` フォルダを使う可能性。
**How to avoid:** Phase 37 は LangGraphHandler のみに適用。SuperChat/Debate への拡張は Phase 38 以降で判断する (CONTEXT.md の Deferred に明示的には記載なし — planner が scope を確認すること)。

---

## Runtime State Inventory

> Phase 37 は新規 volume + 新規ツールの追加。既存の runtime state への影響を確認。

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | 既存 `thread-files` volume なし (新規作成) | なし |
| Live service config | docker-compose.yml のサービス定義変更 | `docker compose up --build` で再作成 |
| OS-registered state | なし | なし |
| Secrets/env vars | `THREAD_FILES_DIR` 環境変数 (新規追加推奨) | docker-compose.yml の各サービスに環境変数追加 |
| Build artifacts | mcp_server venv 再作成 (markitdown 追加) | `docker compose build mcp-server` |

**既存 `claude-code-outputs` volume との独立性:** D-04 通り `thread-files` は新規 named volume。既存データへの影響なし。

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker Compose | volume 管理 | ✓ | (既存) | — |
| `markitdown` 0.1.5 | mcp-server pip | ✗ (未インストール) | — | なし (必須) |
| `magika` ~0.6.1 | markitdown 必須依存 | ✗ (mcp-server venv に未追加) | — | なし (必須) |
| `pdfminer-six` ≥20251230 | markitdown[pdf] | ✗ | — | なし (PDF 抽出に必須) |
| `pdfplumber` ≥0.11.9 | markitdown[pdf] | ✗ | — | なし |
| `mammoth` ~1.11.0 | markitdown[docx] | ✗ | — | なし (docx 抽出に必須) |
| `python-pptx` | markitdown[pptx] | ✓ (既存インストール確認) | 1.0.2 | — |
| `openpyxl`, `pandas` | markitdown[xlsx] | 不明 | — | なし (xlsx 抽出に必須) |
| `httpx` | worker から mcp-server 直接呼び出し (代替案) | ✓ (app pyproject.toml ≥0.28.0) | — | — |
| `fastmcp` 3.2.3 | mcp-server | ✓ | 3.2.3 | — |

**Missing dependencies (blocking):**
- `markitdown[pdf,docx,pptx,xlsx]` — mcp-server Docker image に追加必須 (Wave 0)

---

## Validation Architecture

> `workflow.nyquist_validation: true` のため必須セクション。

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.25 |
| Config file | `pyproject.toml` ([tool.pytest.ini_options]) |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FIN-03 (SC-1) | `attachments_extract("report.pdf")` が テキストを返す | unit (mock MarkItDown) | `pytest tests/test_attachments_extract.py::test_extract_pdf -x` | ❌ Wave 0 |
| FIN-03 (SC-2) | パスワード保護 PDF が `error.code == "password"` を返す | unit (MarkItDown FileConversionException mock) | `pytest tests/test_attachments_extract.py::test_extract_password_protected -x` | ❌ Wave 0 |
| FIN-03 (SC-2) | 100MB 超過ファイルが `error.code == "size_over"` を返す | unit | `pytest tests/test_attachments_extract.py::test_extract_size_over -x` | ❌ Wave 0 |
| FIN-03 (SC-2) | 60 秒タイムアウトが `error.code == "extract_timeout"` を返す | unit (asyncio.sleep mock) | `pytest tests/test_attachments_extract.py::test_extract_timeout -x` | ❌ Wave 0 |
| FIN-03 (SC-3) | `attachments_list()` がフォルダ内ファイルのメタデータ一覧を返す | unit (tmp_path) | `pytest tests/test_attachments_list.py -x` | ❌ Wave 0 |
| FIN-03 (SC-4) | path traversal (`"../../../etc/passwd"`) が ValueError を raise する | unit | `pytest tests/test_attachments_extract.py::test_path_traversal -x` | ❌ Wave 0 |
| FIN-03 (SC-5) | `AgentState.attachments` フィールドが LangGraph checkpoint に永続化される | unit (AsyncPostgresSaver mock or tmp) | `pytest tests/test_agent_state.py::test_attachments_field -x` | ❌ Wave 0 (既存 test_agent_state.py に追記) |
| FIN-04 (SC-3) | `/shared/thread-files/<login>/<thread_id>/` が mcp-server から読み取れる | integration (smoke test) | `docker compose exec mcp-server ls /shared/thread-files/` | N/A (手動) |
| FIN-04 (SC-5) | thread 削除後にフォルダが消える | integration | `pytest tests/test_api_chat.py::test_delete_thread_removes_folder -x` | ❌ Wave 0 |
| ADR 化 (SC-5) | ADR ファイルが存在し INDEX.md に記載される | smoke | `cat docs/adr/INDEX.md | grep thread-files` | ❌ Wave 3 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_attachments_extract.py tests/test_attachments_list.py -x -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_attachments_extract.py` — FIN-03 SC-1/2, path traversal, timeout, truncation
- [ ] `tests/test_attachments_list.py` — FIN-03 SC-3 (tmp_path ベース)
- [ ] `tests/test_api_chat.py::test_delete_thread_removes_folder` — FIN-04 SC-5 (delete_thread hook)
- [ ] `tests/test_agent_state.py::test_attachments_field` — AgentState 型チェック (既存ファイルに追記)
- [ ] `config/mcp_tools.yaml` への `attachments_list`/`attachments_extract` エントリ追加 + `generate_mcp_artifacts.py --target all` 実行

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | JWT 認証は既存の auth.py が処理 |
| V3 Session Management | no | セッション管理変更なし |
| V4 Access Control | **yes** | RPCContext による thread 所有者検証 (D-17) |
| V5 Input Validation | **yes** | filename basename check + realpath + prefix assert (D-18) |
| V6 Cryptography | no | 暗号処理なし (パスワード解除は非対応) |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal (`../../../etc/passwd`) | Tampering/Disclosure | `os.path.basename` + `os.path.realpath` + prefix assert |
| Cross-thread 読み取り (プロンプト汚染) | Disclosure | tool 引数に thread_id を含めない (D-17) |
| 大容量ファイルによる DoS (100MB 超) | DoS | size check before MarkItDown 呼び出し (D-09) |
| 無限ループ PDF (MarkItDown hang) | DoS | `asyncio.wait_for` 60 秒タイムアウト (D-19) |
| mcp-server への直接アクセス | Elevation | mcp-server はホストポート非公開 (既存 ADR-0020) |

---

## Open Questions

1. **`MultiServerMCPClient` の `headers` オプションサポート (CRITICAL)**
   - What we know: mcp_server/server.py は streamable-http トランスポートを使用。FastMCP 3.2.3 は `CurrentHeaders()` で HTTP ヘッダーを読める
   - What's unclear: `langchain_mcp_adapters.MultiServerMCPClient` が `"headers"` キーを `streamable_http` 接続設定で受け付け、各 tool call 時に HTTP ヘッダーとして転送するかどうか
   - Recommendation: Wave 0 の **スパイクタスク** として 30 分以内で確認。確認できなければ mcp-server に専用 REST エンドポイント (`/internal/attachments_list`, `/internal/attachments_extract`) を追加する fallback 実装で進める

2. **OrchestratorHandler / DebateHandler への添付ファイル scan 拡張スコープ**
   - What we know: D-11 は `langgraph_handler.py` への追加を明示
   - What's unclear: SuperChat (orchestrator) / DebateChat のユーザーも `thread-files` フォルダを使うか、またその場合に本 phase で対応するか
   - Recommendation: Phase 37 は `LangGraphHandler` (chat/gem/canvas) のみに適用し、SuperChat/Debate は Phase 38 で判断。CONTEXT.md に明示的な記述がないため planner がユーザーに確認するか、保守的に LangGraphHandler のみで実装する

3. **magika onnxruntime の Docker ビルド時間**
   - What we know: `magika` は `onnxruntime` を依存として引き込む。初回 `uv sync` 時に数十 MB のパッケージをダウンロード
   - What's unclear: Docker ビルド時間への実際の影響。ARM64 (Apple Silicon) vs AMD64 でビルド済み wheel が提供されているか
   - Recommendation: Wave 0 の Docker build で実測。30 秒以上増加する場合は `start_period` を `60s` に延長、または `MarkItDown(enable_builtins=False)` で必要なコンバーターのみ手動登録 (magika 起動を遅延させる)

4. **`attachments_list` の戻り値に MIME type を含めるか (Claude's Discretion)**
   - What we know: `mimetypes.guess_type(filename)` で拡張子ベースの MIME type は取得可能
   - Recommendation: 含めることを推奨。LLM がファイルの種類を把握しやすくなる。`{name, size, modified_at, ext, mime_type}` のフォーマットで返す

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `langchain_mcp_adapters.MultiServerMCPClient` が `streamable_http` 接続設定で `headers` キーをサポートしており、ツール呼び出し時に HTTP ヘッダーとして転送する | Libraries and APIs | コンテキスト伝搬の実装方針を REST エンドポイント方式に変更必要 |
| A2 | パスワード保護 PDF の MarkItDown 変換が `FileConversionException` に内包される例外メッセージに "password" または "encrypt" 文字列を含む | Libraries and APIs | password 検出ロジックを実ファイルでテストして修正が必要 |
| A3 | mcp-server Docker image の onnxruntime ビルドが既存の `start_period: 30s` 内に完了する | Environment Availability | healthcheck の `start_period` を 60s に延長 |
| A4 | `asyncio.to_thread(MarkItDown().convert, path)` 経由での変換で、スレッドプールが MarkItDown 実行を正しく処理する (reentrance safe) | Approach Analysis | MarkItDown インスタンスのスレッドセーフ性に問題があれば per-call の lock が必要 |
| A5 | OrchestratorHandler / DebateHandler への添付ファイル scan 拡張は Phase 37 スコープ外 | Open Questions | SuperChat ユーザーが添付ファイルを参照できない |

---

## Sources

### Primary (HIGH confidence)
- [VERIFIED] `markitdown-0.1.5-py3-none-any.whl` — `_exceptions.py`, `_pdf_converter.py`, `_markitdown.py`, `METADATA` を直接展開して確認
- [VERIFIED] `mcp_server/.venv/lib/.../fastmcp/server/dependencies.py` (3.2.3) — `CurrentHeaders`, `get_http_headers`, `get_http_request` の実装
- [VERIFIED] `app/jobs/handlers/langgraph_handler.py` — SystemMessage 構築の現状 (L118-134)
- [VERIFIED] `app/api/routes/chat.py` L345-385 — `delete_thread` の現在の実装
- [VERIFIED] `app/orchestrator/state.py` — `AgentState` TypedDict 現状
- [VERIFIED] `docker-compose.yml` — 既存 named volume `claude-code-outputs` パターン (L151)
- [VERIFIED] `config/mcp_tools.yaml` — ツール宣言スキーマと既存 6 ツール
- [VERIFIED] `mcp_server/server.py` — `/internal/call_tool` エンドポイントパターン

### Secondary (MEDIUM confidence)
- [CITED: pypi.org/project/markitdown/] — バージョン 0.1.5、optional extras 一覧
- [CITED: gofastmcp.com/servers/context] — FastMCP Context injection パターン、`CurrentHeaders` 使用例
- [CITED: docs/adr/0025-datetime-and-user-context-injection-into-agent-prompts.md] — SystemMessage prepend の既存パターン
- [CITED: docs/adr/0026-thread-deletion-also-removes-threads-table-row.md] — thread 削除の原子性設計

### Tertiary (LOW confidence)
- [ASSUMED] `MultiServerMCPClient` の `headers` サポート — 未テスト
- [ASSUMED] パスワード保護 PDF の exception type 名 — 実ファイルでのテスト未実施

---

## Metadata

**Confidence breakdown:**
- Standard stack (MarkItDown API): HIGH — wheel を直接展開して確認
- Architecture (FastMCP headers): MEDIUM — `CurrentHeaders()` は確認済みだが MCP client 側のヘッダー注入が [ASSUMED]
- Pitfalls: HIGH — 既存コードのパターンと照合済み
- Docker volume: HIGH — 既存 `claude-code-outputs` パターンを直接確認

**Research date:** 2026-04-21
**Valid until:** 2026-05-21 (MarkItDown は活発に更新中。30 日以内に planner が実行すること)
