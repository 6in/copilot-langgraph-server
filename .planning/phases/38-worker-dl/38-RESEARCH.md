# Phase 38: ファイル出力 — worker 生成 DL + プレビュー + ユーザー別保持 - Research

**Researched:** 2026-05-12
**Domain:** Sandbox 出力永続化 + multi-user thread storage + frontend preview renderer
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

> CONTEXT.md (`.planning/phases/38-worker-dl/38-CONTEXT.md`) の `<decisions>` ブロックを逐語コピー。Planner は **これら 19 個の locked decision を絶対に変更しない**。

### Locked Decisions

#### ストレージ規約・ライフサイクル

- **D-01:** AI 生成ファイルのパスは `/shared/thread-files/<github_login>/<thread_id>/_generated/<name>` の 3 階層。Phase 37 ADR-0048 の `thread-files` 規約を `_generated/` サブフォルダで拡張し、input (アップロード添付) と output (本 phase) を **明示的に分離** する。
- **D-02:** ライフサイクルは Phase 37 D-03 を踏襲 — thread 削除と同期で `rm -rf` (`app/api/routes/chat.py::delete_thread` の hook が親フォルダごと削除するため、新規 hook は不要)。`_generated/` 個別削除 API (DELETE) は **新設しない**。
- **D-03:** ファイル命名規則は Phase 37 D-02 と統一 — `YYYYMMDDTHHMMSS_<original>.<ext>` を必ず付ける。AI が同名ファイル (例: `output.png`) を 2 回生成しても timestamp prefix で常時 unique、履歴が `_generated/` 内に時系列で残る。
- **D-04:** Docker volume / mount mode は Phase 37 D-04 を **再利用** (既存 `thread-files` named volume: api=RW / mcp-server=RW / worker=RO)。新規 volume 追加なし。

#### API・MCP インタフェース

- **D-05:** HTTP API ルートは attachments と **分離** — `GET /api/threads/{thread_id}/outputs/{name}` を新設。認可・realpath guard は `_resolve_thread_folder` / `_safe_resolve_file` helper を `_generated/` 向けに再利用。
- **D-06:** MCP ツールは **拡張一体化** — `attachments_list` の戻り値に `kind: "user_upload" | "generated"` フィールド追加、`_generated/` 配下も含めて返す。新規 `outputs_list` ツールは作らない。
- **D-07:** ツール拡張は `config/mcp_tools.yaml` SSoT 変更 + `scripts/generate_mcp_artifacts.py --target all` 再生成 (ADR-0044)。

#### 出力永続化経路 (sandbox 内直接書き込み)

- **D-08:** `execute_python` の `cwd` を `/shared/thread-files/<github_login>/<thread_id>/_generated/` に切り替え。ヘッダ (x-thread-id / x-github-login、Phase 37 Route A) から folder path を構築。
- **D-09:** `claude_code` は `cwd` 引数を **削除** し常に `_generated/` で実行する固定仕様。引数 override 不可。overflow output (`OUTPUT_DIR=/shared/claude-code-outputs`) は debug 用 global volume として **現状維持** — `_generated/` にマージしない。
- **D-10:** timestamp prefix の付与責任は **MCP tool wrapper** が持つ。`execute_python_with_headers` / `claude_code_with_headers` の tool 実行終了後に post-process loop で `_generated/` 内の prefix 無しファイルを `{ts}_{basename}` にrename。
- **D-11:** rename 検出ロジック (snapshot diff vs mtime 判定 vs その他) は **planner 判断**。

#### UI / プレビュー

- **D-12:** プレビュー対象フォーマット — **画像 (png/jpg/gif/webp)**、**Markdown (.md)**、**CSV (テーブル)**、**プレーンテキスト系 (.txt/.log/.py/.json/.yaml 等を Monaco で syntax highlight)**。PDF は DL のみ。HTML は対象外。
- **D-13:** 表示方式は **全種類「メッセージ下のチップ一覧」+ クリックでモーダルプレビュー** で Phase 36 と統一。AI 応答テキスト内 inline 描画はしない。Phase 36 `AttachmentChipRow` を `kind` 対応に拡張して再利用。
- **D-14:** チップに「AI 生成」「添付」ラベルを表示。UI 詳細は `/gsd-ui-phase` の UI-SPEC で確定。
- **D-15:** 1 turn 内で生成された全ファイルを **AI 最終 message に metadata として bundle**。中間 tool 呼び出しの delta はチップ描画しない (turn 完了時点でまとめて反映)。Phase 36 attachments の「message に bundle」メンタルモデル踏襲。

#### 過去スレッドからの再取得 (FOUT-04)

- **D-16:** 「過去スレッドから再取得」の scope は **ThreadSidebar から該当スレッドを開き AI message に bundle されたチップから再取得** で閉じる。横断 "My Files" 画面は v6.1+ deferred。
- **D-17:** 一覧 endpoint (`GET /api/threads/{tid}/outputs`) は **新設しない**。LangGraph checkpointer で永続化された message metadata から UI が直接復元。
- **D-18:** SystemMessage prepend は **input/output 両方含む flat list、件数制限なし**。エントリは `name + size + timestamp + kind` の薄いメタデータのみ。
- **D-19:** multi-user isolation の検証は **Phase 36 で確立した isolation テストの間接的引き継ぎ**。outputs route が `_resolve_thread_folder` / `_safe_resolve_file` を経由していることをスモークテストで確認。

### Claude's Discretion

- `AgentState` の出力フィールド設計 — `attachments` 拡張 (kind フィールド) に倒すのが筋。
- D-11 rename 検出ロジック。
- AI 最終 message への metadata bundle 永続化方式 (LangGraph checkpoint の標準 message metadata 機構を使う — planner 確認)。
- `_generated/` ディレクトリ作成タイミング (handler scan 時オンデマンド `mkdir -p`)。
- AttachmentChip の `kind` ラベル文言・色味・アイコン — `/gsd-ui-phase` で確定。
- AI に見せる `attachments_list` 戻り値の表示順 (timestamp 降順 / kind 別 grouping 等)。
- MarkdownMessage.tsx は D-13 により inline 描画しない方針なので追加変更を入れない。
- 中間ファイル / 失敗 tool 呼び出しの orphan ファイル扱い (v6.1+ で GC 検討)。

### Deferred Ideas (OUT OF SCOPE)

- 個別削除 UI (`DELETE /api/threads/{tid}/outputs/{name}` + UI ボタン) — v6.1+
- 横断 "My Files" 画面 / Header dropdown — v6.1+
- timestamp prefix で溜まる古い生成ファイルの自動 GC — v6.1+
- `AgentState.outputs` 独立フィールド化 — `attachments` 拡張に倒す
- PDF プレビュー (pdf.js / iframe) — v6.1+
- HTML プレビュー — Canvas (Phase 16/18) と用途衝突
- AI に「自分が生成したファイルを更新する」メンタルモデル — v6.1+ で SystemMessage hint 検討
- 中間ファイル orphan GC — v6.1+
- CSV / Table 行数上限 (1000 行超え時 summary) — UI 観察次第で UI-SPEC に書く
- 画像サムネ生成 — Phase 36 D-23 同様やらない (raw bytes 配信)
- AI 生成完了の toast / 通知 — v6.1+
- `session-state/files/` paths が AI 応答テキストに残ったときの自動マッピング — D-13 で inline 描画しない方針
- MCP `outputs_list` / `outputs_read` 単独ツール化 — `attachments_list` 拡張に倒す
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FOUT-01 | execute_python sandbox で生成されたファイル（PDF / 画像 / CSV 等）をユーザーがチャット UI からダウンロードできる | Standard Stack §1 (cwd 切替) + Pattern 1 (post-process rename) + Pattern 4 (outputs route) |
| FOUT-02 | claude_code 実行の workspace 成果物をユーザーがチャット UI から取得できる | Standard Stack §2 (claude_code cwd 引数削除) + Pattern 1 (post-process rename) |
| FOUT-03 | 生成ファイル（画像・CSV・Markdown 等）をダウンロードせずにチャット画面上でプレビューできる | Standard Stack §6-9 (renderer 選定) + Pattern 6 (extension → renderer mapping) |
| FOUT-04 | 生成ファイルがユーザー別ストレージに保持され、過去の生成成果を一覧・再取得できる | Pattern 2 (LangGraph checkpoint で AIMessage.additional_kwargs 永続化) + Pattern 3 (SystemMessage prepend kind 拡張) |
</phase_requirements>

## Summary

Phase 38 は Phase 36 (アップロード添付 = 入力側) と Phase 37 (PDF/Office MCP 抽出 + thread-files 規約 ADR-0048) のレールに完全に乗る薄いレイヤーである。新規アーキテクチャは存在せず、研究の中心は「locked decision の中で複数手段から1つを推薦すべき点」と「既存 helper のどの行を再利用してどこをコピーするか」の特定である。

**主要発見:**

1. **D-11 rename 検出**: snapshot diff (before/after `os.listdir`) を推奨。理由は CONTEXT.md `<specifics>` の「中間ファイル・既存ファイル更新・部分失敗に強い」要件、`shutil.rmtree` ロールバックや mtime 比較の OS 依存性回避、そして実装行数が最小 (≦ 20 LOC)。
2. **D-12 / D-13 プレビュー基盤**: 必要な依存ライブラリは **すべて既存導入済** — `@monaco-editor/react@4.7.0` (MarkdownMessage が既に使用)、`ag-grid-community@35.2.1` + `ag-grid-react` (`ChatAgGridTable.tsx` 既存)、`react-markdown@10.1.0` + `remark-gfm@4.0.1` (MarkdownMessage)。Phase 38 では新規 npm install ゼロで全 renderer が組める。
3. **D-15 message bundle**: Phase 36 が既に `HumanMessage.additional_kwargs.attachments` を **AsyncPostgresSaver JSONB に round-trip 検証済** (patterns.md 「HumanMessage.additional_kwargs サイドカー envelope」)。AI 最終 message にも同 envelope を使えば `AIMessage.name` 喪失問題 (ADR-0038) と無関係、API 側 `_messages_to_response` (`app/api/routes/chat.py:481-490`) も既に `additional_kwargs.attachments` を透過返却している。
4. **D-09 claude_code cwd 引数削除の影響範囲**: `mcp_server/tools/claude_code.py` 内部 + `mcp_helper.py` 自動生成のみ。`config/mcp_tools.yaml` には `claude_code` の python_wrapper があるか確認すると **cwd を MCP tool 引数として公開していない** ため、外部 caller (agent / sandbox) からの破壊変更ゼロ。
5. **D-06 MCP YAML 変更**: `config/mcp_tools.yaml:160-182` の `attachments_list` python_wrapper docstring に `kind` フィールドを追記するだけ。スキーマフィールドそのものは型注釈 `list[dict]` のまま (型は dict なので拡張時に schema breakage なし)。
6. **既存リソースの再利用度**: 新規ファイル想定 1 個 (`app/api/routes/outputs.py`)、変更想定 7 ファイル前後。コードベース重量級モジュールはほぼゼロ — 「薄いレイヤー」の評価は正確。

**Primary recommendation:** D-11 = snapshot diff、`outputs.py` を新規追加 (attachments.py へ追記より分離が patterns.md `Backward Compatibility` 原則と整合)、AttachmentChipRow 拡張で全プレビューを賄う、AIMessage `additional_kwargs.attachments` (kind=generated) で metadata bundle、smoke test は既存 isolation テストの helper 経由再利用を assert する 1 ファイルで足りる。

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 生成ファイル永続化 (cwd 切替) | mcp-server (MCP tool wrapper) | — | execute_python / claude_code subprocess の cwd を変えるのは MCP tool 層、worker は RO mount でアクセスのみ |
| post-process rename | mcp-server (MCP tool wrapper) | — | snapshot diff は subprocess 完了直後に走る必要があり tool wrapper のスコープ |
| timestamp prefix 命名 | mcp-server (MCP tool wrapper) | — | D-10 で wrapper 責任明示 (AI プロンプト依存ゼロ) |
| DL HTTP route | api (FastAPI) | — | Phase 36 と同じく JWT cookie 認証は api 側でのみ可能 |
| MCP 戻り値 `kind` 付与 | mcp-server (`attachments.py`) | — | scan + kind マークは MCP tool 層 |
| SystemMessage prepend (kind 拡張) | api/worker (langgraph_handler) | — | LangGraph 入口 = handler が scan して prompt 組み立て |
| AIMessage metadata bundle | api/worker (langgraph_handler) | — | turn 完了タイミング = LangGraph end イベント (handler) |
| プレビュー renderer (画像/MD/CSV/text) | frontend (browser) | — | バイナリは API 経由で raw bytes 取得、レンダリングは全てクライアント |
| チップ kind ラベル表示 | frontend (`AttachmentChipRow`) | — | UI 装飾は frontend スコープ |
| user isolation (realpath guard) | api (`_resolve_thread_folder`) | — | JWT payload → folder 解決は api 側のみ実装、Phase 36 で確立済 |
| Persistence (DB JSONB checkpoint) | postgres (langgraph-checkpoint-postgres) | — | `additional_kwargs` は AsyncPostgresSaver に透過保存される |

## Project Constraints (from CLAUDE.md)

> 以下は CLAUDE.md から抽出した actionable directive。Plan / 実装で逸脱しないこと。

- **応答言語**: すべての応答は日本語（コード・コマンド・ファイルパス・固有名詞は英語可）。GSD バナーやチェックポイントも日本語。
- **GSD Workflow 必須**: Edit/Write を行う前に GSD コマンド (`/gsd:execute-phase` 等) から作業を開始。**ブランチ必須** (main で直接コミットしない)。
- **Squash Merge**: main へのマージは必ず `git merge --squash`。Fast-forward / `--no-edit` 禁止。
- **worktree マージ前安全確認**: 削除行数 > 追加行数×2、アプリコード削除がある場合は手動精査。
- **MCP Tool Catalog 境界 (Phase 30, ADR-0044)**:
  - **手書き**: `config/mcp_tools.yaml`, `mcp_server/tools/<name>.py`, `mcp_server/tools/mcp_helper_utils.py`, `static/js/iframe-rpc.js`, `docs/mcp-tool-add-manual.md`
  - **自動生成** (DO NOT EDIT ヘッダー付): `mcp_server/tools/mcp_helper.py`, `static/js/tool-catalog-generated.js`, `docs/mcp-tools.md`
  - 自動生成ファイルを手で触ると pre-commit hook の drift 検知 (`scripts/generate_mcp_artifacts.py --check`) が commit をブロック。修正は `--target all` 再実行で再ステージ。
- **ADR INDEX**: `docs/adr/INDEX.md` は `scripts/generate_adr_index.py` で自動生成 (pre-commit hook)。新規 ADR を追加したら `.planning/adr-categories.yaml` にも番号とカテゴリ追記。
- **patterns.md 手動更新**: 新規 ADR で記録すべきパターンがあれば `.planning/patterns.md` に**手動追記** (D-15)。自動生成しない。
- **GSD-Discuss canonical_refs**: `/gsd-discuss-phase` 実行時は `.planning/patterns.md` と `docs/adr/INDEX.md` を canonical_refs に必ず追加 (本 phase の CONTEXT.md には既に記載済)。
- **Docker compose で起動**: 直接 uvicorn / bun run dev 不使用。dev URL は `http://localhost:5173/orochi/`。
- **pre-commit hook インストール**: 新規 clone 直後は `bash scripts/install-hooks.sh` 必須 (ADR INDEX + MCP drift の両方)。

## Standard Stack

### Core (Backend — Python)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12 | ランタイム | プロジェクト固定 [VERIFIED: pyproject.toml] |
| FastAPI | >=0.135.2 | HTTP route (`/api/threads/{tid}/outputs/{name}`) | 既存 attachments route の同居 [VERIFIED: pyproject.toml] |
| FastMCP | >=2.14.0,<4.0 | MCP tool wrapper (execute_python / claude_code / attachments_list) | Phase 20 ADR-0020 で確定 [VERIFIED: pyproject.toml] |
| langgraph | >=1.1.4 | message bundle 保持 + checkpoint 永続化 | Phase 02-graph-layer 以降 [VERIFIED: pyproject.toml] |
| langgraph-checkpoint-postgres | >=3.0.5 | `additional_kwargs` JSONB round-trip | Phase 36 Wave 0 で round-trip 検証済 [VERIFIED: pyproject.toml + patterns.md L94-99] |
| psycopg[binary] | >=3.2.0 | DB アクセス | 既存 [VERIFIED: pyproject.toml] |
| PyJWT | >=2.9.0 | JWT cookie 認証 | 既存 attachments route が利用 [VERIFIED: pyproject.toml] |
| pytest / pytest-asyncio | >=8.0 / >=0.25 | テスト | 既存 [VERIFIED: pyproject.toml] |

### Core (Frontend — TypeScript / React)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | ^19.2.4 | UI | プロジェクト固定 [VERIFIED: frontend/package.json] |
| @monaco-editor/react | ^4.7.0 | プレーンテキスト系プレビュー (read-only + syntax highlight) | `MarkdownMessage` が既に使用、コードブロックレンダリング基盤 [VERIFIED: frontend/package.json L17 + MarkdownMessage.tsx L10] |
| react-markdown | ^10.1.0 | Markdown プレビュー | `MarkdownMessage` が既に使用 [VERIFIED: frontend/package.json L20 + MarkdownMessage.tsx L8] |
| remark-gfm | ^4.0.1 | GFM テーブル・タスクリスト | 既存 `MarkdownMessage` 経路 [VERIFIED: frontend/package.json L22] |
| ag-grid-community | ^35.2.1 | CSV テーブル描画 | `ChatAgGridTable.tsx` で MIT community 版を実装済 (lazy load) [VERIFIED: frontend/package.json L14 + ChatAgGridTable.tsx] |
| ag-grid-react | ^35.2.1 | React wrapper | 同上 [VERIFIED: frontend/package.json L15] |

### Supporting (Don't add — already there)
**新規 npm install は不要。CSV パースは ag-grid に直接渡せる行列に整形する 1 関数で足りる (papaparse 不要)。**

理由:
1. CSV は通常 RFC 4180 準拠 (カンマ区切り + 改行 + ダブルクォート escape) で、ad-hoc な split + 簡易 quote 処理で 95% のケースは賄える
2. CSV プレビューは AI 生成成果物 (worker output) なので well-formed が期待できる (ユーザー手入力ではない)
3. 万一 edge case (multiline quoted cells) で問題が出れば v6.1+ で papaparse 追加 (8KB gzip) を再検討

CSV 行数上限は D-12 で Deferred 扱い、ag-grid 自体の virtual scroll で 10k 行までは耐える。

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| @monaco-editor/react | highlight.js + `<pre>` | bundle 軽量だが Monaco が既に load されている (sunk cost zero)、search/折りたたみ等の UX を捨てる |
| ag-grid-community | papaparse + `<table>` | 行数上限と sort/filter UX を捨てる、新規 dep 必要 |
| react-markdown 再使用 | AttachmentModal 内で別 instance | `MarkdownMessage` は AI 応答全文向けに heavy なツリー (Monaco code block 等) を含むため、preview 用には react-markdown を直接呼ぶ薄ラッパーが軽い |
| AIMessage.additional_kwargs | AgentState.outputs 独立フィールド | LangGraph checkpoint で AIMessage.name が落ちる既知問題 (ADR-0038) と隣接するため不安あり。**ただし additional_kwargs は別系統で round-trip 検証済 (patterns.md L82)** — 安全。AgentState 拡張だと API `_messages_to_response` の改修が必要、Phase 36 の対称形が崩れる |

**Installation:** N/A — 新規依存ゼロ。

**Version verification (2026-05-12 確認):**
- `@monaco-editor/react@4.7.0` (latest published version) [VERIFIED: npm view]
- `ag-grid-community@35.2.1` (latest in 35.x line) [VERIFIED: npm view]
- `papaparse@5.5.3` (参考、本 phase では追加しない) [VERIFIED: npm view]

## Architecture Patterns

### System Architecture Diagram

```
[User Chat UI]
     │ POST /api/chat (prompt + thread_id + attachments?)
     ▼
[FastAPI api]──enqueue──▶[Redis (arq)]──▶[Worker]
     │                                       │
     │                                       │ task_type=langgraph
     │                                       ▼
     │                                [LangGraphHandler]
     │                                       │
     │                                       │ scan _generated/ + SystemMessage prepend
     │                                       │ (kind=user_upload | generated, flat list)
     │                                       │
     │                                       │ graph.astream_events()
     │                                       ▼
     │                                [LangGraph StateGraph]
     │                                       │
     │                                       │ tool_call (execute_python / claude_code)
     │                                       │ via streamable_http
     │                                       ▼
     │                              [mcp-server (MCP tools)]
     │                                       │
     │                                       │ cwd = /shared/thread-files/<login>/<tid>/_generated
     │                                       │
     │                                       ▼
     │                              [subprocess: python3 -c / claude --print]
     │                                       │   writes output.png 等 to cwd
     │                                       │
     │                                       ▼
     │                              [tool wrapper post-process]
     │                                       │   snapshot diff: list new files
     │                                       │   rename → {ts}_{name}
     │                                       │
     │                                       ▼
     │                              [shared/thread-files volume]
     │                                       │
     │                                       │ (api=RW, mcp=RW, worker=RO)
     │                                       │
     │ ◀──turn end (on_chain_end LangGraph)──┘
     │
     │ scan delta of _generated/, attach to AIMessage.additional_kwargs.attachments
     │ (kind=generated, name=<ts>_..., size, ext)
     │
     │ checkpoint via AsyncPostgresSaver (JSONB)
     │
[GET /api/job/{id}] ◀────────── result + SSE done signal
     │
     │ frontend hydrate AIMessage with additional_kwargs.attachments
     │
[AttachmentChipRow (kind="generated")]
     │ on click
     ▼
[AttachmentModal: image / markdown / csv / monaco-text renderer]
     │ raw bytes via:
     ▼
[GET /api/threads/{tid}/outputs/{name}]
     │ (JWT cookie + _resolve_thread_folder + _safe_resolve_file)
     ▼
[FileResponse from /shared/thread-files/<login>/<tid>/_generated/<name>]

Persistence:
  - Files: thread-files named volume
  - Message metadata: postgres (langgraph_checkpoints, JSONB)
  - Cleanup: thread delete hook (chat.delete_thread → shutil.rmtree, ADR-0048)
```

### Component Responsibilities

| File | Role | New / Modified |
|------|------|----------------|
| `mcp_server/tools/execute_python.py` | cwd を `_generated/` に切替、wrapper に post-process rename | **Modified** |
| `mcp_server/tools/claude_code.py` | `cwd` 引数削除 + 同上 | **Modified** (シグネチャ破壊) |
| `mcp_server/tools/attachments.py` | scan に `_generated/` 含める、`kind` フィールド付与 | **Modified** |
| `config/mcp_tools.yaml` | `attachments_list.returns` の docstring に `kind` 追記 | **Modified** |
| (auto-generated) `mcp_server/tools/mcp_helper.py` | `--target all` で再生成 | **Regenerated** |
| (auto-generated) `static/js/tool-catalog-generated.js` | 同上 | **Regenerated** |
| (auto-generated) `docs/mcp-tools.md` | 同上 | **Regenerated** |
| `app/api/routes/outputs.py` | `GET /api/threads/{tid}/outputs/{name}` | **NEW** |
| `app/api/main.py` | outputs router include | **Modified** (1 行) |
| `app/jobs/handlers/attachments_helper.py` | scan に `_generated/` 含め `kind` 付与 | **Modified** |
| `app/jobs/handlers/langgraph_handler.py` | turn 完了時の `_generated/` delta scan → AIMessage `additional_kwargs.attachments` | **Modified** |
| `app/orchestrator/state.py` | `AttachmentMeta` 相当に `kind` 追加 (型コメント) | **Modified** (型注釈のみ) |
| `frontend/src/types.ts` | `AttachmentMeta` に `kind?: 'user_upload' \| 'generated'` 追加 | **Modified** |
| `frontend/src/components/MessageArea.tsx` | `AttachmentChipRow` に `kind` 対応 (ラベル表示) | **Modified** |
| `frontend/src/components/AttachmentModal.tsx` | **NEW** モーダル + 4 種 renderer (image / markdown / csv / monaco-text) | **NEW** |
| `frontend/src/hooks/useAttachments.ts` (or new hook) | `kind` ベースで URL を `/attachments/` or `/outputs/` に振り分けるヘルパー | **Modified** |
| `tests/test_outputs_route.py` | GET 認可 / 404 / path traversal / isolation スモークテスト | **NEW** |
| `tests/test_mcp_attachments_kind.py` | `attachments_list` が `kind` を返す + `_generated/` を含む | **NEW** |
| `tests/test_post_process_rename.py` | snapshot diff の rename ロジックを単体テスト | **NEW** |
| `tests/test_langgraph_handler_outputs_bundle.py` | turn 完了で AIMessage に metadata bundle される | **NEW** |
| `docs/adr/0052-worker-generated-outputs-storage-and-preview.md` (案) | ADR 化 | **NEW** (任意、phase wrap-up で判断) |
| `docker-compose.yml` | **変更なし** | unchanged |

### Recommended Project Structure
既存ツリー踏襲。追加は以下のみ:
```
app/api/routes/outputs.py     # NEW
frontend/src/components/
  AttachmentModal.tsx         # NEW
  preview/                    # NEW (フォルダ、renderer 4 種を分離)
    ImagePreview.tsx
    MarkdownPreview.tsx
    CsvPreview.tsx
    TextPreview.tsx
tests/
  test_outputs_route.py       # NEW
  test_mcp_attachments_kind.py
  test_post_process_rename.py
  test_langgraph_handler_outputs_bundle.py
```

### Pattern 1: Post-process Rename (snapshot diff 推奨)

**What:** Tool 実行終了後に `_generated/` 内の新規ファイルだけを `{ts}_{basename}` にリネーム。

**When to use:** D-10 / D-11。`execute_python_with_headers` と `claude_code` の register_tools wrapper 内。

**Recommended approach: snapshot diff (before/after listdir).** 理由:
- AI が `open("output.png", "w")` を実行した直後の **新規** ファイルだけが対象になり、既存ファイル (前 turn の生成物) の mtime が変わっても誤って rename されない (mtime 判定の脆さを回避)
- subprocess が複数ファイルを同時生成しても確実に網羅できる
- 失敗時 (例: rename 中に SIGKILL) も before snapshot が再 invocation 時の reference になりオーケストレーション複雑度が低い
- 実装が短い (≦ 20 LOC)

**Counter-options 評価:**
- **mtime 判定** (実行開始時刻より新しい mtime): OS の `mtime` 解像度差・clock skew で稀に取りこぼし。Linux ext4 で nanosec 解像度はあるが Docker volume を NFS / 9p で mount すると 1s 解像度に落ちるケース報告あり。
- **timestamp regex で「未 prefix」判定**: AI が `20260601T120000_foo.png` を直接書いた場合と区別不能。
- **inotify**: Linux 専用 / overkill。

**Pseudo-implementation:**

```python
# mcp_server/tools/execute_python.py の register_tools 内 wrapper
import datetime
import os

def _utc_ts() -> str:
    return datetime.datetime.now(tz=datetime.timezone.utc).strftime("%Y%m%dT%H%M%S")

def _rename_new_outputs(folder: str, before: set[str]) -> list[str]:
    """before snapshot との diff で新規ファイルを {ts}_{name} にリネーム。
    返り値は最終的なファイル名一覧 (renamed)。"""
    if not os.path.isdir(folder):
        return []
    ts = _utc_ts()
    after = set(os.listdir(folder))
    new_files = sorted(after - before)
    renamed: list[str] = []
    for name in new_files:
        src = os.path.join(folder, name)
        if not os.path.isfile(src):
            continue
        # 既に ts prefix 付きならスキップ (AI が D-03 規約で書いたケース)
        if len(name) >= 16 and name[:8].isdigit() and name[8] == "T" and name[9:15].isdigit() and name[15] == "_":
            renamed.append(name)
            continue
        dst_name = f"{ts}_{name}"
        dst = os.path.join(folder, dst_name)
        os.rename(src, dst)
        renamed.append(dst_name)
    return renamed

# wrapper 内:
async def execute_python_with_headers(code, timeout=60, headers=CurrentHeaders()) -> dict:
    folder = _resolve_generated_folder(headers)   # 後述 (D-08)
    os.makedirs(folder, exist_ok=True)
    before = set(os.listdir(folder)) if os.path.isdir(folder) else set()
    result = await execute_python(code, timeout=timeout, headers=headers,
                                  cwd_override=folder)   # 後述 (D-08)
    result["generated_files"] = _rename_new_outputs(folder, before)
    return result
```

**Source:** D-11 で planner 判断とされた領域。検出ロジックの推奨は本 RESEARCH.md 独自結論 [ASSUMED: snapshot diff が mtime 判定より堅牢 — 業界一般則だが本プロジェクト固有 benchmark なし]。

### Pattern 2: AIMessage.additional_kwargs.attachments で AI 生成ファイルを turn 単位で bundle (D-15)

**What:** turn 完了時 (on_chain_end イベント) に `_generated/` の delta を AIMessage の `additional_kwargs.attachments` に書き戻し、AsyncPostgresSaver で永続化。

**Why this works:** patterns.md §"HumanMessage.additional_kwargs サイドカー envelope" (L79-85) で確立済のパターンを AIMessage 側に適用するだけ。Phase 36 Wave 0 で `additional_kwargs` が AsyncPostgresSaver JSONB に round-trip 保存されることが検証済 (`AIMessage.name` 喪失問題 ADR-0038 とは別系統)。

**Where to insert:** `app/jobs/handlers/langgraph_handler.py:236-241`、`final_state` を確定する直前後。

```python
# 既存 (L228-241):
state_input = {"messages": messages_input, "attachments": attachments_meta or None}
final_state = None
async for event in graph.astream_events(state_input, config=config, version="v2"):
    kind = event.get("event")
    if kind == "on_chat_model_stream":
        ...
    elif kind == "on_chain_end" and event.get("name") == "LangGraph":
        final_state = event["data"].get("output")

if final_state is None:
    final_state = await graph.ainvoke(state_input, config=config)

# === Phase 38 追加 ===
# 1. turn 完了後に _generated/ の delta を scan
before_generated_set = set(...)   # 注意: turn 開始時の snapshot は handler ではなく
                                  # 各 tool wrapper 内 (Pattern 1) で取られる。
                                  # handler レベルでは turn 開始時の listdir を取り、
                                  # turn 終了時の listdir との diff を AIMessage に bundle する。
                                  # tool wrapper 側の rename と二重カウントにならないよう
                                  # 「kind=generated の全 file を SystemMessage prepend と同じ scan で取り直す」
                                  # 設計が一番安全 (実装簡素・冪等)。
generated_now = scan_generated_subfolder(thread_id, github_login)  # 新 helper
turn_delta = [f for f in generated_now if f["name"] not in {a["name"] for a in attachments_meta or []}]
# (turn_delta は kind=generated のみ抽出済)

# 2. final AIMessage に bundle
if turn_delta:
    final_msg = final_state["messages"][-1]
    final_msg.additional_kwargs = (final_msg.additional_kwargs or {}) | {
        "attachments": turn_delta,  # AttachmentMeta 形式 + kind="generated"
    }
    # AsyncPostgresSaver が次の checkpoint で JSONB として保存する
```

**Note:** API `_messages_to_response` (`app/api/routes/chat.py:481-490`) は **既に `additional_kwargs.attachments` を透過返却している**。frontend は何も変更せずとも AI 側の bundle を受け取れる (型は `AttachmentMeta` に `kind` field を追加するのみ)。

**Source:**
- patterns.md §"HumanMessage.additional_kwargs サイドカー envelope" [VERIFIED: .planning/patterns.md L79-85]
- ADR-0050 [CITED: docs/adr/0050-copilot-sdk-multimodal-attachments.md]
- Pattern 3 (Wave 0 risk-gate) [VERIFIED: .planning/patterns.md L94-99] — round-trip 検証は Phase 36 で既に済んでいるため Phase 38 では new Wave 0 risk なし

### Pattern 3: SystemMessage Prepend の kind 拡張 (D-18)

**What:** Phase 37 D-11 の `scan_thread_attachments` + `build_attachments_hint` (`app/jobs/handlers/attachments_helper.py`) を以下に拡張:

- scan 対象を thread folder 直下 + `_generated/` の両方
- 各エントリに `kind: "user_upload" | "generated"` フィールド付与
- `build_attachments_hint` の出力に kind を表示 (例: `- output.png (12.3KB, .png) [AI 生成]`)

**Why:** AI から見た「現在 thread にあるファイル一覧」を flat に統一 (Phase 38 specifics 「`kind` フィールドを single discriminator として通す」)。AI は `attachments_extract` (PDF / Office のみ) と `attachments_list` (両方) を引数なしで呼べる API のまま、kind を識別できる。

**Implementation sketch:**

```python
# app/jobs/handlers/attachments_helper.py
def scan_thread_attachments(thread_id, github_login):
    if not thread_id or not github_login: return []
    folder = os.path.join(THREAD_FILES_DIR, github_login, thread_id)
    result = []
    # 1. user uploads (直下)
    if os.path.isdir(folder):
        for fname in sorted(os.listdir(folder)):
            fpath = os.path.join(folder, fname)
            if os.path.isfile(fpath) and not os.path.islink(fpath):
                stat = os.stat(fpath)
                ext = os.path.splitext(fname)[1].lower()
                result.append({
                    "name": fname, "size": stat.st_size,
                    "modified_at": float(stat.st_mtime),
                    "ext": ext, "kind": "user_upload",
                })
    # 2. generated (_generated/ 配下)
    gen_folder = os.path.join(folder, "_generated")
    if os.path.isdir(gen_folder):
        for fname in sorted(os.listdir(gen_folder)):
            fpath = os.path.join(gen_folder, fname)
            if os.path.isfile(fpath) and not os.path.islink(fpath):
                stat = os.stat(fpath)
                ext = os.path.splitext(fname)[1].lower()
                result.append({
                    "name": fname, "size": stat.st_size,
                    "modified_at": float(stat.st_mtime),
                    "ext": ext, "kind": "generated",
                })
    return result
```

**Source:** Phase 37 D-11 の attachments_helper.py L15-42 の延長 [VERIFIED: app/jobs/handlers/attachments_helper.py]。

### Pattern 4: `GET /api/threads/{tid}/outputs/{name}` ルート (D-05)

**What:** Phase 36 `get_attachment` (`app/api/routes/attachments.py:172-194`) をそのままコピー → `folder` 解決時に `_generated/` を append。

**Recommendation:** `app/api/routes/outputs.py` を **新規ファイル** として作成 (attachments.py 追記より分離が好ましい)。

**Rationale (分離 vs 追記):**

| 観点 | 新規 outputs.py | attachments.py 追記 |
|------|-----------------|---------------------|
| LOC | 約 50 行 (helper import + route 1 個) | 同等 |
| 既存テスト影響 | ゼロ (`test_attachments_get_delete_route.py` は無関係) | 同居でテストが厚くなる |
| Tag / Router 分離 | `tags=["outputs"]` で OpenAPI 上きれい | tags 1 個に混在 |
| import 循環 | helper を attachments.py から import するだけ、循環なし | 増設のみ |
| **推奨理由** | Phase 38 の責務 (出力側) が attachments (入力側) と分離して読める | — |

**Implementation sketch (約 50 行):**

```python
# app/api/routes/outputs.py
"""Phase 38 D-05: GET /api/threads/{tid}/outputs/{name} — AI 生成ファイル DL/preview."""
import logging
import mimetypes
import os
from fastapi import APIRouter, Depends, HTTPException, Path, Request
from fastapi.responses import FileResponse

from app.api.routes.attachments import (
    _resolve_thread_folder,
    _safe_resolve_file,
    _normalize_basename,
)
from app.api.routes.chat import get_jwt_payload

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["outputs"])


@router.get("/threads/{thread_id}/outputs/{name}")
async def get_output(
    request: Request,
    thread_id: str = Path(...),
    name: str = Path(..., description="storage name (timestamp prefix)"),
    payload: dict = Depends(get_jwt_payload),
):
    """AI 生成ファイルを JWT 認証下で inline 配信。"""
    github_login = payload.get("github_login", "unknown")
    thread_folder = _resolve_thread_folder(github_login, thread_id)
    gen_folder = os.path.join(thread_folder, "_generated")
    # realpath guard は _resolve_thread_folder が thread_folder については保証済 →
    # _safe_resolve_file に gen_folder を渡して二重防御
    safe_path = _safe_resolve_file(gen_folder, name)
    if not os.path.isfile(safe_path):
        raise HTTPException(status_code=404, detail="output not found")
    mime, _ = mimetypes.guess_type(name)
    return FileResponse(
        safe_path,
        media_type=mime or "application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{_normalize_basename(name)}"'},
    )
```

`app/api/main.py` で `from app.api.routes import outputs` + `app.include_router(outputs.router)` を 2 行追加。

**Source:** `app/api/routes/attachments.py:172-194` [VERIFIED: ファイル直接読み込み]。

### Pattern 5: execute_python の cwd 切替 (D-08)

**Current (`mcp_server/tools/execute_python.py:151-158`):**
```python
proc = await asyncio.create_subprocess_exec(
    "python3", "-c", code,
    stdout=..., stderr=..., cwd="/tmp",
    env=sanitized_env, preexec_fn=_set_limits,
)
```

**Recommended change:**

```python
# Phase 38 D-08: cwd = /shared/thread-files/<login>/<tid>/_generated/
THREAD_FILES_DIR = os.environ.get("THREAD_FILES_DIR", "/shared/thread-files")

def _resolve_generated_folder(headers: dict | None) -> str:
    """ヘッダから _generated/ folder path を構築。
    thread_id / github_login が無ければ /tmp に fallback (D-08 fallback policy)。"""
    h = headers or {}
    tid = h.get("x-thread-id") or ""
    login = h.get("x-github-login") or ""
    if not tid or not login:
        return "/tmp"
    folder = os.path.join(THREAD_FILES_DIR, login, tid, "_generated")
    real = os.path.realpath(folder)
    base = os.path.realpath(THREAD_FILES_DIR)
    if not real.startswith(base + os.sep):
        return "/tmp"   # path traversal 検出時も /tmp に fallback
    return real

async def execute_python(code, timeout=60, headers=None) -> dict:
    ...
    cwd = _resolve_generated_folder(headers)
    os.makedirs(cwd, exist_ok=True)
    proc = await asyncio.create_subprocess_exec(
        "python3", "-c", code,
        stdout=..., stderr=...,
        cwd=cwd,
        env=sanitized_env, preexec_fn=_set_limits,
    )
    ...
```

**Fallback rationale:** "thread_id ヘッダ未送信" 時に `/tmp` 維持を推奨。理由:
- Phase 31 / Phase 37 の RPCContext 伝搬は基本動作だが、test / spike / 直接呼び出しなど想定外経路では headers が空のまま到達する
- error にすると既存単体テスト (`tests/test_execute_python*.py` 等) が全滅
- /tmp は subprocess 標準で書き込み可、過去動作と完全互換

**path traversal:** ヘッダから組み立てる `folder` に `../` を含む文字列が入ったケースは realpath prefix guard で検出 → /tmp に縮退 (route 側より緩い fallback だが MCP tool は内部 RPC 経路で外部 input ではないため許容範囲)。

**Source:** ヘッダ伝搬は `mcp_server/tools/execute_python.py:139-148` で実装済 (Phase 37 Route A) [VERIFIED]。

### Pattern 6: claude_code の cwd 引数削除 (D-9)

**Current (`mcp_server/tools/claude_code.py:55`):**
```python
async def claude_code(prompt: str, cwd: str = "/tmp") -> dict:
```

**Change:** `cwd` 引数を削除。register_tools wrapper で headers を受け取り、Pattern 5 と同じ `_resolve_generated_folder` で組み立てる。overflow output (`CLAUDE_CODE_OUTPUT_DIR=/shared/claude-code-outputs`) は **触らない** (D-09)。

**Call sites to update:**
- `mcp_server/tools/claude_code.py:55, 74, 135-136` (関数定義 + 実装内 + register_tools)
- `config/mcp_tools.yaml:123` (`claude_code` の python_wrapper) — wrapper があれば args から `cwd` を削除
- `mcp_server/tools/mcp_helper.py` (自動生成) — `--target all` 再生成で吸収

**grep 結果 (CONTEXT.md preview):** `app/` / `agents/` / `scripts/` には `claude_code` の直接呼び出しなし [VERIFIED: 上で grep 実行、ヒット数 0]。MCP tool は `MultiServerMCPClient.get_tools()` 経由でしか呼ばれないため、cwd 引数を渡している外部 caller はゼロ。**破壊変更だが影響範囲は局所** (CONTEXT.md specifics の判断と一致)。

**Source:** `mcp_server/tools/claude_code.py` [VERIFIED: 上記読み込み]。

### Pattern 7: MCP YAML 拡張 + 自動生成再実行 (D-06 / D-07)

**What:** `config/mcp_tools.yaml:160-182` の `attachments_list` の `python_wrapper` セクションに **docstring を更新** (戻り値の dict が `kind` を含む旨を追記)。

**Schema impact:** YAML スキーマには `kind` を表現する明示的なフィールドが **ない** (`returns` は `return_type: "list[dict]"` という型注釈文字列のみ)。よって YAML 上の変更は docstring の更新だけで足り、`scripts/generate_mcp_artifacts.py` の構造変更は不要。

```yaml
# 編集後 (config/mcp_tools.yaml:160-182):
  - name: attachments_list
    description: 現在の thread の添付ファイル + AI 生成ファイルの一覧を返す  # 文言更新
    privileged: false
    sandbox_exposed: true
    python_wrapper:
      function_name: list_attachments
      args: []
      return_type: "list[dict]"
      docstring: |
        thread にある添付ファイル (user_upload) と AI 生成ファイル (generated) の一覧を返す。
        引数なし (thread は RPCContext 解決)。

        Returns:
            [{"name": "...", "size": N, "modified_at": <float epoch sec>,
              "ext": "...", "mime_type": "...",
              "kind": "user_upload" | "generated"}, ...]
            ファイルが存在しない場合は []

        Example:
            from mcp_helper import list_attachments
            files = list_attachments()
            for f in files:
                print(f["name"], f["kind"], f["size"])
      mcp_args_mapping: {}
      result_transform:
        mode: passthrough
```

**Regenerate:**
```bash
python3 scripts/generate_mcp_artifacts.py --target all
git diff --stat   # mcp_helper.py / tool-catalog-generated.js / docs/mcp-tools.md が更新
git add config/mcp_tools.yaml mcp_server/tools/mcp_helper.py static/js/tool-catalog-generated.js docs/mcp-tools.md
```

**Caller 互換性:**
- `attachments_list` は handler の SystemMessage prepend と sandbox 内 AI prompt で消費されるが、両方とも dict の追加フィールドには寛容 (key を pick して使うのみ)。
- `attachments_extract` は触らない (PDF/Office 抽出 = user_upload のみ対象)。
- 既存テスト `tests/test_attachments_list.py` は `kind` field の assertion を追加 (新規ケース1個)。

**Source:** Phase 30 ADR-0044 [CITED: docs/adr/0044-mcp-tool-catalog-single-source-of-truth.md] + CLAUDE.md §"MCP Tool Catalog (Phase 30)"。

### Pattern 8: AttachmentChipRow の kind 対応 + AttachmentModal (D-13 / D-14)

**What:** `frontend/src/components/MessageArea.tsx:52-115` の `AttachmentChipRow` を以下に拡張:
1. 各チップに kind ラベル (例: `[添付]` / `[AI 生成]`) を表示
2. クリック時に `AttachmentModal` を開く

**Rationale (re-render vs URL switching):** チップの kind に応じて URL prefix が `/api/threads/{tid}/attachments/{name}` または `/api/threads/{tid}/outputs/{name}` に分岐する。フックは小さくなる:

```ts
function buildFileUrl(threadId: string, name: string, kind: 'user_upload' | 'generated'): string {
  const base = (import.meta.env.VITE_APP_BASE ?? '').replace(/\/$/, '');
  const segment = kind === 'generated' ? 'outputs' : 'attachments';
  return `${base}/api/threads/${encodeURIComponent(threadId)}/${segment}/${encodeURIComponent(name)}`;
}
```

**Modal structure (`AttachmentModal.tsx` 新規):**

```tsx
type PreviewKind = 'image' | 'markdown' | 'csv' | 'text' | 'unsupported';

function classify(ext: string): PreviewKind {
  const e = ext.toLowerCase().replace(/^\./, '');
  if (['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(e)) return 'image';
  if (e === 'md' || e === 'markdown') return 'markdown';
  if (e === 'csv' || e === 'tsv') return 'csv';
  if (['txt', 'log', 'py', 'js', 'ts', 'tsx', 'jsx', 'html', 'css',
       'json', 'yaml', 'yml', 'toml', 'xml', 'sh', 'sql'].includes(e)) return 'text';
  return 'unsupported';   // PDF など → DL のみ
}

export function AttachmentModal({ attachment, threadId, onClose }: Props) {
  const url = buildFileUrl(threadId, attachment.name, attachment.kind);
  const kind = classify(attachment.ext);
  return (
    <Overlay onClose={onClose}>
      {kind === 'image' && <ImagePreview url={url} alt={attachment.name} />}
      {kind === 'markdown' && <MarkdownPreview url={url} />}
      {kind === 'csv' && <CsvPreview url={url} />}
      {kind === 'text' && <TextPreview url={url} ext={attachment.ext} />}
      {kind === 'unsupported' && <DownloadOnly url={url} name={attachment.name} />}
      <DownloadLink url={url} name={attachment.name} />   {/* 全種類で常に表示 */}
    </Overlay>
  );
}
```

**Renderer details:**

- **ImagePreview**: `<img src={url} alt={...} />` のみ。サムネ生成しない (D-12, Phase 36 D-23 同じ方針)。
- **MarkdownPreview**: `fetch(url).then(r => r.text())` → `ReactMarkdown + remarkGfm` で render。`MarkdownMessage` を直接呼ぶと AI 応答用の Monaco code block 等の重い tree が裏返るため、AttachmentModal 内で薄い react-markdown ラッパーを直接書く方が軽い。
- **CsvPreview**: `fetch().then(r => r.text())` → 行/列 split → ag-grid に渡す。既存 `ChatAgGridTable.tsx` は `MarkdownTableData` を取るので、似た shape (`{headers: string[], rows: string[][]}`) に整形する小ヘルパー。
- **TextPreview**: `fetch().then(r => r.text())` → `<Editor value={text} language={resolveLanguage(ext)} options={{readOnly: true, ...}} />` で Monaco 既存パターン (`MarkdownMessage.tsx:10`) 流用。

**Size guard:** 大きい CSV/log でブラウザがクラッシュしないよう、fetch 前に `HEAD` で size を取得 or `Content-Length` を確認し、閾値超過 (例: 10MB) なら "ファイルが大きいため DL のみ" の banner を表示する案を planner で詰める (UI-SPEC 委譲)。

**Source:** Phase 36 `AttachmentChipRow` [VERIFIED: frontend/src/components/MessageArea.tsx:52-115]、`ChatAgGridTable.tsx` [VERIFIED]、Monaco editor 既存使用 [VERIFIED: MarkdownMessage.tsx]。

### Anti-Patterns to Avoid

- **inline 描画**: D-13 で明示禁止。AI 応答テキスト内の `![]()` パスをそのままレンダリングしない。`MarkdownMessage.tsx` には Phase 38 で追加変更を入れない。
- **新規 MCP ツール (`outputs_list` / `outputs_read`) 追加**: D-06 / Deferred で却下済。tool 数膨張を避ける (ADR-0024 の趣旨)。
- **個別削除 API 追加**: D-02 / Deferred で却下済。thread 削除 hook (ADR-0048) で十分。
- **`AgentState.outputs` 独立フィールド**: Deferred 済。`AttachmentMeta` の kind フィールドで discriminator 化する。
- **手書き mcp_helper.py / tool-catalog-generated.js 編集**: CLAUDE.md / ADR-0044 で禁止。pre-commit hook が drift を検知して commit ブロックする。
- **mtime ベースの新規ファイル検出**: 上述の通り Pattern 1 で snapshot diff を採用 (NFS / 9p mount で解像度が落ちるリスク)。
- **subprocess 内中間ファイル (`.pyc` 等) を rename 対象に含める**: D-08 で「中間ファイルもこの cwd に出る点を sandbox 仕様として受容」と決定。 ただし `__pycache__/*.pyc` までは AI 利用上ノイズなので、Pattern 1 で `.pyc` / `__pycache__` を rename 対象から除外する微小フィルタを入れることを推奨 (planner 判断、≦ 5 LOC)。
- **AI prompt 内に `session-state/files/...` paths を生成させる**: Phase 36 hand-off で観察された現象。D-13 で inline 描画しない方針なので「prompt 側で `_generated/` への path 言及を抑制」する SystemMessage hint の追加を planner で検討 (任意)。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| MCP tool catalog の同期 | mcp_helper.py / tool-catalog-generated.js を手編集 | `scripts/generate_mcp_artifacts.py --target all` | pre-commit hook が drift を検知 (ADR-0044) |
| 認可付き thread folder 解決 | 新 helper を outputs.py 内に作成 | `_resolve_thread_folder` を attachments.py から import | realpath guard 重複は監査面で危険 (ADR-0048 / Phase 37 D-18) |
| Path traversal 防御 | regex で `../` 文字列拒否 | `_safe_resolve_file` を attachments.py から import | symlink / realpath 攻撃を物理的に塞ぐ (Phase 36 MEDIUM-01) |
| Markdown render | unified を直接呼ぶ | 既存 `react-markdown@10.1.0` + `remark-gfm@4.0.1` | 同一バージョンで chat 全体の整合 |
| CSV table render | 手書き `<table>` | 既存 `ag-grid-community@35.2.1` + `ChatAgGridTable.tsx` 流用 | virtual scroll / sort / filter 込みで MIT community 版完備 |
| プレーンテキスト syntax highlight | highlight.js 新規追加 | 既存 `@monaco-editor/react@4.7.0` (MarkdownMessage が使用済) | 新規 dep ゼロ・差分なし |
| LangGraph message metadata 永続化 | StateGraph に新 reducer | `BaseMessage.additional_kwargs` (JSONB checkpoint round-trip 検証済) | patterns.md L79-85 |
| timestamp prefix の付与 | AI prompt に「YYYYMMDDTHHMMSS_ を付けて」と命じる | MCP tool wrapper の post-process rename | D-10 で wrapper 責任明示 |

**Key insight:** Phase 38 は **「既存パーツの組合せ」だけで構成する** ことを CONTEXT.md `<specifics>` が明示している。Hand-roll する場面は post-process rename (≦ 20 LOC) + AttachmentModal renderer 4 種 (≦ 100 LOC) 程度。

## Runtime State Inventory

> Phase 38 は新規機能追加 (rename/refactor ではない) だが、claude_code の cwd 引数削除 (D-09) が破壊変更を含むため部分的に確認。

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | **なし** — verified by grep: `app/` / `agents/` / `scripts/` に `claude_code(` 引数渡しの直接呼び出しゼロ。MCP tool は `MultiServerMCPClient.get_tools()` 経由のみ。 | コード edit のみ (tool 関数シグネチャ変更) |
| Live service config | **なし** — Datadog / pm2 / Tailscale ACL 等は本プロジェクト未使用。docker-compose の environment は変更不要 (D-04)。 | なし |
| OS-registered state | **なし** — Windows Task Scheduler / launchd / systemd は未使用。 | なし |
| Secrets / env vars | `THREAD_FILES_DIR=/shared/thread-files` (`docker-compose.yml:50,80,111`、API + worker + mcp-server) は Phase 37 で設定済、変更不要。`CLAUDE_CODE_OUTPUT_DIR=/shared/claude-code-outputs` は D-09 で **維持**、削除しない。 | なし |
| Build artifacts / installed packages | **なし** — Python package の rename / shape 変更なし。frontend は新規 npm install ゼロ。`bun install` 再実行も不要。 | なし |

**The canonical question:** *コードを全部更新したあとに、まだ古い state が残るか？* → **残らない**。`claude_code(cwd=...)` の呼び出しは現存ゼロ、MCP tool は次回再起動で新シグネチャになる。

## Common Pitfalls

### Pitfall 1: `_generated/` を SystemMessage scan で読まずに AI に見せるのを忘れる
**What goes wrong:** AI が「生成したファイル一覧」を聞いてきたとき、attachments_list 拡張だけ実装して `attachments_helper.scan_thread_attachments` を `_generated/` 対応にし忘れると、SystemMessage prepend には kind=user_upload しか乗らず AI が混乱する。
**Why it happens:** Phase 37 の handler scan と Phase 38 の MCP tool scan が **同じファイル群を 2 経路で見る** 構造になっており、片方だけ更新するミスが起きやすい。
**How to avoid:** Pattern 3 の通り `app/jobs/handlers/attachments_helper.py:15` と `mcp_server/tools/attachments.py:123` (`attachments_list_core`) の **両方** を同じ Wave で更新する。テスト `tests/test_mcp_attachments_kind.py` (新規) と `tests/test_attachments_helper_kind.py` (新規 or 既存拡張) でそれぞれ kind を返すことを assert。
**Warning signs:** AI が `attachments_list()` 呼び出し結果に `_generated/` ファイルが含まれているのに、SystemMessage 内では同じファイルが見えていない不整合。

### Pitfall 2: `additional_kwargs` を上書きして既存フィールドを潰す
**What goes wrong:** Phase 36 の前例で `AIMessage.additional_kwargs` に何か別目的のキーが入っていた場合、`final_msg.additional_kwargs = {"attachments": ...}` で上書きすると喪失する。
**Why it happens:** Python の dict は assignment で全置換される。
**How to avoid:** **dict union** で merge する: `final_msg.additional_kwargs = (final_msg.additional_kwargs or {}) | {"attachments": turn_delta}`。Phase 36 D-22 で同パターン使用済。
**Warning signs:** test で round-trip 後に既存フィールドが消える / 型エラー。

### Pitfall 3: `_generated/` mkdir のタイミング
**What goes wrong:** MCP tool wrapper が cwd を `_generated/` にしようとした瞬間、folder 不在で `FileNotFoundError`。
**Why it happens:** Phase 36 / 37 では folder 作成は `upload_attachments` の `os.makedirs(folder, exist_ok=True)` で行われていたが、本 phase では generated 経路 = MCP tool wrapper 入口にのみ存在する。AI が初めてファイル生成を試みた turn で先に作る必要がある。
**How to avoid:** Pattern 5 の通り `_resolve_generated_folder` 直後に `os.makedirs(cwd, exist_ok=True)` を呼ぶ。冪等。
**Warning signs:** `tests/test_execute_python_output.py` (新規) で initial 状態の thread に対して 1 件目の execute_python が成功すること。

### Pitfall 4: `_generated/` を SystemMessage prepend の scan に含めるとき、サブフォルダ 1 段だけ降りるのを忘れる
**What goes wrong:** `os.listdir(folder)` だけだと `_generated/` は **ディレクトリ** として 1 エントリ現れるだけ。
**How to avoid:** Pattern 3 のサンプル通り `os.path.join(folder, "_generated")` を別途読み、両方の result を append。`os.path.isfile(...)` チェックを `_generated/` 側でも行う。再帰しない (`_generated/` 内のサブフォルダは想定外)。
**Warning signs:** AI に file 一覧が空に見える。

### Pitfall 5: 二重 rename (tool wrapper と handler が両方 rename しようとする)
**What goes wrong:** snapshot diff を tool wrapper + handler の両方に置くと、handler 側 scan が拾った時には既に `{ts}_{name}` 形式に変わっており、二重 prefix `{ts2}_{ts1}_{name}` になる。
**How to avoid:** **tool wrapper のみ** で rename する。handler 側 (turn 完了時 scan) は **既に rename 済みの状態** を読むだけ。Pattern 1 で「既に ts prefix 付きならスキップ」のガードを `_rename_new_outputs` 内に入れているのも同目的の二重防御。
**Warning signs:** 二重 prefix のファイル名が `_generated/` 内に出現。

### Pitfall 6: AsyncPostgresSaver が `additional_kwargs.attachments` の dict 内の `kind` を文字列以外で受け取って serialize 失敗
**What goes wrong:** `kind` を Python `Enum` などで持っていると JSONB シリアライズで stringify されず DB エラー。
**How to avoid:** `kind` は **文字列リテラル** (`"user_upload"` or `"generated"`) で持つ。AttachmentMeta dict 内に Enum は混在させない。
**Warning signs:** worker で `TypeError: Object of type Kind is not JSON serializable` 等。

### Pitfall 7: TextPreview で Monaco が大きいファイルでハング
**What goes wrong:** 10MB の log を全部 Monaco editor に渡すと初回 render で数秒ハング。
**How to avoid:** `AttachmentModal` の fetch 段階で size cap (例: 1MB) を設定し、超過時は "Show first 1MB" + DL ボタンに切替。詳細は UI-SPEC で planner と詰める (D-12 / Deferred の「CSV / Table 行数上限」と同枠)。
**Warning signs:** 実機操作で large output モーダルを開くとブラウザが固まる。

### Pitfall 8: claude_code の `OUTPUT_DIR` overflow output と `_generated/` の混同
**What goes wrong:** D-09 で「overflow output (`OUTPUT_DIR=/shared/claude-code-outputs`) は debug 用 global volume として現状維持」と決まっているが、claude_code 本体の output が長文 (>4000 chars) のとき `_save_overflow_output` がそこへ書き込むことを忘れ、`_generated/` 側にも同じ tail が書かれていない、と勘違いする。
**How to avoid:** `overflow output` (テキスト output の文字数超過) と `_generated/` (subprocess の workspace 出力) は **別物**。前者は debug log 用、後者がユーザー成果物。AttachmentChipRow が拾うのは後者のみ。
**Warning signs:** `_generated/` に何も出ないのに `claude-code-outputs` には大きな txt が出ている → ユーザーが探せない。これは仕様通り (D-09)、混乱しないよう ADR or 内部 docs に明記する。

### Pitfall 9: thread-files volume の worker mount が **read-only**
**What goes wrong:** Phase 37 D-04 で worker = RO に決まっている。`handler` 内で `_generated/` を mkdir しようとすると `PermissionError`。
**How to avoid:** mkdir は **MCP tool wrapper 側 (mcp-server は RW)** で行う。handler (worker) 側は **read-only scan のみ**。Pattern 5 (wrapper 内 `os.makedirs`) が正しい場所。
**Warning signs:** docker compose で worker から書き込みエラーが出る。

### Pitfall 10: API route の `_resolve_thread_folder` は 親 folder を返す → outputs route は `_generated/` を append 後に `_safe_resolve_file` 呼ぶ必要
**What goes wrong:** `_resolve_thread_folder` (`attachments.py:63`) は `/shared/thread-files/<login>/<tid>/` を返す。outputs route で直接 `_safe_resolve_file(thread_folder, name)` を呼ぶと `/.../tid/{name}` を解決してしまい `_generated/` をスキップする。
**How to avoid:** Pattern 4 の通り `gen_folder = os.path.join(thread_folder, "_generated")` を一段挟んで `_safe_resolve_file(gen_folder, name)` を呼ぶ。realpath guard は `_safe_resolve_file` 内で thread_folder ではなく **gen_folder** prefix で行われる必要がある。`_safe_resolve_file` 実装 (`attachments.py:83-95`) を読むと `thread_folder` を引数で受けるため `gen_folder` を渡せばその prefix で guard される。OK。
**Warning signs:** `tests/test_outputs_route.py` で thread_folder 直下の file (user upload) が outputs route 経由でも取れてしまう (本来は attachments route のみで取れるべき)。

## Code Examples

### Example 1: AttachmentMeta 型拡張 (TypeScript, frontend)

```ts
// frontend/src/types.ts
export interface AttachmentMeta {
  kind: 'user_upload' | 'generated';   // Phase 38: 'file' から enum 化 (既存値は 'user_upload' に正規化)
  name: string;
  storage_name: string;
  path: string;
  size: number;
  mime_type: string;
  ext: string;
  modified_at: string;
}
```

**Migration concern:** Phase 36 で書かれた既存メッセージは `kind: 'file'` を持つ。後方互換策:

```ts
// API _messages_to_response (chat.py:481) で legacy 'file' を 'user_upload' に正規化、
// または frontend 側で `kind === 'generated' ? ... : ... // (file or user_upload)` の defensive guard。
```

Phase 36 の既存 DB データ (additional_kwargs.attachments) に `kind: 'file'` が入っている件は **API 側で正規化 → 単一 enum を frontend に流す** が rollout patterns.md L221-225 「BaseMessage.content 正規化 + ReactMarkdown 防御ガード」と整合。

### Example 2: scan_thread_attachments の kind 拡張 (backend)

(Pattern 3 にコード掲載済)

### Example 3: outputs route (backend)

(Pattern 4 にコード掲載済)

### Example 4: post-process rename loop (backend)

(Pattern 1 にコード掲載済)

### Example 5: AttachmentModal renderer dispatch (frontend)

(Pattern 8 にコード掲載済)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| AI 応答テキストに `![]()` の path が出るのを期待した inline 描画 | チップ + モーダル UX 統一 (D-13) | Phase 38 | 画像も Markdown も CSV も同じ UX、Phase 36 アップロード添付と連続 |
| `execute_python.cwd="/tmp"` で揮発出力 | thread 永続フォルダの `_generated/` | Phase 38 (D-08) | ファイルが thread のライフサイクルで残る |
| `claude_code(prompt, cwd="/tmp")` | `claude_code(prompt)` (cwd 固定) | Phase 38 (D-09) | API シグネチャ破壊だが external caller ゼロで局所 |
| 入力と出力でファイル一覧 API が別物 | `attachments_list` 一本に統合 (kind discriminator) | Phase 38 (D-06) | tool 数を増やさず discriminator で識別 |

**Deprecated/outdated:**
- `session-state/files/` paths in AI response: Phase 36 hand-off で観察、本 phase で経路丸ごと再設計。AI 応答テキストに path が出ても無視 (D-13)。

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | snapshot diff (before/after `os.listdir`) が mtime 判定より堅牢 | Pattern 1 | mtime 判定でも実用上問題ないなら snapshot diff の優位性は薄い。ただし NFS / 9p mount 環境での解像度差は実在する一般則 [ASSUMED] |
| A2 | Phase 36 で `additional_kwargs` の JSONB round-trip が AIMessage 側でも問題なく動く | Pattern 2 | patterns.md L82 は Human 側のみ言及 (Phase 36 Wave 0 検証は HumanMessage)。AIMessage 側で同じ round-trip が確認されている可能性は高いが、Phase 38 Plan 01 で Wave 0 spike として **念のため AIMessage round-trip テスト** を入れることを推奨 [ASSUMED-but-low-risk]: ADR-0050 の前例から AI 側でも同様に動くと推定 |
| A3 | CSV プレビューに papaparse 不要 (split + 簡易 quote 処理で十分) | Standard Stack §Supporting | AI 生成 CSV に embedded comma / multiline quoted cells が頻出すると行列がずれる。実機観察次第で v6.1+ に papaparse 追加 [ASSUMED] |
| A4 | claude_code の cwd 引数は外部 caller ゼロ | Pattern 6 | grep で 0 ヒットを確認したが (上述)、もし testbed の手動スクリプトや人手用 spike が存在すれば壊れる [VERIFIED: grep 実行済] |
| A5 | `__pycache__/*.pyc` を rename 対象から除外する | Anti-Patterns | AI が `.pyc` を意図的に生成するケースはレア。除外で「失われた `.pyc`」と思うケースゼロ [ASSUMED] |
| A6 | Monaco editor が `read-only` + 1MB 程度のテキストで安定動作 | Pitfall 7 | MarkdownMessage 内の Monaco は既に稼働中なので code-level 既存検証あり。**Phase 38 専用検証は推奨せず**。1MB cap は安全側の見積もり [ASSUMED] |
| A7 | docker-compose の worker mount が引き続き `:ro` で Phase 38 全テストがパスする | Pitfall 9 | mkdir / rename は MCP tool wrapper 側 (mcp-server=RW) でのみ実行する設計のため worker の RO 制約に違反しない見込み [VERIFIED: docker-compose.yml + Pattern 5/9] |
| A8 | `kind: 'file'` (Phase 36 legacy) と `kind: 'user_upload'` (Phase 38) の正規化を API 側で吸収できる | Example 1 | 既存 DB のメッセージ件数は多い (200 名運用) ため、frontend defensive guard が必要かどうかは UI-SPEC で planner と詰める [ASSUMED] |
| A9 | `attachments_list` 戻り値に新フィールド `kind` を追加しても sandbox 内 AI prompt の互換性は壊れない | Pattern 7 | mcp_helper の dict は pickle/JSON で渡されるため field 追加は許容範囲。AI が `kind` key を見ても無視する [ASSUMED] |

**If this table is empty:** N/A — 上記 9 件は user 確認 or Plan 01 Wave 0 で検証を推奨。

## Open Questions

1. **`session-state/files/...` paths が AI 応答テキストに残るケースの抑制**
   - What we know: D-13 で inline 描画しない方針なので path が残っても UI 上 broken な link にはならない (チップ経路に統一)。
   - What's unclear: AI prompt 内に「`_generated/` への path 言及を抑制する」hint を入れるか、 STATE.md 上で v6.1+ に観察ベースで判断するか。
   - Recommendation: planner 判断 — SystemMessage に「あなたが生成したファイルは自動的にユーザーに表示されます。応答テキスト内にファイルパスを書く必要はありません。」程度の 1 文を追加するのが筋。≦ 5 LOC で副作用も小さい。

2. **Phase 36 既存メッセージの `kind: 'file'` の正規化方針**
   - What we know: API `_messages_to_response` が `additional_kwargs.attachments` を透過返却している。
   - What's unclear: legacy `kind: 'file'` のままにするか、API で `'user_upload'` に正規化するか。後者だと DB は変えずに API 出力だけで正規化。
   - Recommendation: API で **正規化 (`file` → `user_upload`)**。frontend に分岐を残さない方が D-06 の `kind` 単一 discriminator 原則と整合。

3. **AttachmentModal のサイズキャップ閾値**
   - What we know: D-12 で「CSV/Table 行数上限は UI 観察次第で UI-SPEC に書く」と Deferred。
   - What's unclear: 画像・MD・Monaco テキストでも同様に何らかの上限が必要か。
   - Recommendation: 暫定 1MB (text/CSV/MD)、画像は 10MB (Phase 36 IMAGE_MAX_BYTES と統一)。UI-SPEC で見直し。

4. **post-process rename と handler turn-delta scan のどちらが authoritative か**
   - What we know: Pattern 1 で wrapper が rename、Pattern 2 で handler が AIMessage に bundle。
   - What's unclear: turn 中に 2 つの tool 呼び出しが両方ファイル生成した場合、handler は両方の rename 完了後の状態を見るのが理想。
   - Recommendation: handler 側 turn-delta scan は **turn 完了 (graph.astream_events の on_chain_end) 後にのみ実行**。LangGraph の tool 呼び出しは順次なので、複数 tool 呼び出しがあっても全 rename が完了した状態で scan される。これで race condition なし。

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| docker compose | dev / 統合テスト | ✓ | (既存運用) | — |
| PostgreSQL (pgvector/pg17) | LangGraph checkpoint | ✓ | pg17 | — |
| Redis 7-alpine | arq job queue | ✓ | 7-alpine | — |
| mcp-server (FastMCP) | tool 経路 | ✓ | fastmcp >=2.14.0 | — |
| @monaco-editor/react | TextPreview | ✓ | 4.7.0 (既存) | — |
| ag-grid-community | CsvPreview | ✓ | 35.2.1 (既存) | — |
| react-markdown + remark-gfm | MarkdownPreview | ✓ | 10.1.0 / 4.0.1 (既存) | — |
| thread-files named volume | ファイル永続化 | ✓ | (Phase 37 D-04 で作成済) | — |
| `_resolve_thread_folder` / `_safe_resolve_file` helper | 認可 | ✓ | (Phase 36 / 37) | — |
| LangGraph checkpoint JSONB round-trip | metadata bundle | ✓ | (Phase 36 検証済) | — |

**Missing dependencies with no fallback:** なし。

**Missing dependencies with fallback:** なし。

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ + pytest-asyncio 0.25+ (`asyncio_mode = "auto"`) |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/test_outputs_route.py tests/test_mcp_attachments_kind.py tests/test_post_process_rename.py tests/test_langgraph_handler_outputs_bundle.py -x` |
| Full suite command | `uv run pytest tests/ -x --ignore=tests/test_api_chat.py` (Phase 36 deferred-items 通り test_api_chat.py は pre-existing milestone debt) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FOUT-01 | execute_python が生成したファイルが `_generated/` に永続化される | unit + integration | `pytest tests/test_execute_python_output.py::test_writes_to_generated_folder -x` | ❌ Wave 0 |
| FOUT-01 | post-process で `{ts}_{name}` 形式に rename される | unit | `pytest tests/test_post_process_rename.py::test_snapshot_diff_renames_only_new -x` | ❌ Wave 0 |
| FOUT-01 | GET `/api/threads/{tid}/outputs/{name}` が raw bytes を返す | integration | `pytest tests/test_outputs_route.py::test_get_output_returns_raw_bytes -x` | ❌ Wave 0 |
| FOUT-02 | claude_code が cwd 引数なしで `_generated/` に書く | unit | `pytest tests/test_claude_code_no_cwd_arg.py::test_signature_has_no_cwd -x` | ❌ Wave 0 |
| FOUT-02 | claude_code が生成したファイルも GET /outputs で取得できる | integration | `pytest tests/test_outputs_route.py::test_get_output_works_for_claude_code -x` | ❌ Wave 0 |
| FOUT-03 | (frontend) AttachmentModal が画像/MD/CSV/text をモード別 render | manual (browser) | docker compose up + manual checklist | manual-only |
| FOUT-04 | AIMessage.additional_kwargs.attachments に generated metadata が bundle される | integration | `pytest tests/test_langgraph_handler_outputs_bundle.py::test_bundles_generated_files -x` | ❌ Wave 0 |
| FOUT-04 | AsyncPostgresSaver で round-trip 後も bundle が復元される | integration | `pytest tests/test_langgraph_handler_outputs_bundle.py::test_round_trip_postgres -x` | ❌ Wave 0 |
| FOUT-04 success criteria 5 | 別 user JWT で 401/404 が返る | integration | `pytest tests/test_outputs_route.py::test_isolation_other_user_blocked -x` | ❌ Wave 0 |
| FOUT-04 success criteria 5 | path traversal `../` が拒否される | integration | `pytest tests/test_outputs_route.py::test_path_traversal_rejected -x` | ❌ Wave 0 |
| `attachments_list` kind | `_generated/` 配下も含み kind 付き | unit | `pytest tests/test_mcp_attachments_kind.py::test_returns_both_kinds -x` | ❌ Wave 0 |
| YAML drift | `scripts/generate_mcp_artifacts.py --check` が exit 0 | integration | `python3 scripts/generate_mcp_artifacts.py --check` | ✅ (既存 pre-commit hook) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_outputs_route.py tests/test_mcp_attachments_kind.py tests/test_post_process_rename.py tests/test_langgraph_handler_outputs_bundle.py -x` (30 秒以内)
- **Per wave merge:** `uv run pytest tests/ -x --ignore=tests/test_api_chat.py` (full suite、約 5-10 分)
- **Phase gate:** Full suite green + docker compose up での integration check (CONTEXT.md `<specifics>` に従い、画像生成 → チップ → モーダル → 別 thread からの再取得 → 別 user 401 確認の手動 checklist)

### Wave 0 Gaps
- [ ] `tests/test_outputs_route.py` — GET 認可 / 404 / path traversal / isolation
- [ ] `tests/test_mcp_attachments_kind.py` — attachments_list が kind を返す + _generated/ 含む
- [ ] `tests/test_post_process_rename.py` — snapshot diff の単体検証 (前後 listdir / 既存 prefix スキップ / `.pyc` 除外)
- [ ] `tests/test_langgraph_handler_outputs_bundle.py` — turn 完了で AIMessage に bundle + AsyncPostgresSaver round-trip
- [ ] `tests/test_execute_python_output.py` — cwd 切替 + fallback (/tmp) + mkdir 冪等
- [ ] `tests/test_claude_code_no_cwd_arg.py` — シグネチャ確認 + post-process rename
- [ ] フレームワーク install: なし (pytest + pytest-asyncio 既存)

**Wave 0 risk-gate check (patterns.md L94-99 準拠):** AIMessage.additional_kwargs round-trip は既知の Phase 36 patterns 流用なので **新規 Wave 0 risk なし**。ただし「AIMessage 側の `additional_kwargs` round-trip」 (A2) は厳密には未検証なので `tests/test_langgraph_handler_outputs_bundle.py::test_round_trip_postgres` を Wave 0 (Plan 01) に置くことを推奨。

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | JWT HS256 httpOnly cookie (既存 ADR-0014 / Phase 11) — outputs route も `Depends(get_jwt_payload)` で踏襲 |
| V3 Session Management | yes | JTI blocklist (既存) — 本 phase で変更なし |
| V4 Access Control | yes | `_resolve_thread_folder` + JWT payload `github_login` で user-scoped — Phase 36 / 37 helper を再利用 (D-19) |
| V5 Input Validation | yes | basename sanitization (`_normalize_basename`) + realpath prefix guard — Phase 36 既存 |
| V6 Cryptography | no | 本 phase で暗号化処理なし。SOPS / JWT 鍵は既存運用に従う |
| V8 Data Protection | yes | thread-files volume の RO/RW 分離 (api=RW, worker=RO, mcp-server=RW) — Phase 37 D-04 を踏襲 |
| V12 Files and Resources | yes | path traversal 防御 (`_safe_resolve_file` realpath prefix assert) — Phase 36 W-04 / Phase 37 MEDIUM-01 |

### Known Threat Patterns for Phase 38

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| URL `{name}` に `../etc/passwd` を埋め込んで thread folder 外へ脱出 | Tampering | `_safe_resolve_file` realpath prefix guard + `_normalize_basename` の `/` `\` `\x00` reject + URL-decode 後の realpath 検査 (Phase 36 既存テスト L60-67 で coverage 確認済) |
| 別 user の thread_id を推測して outputs route 経由でファイル取得 | Information Disclosure | `_resolve_thread_folder` が JWT payload `github_login` で folder path を組み立てるため、別 user の login がわからない限り folder 物理パスが作れない (Phase 36 helper の本質的特性、ADR-0048) |
| sandbox 内で `open("../../../etc/passwd", "w")` の subprocess 実行 | Tampering | sandbox は `cwd=_generated/` だが Python の `open` は絶対パスを許容する。AST allowlist (`config/sandbox_allowlist.yaml`、Phase 28 D-10/11) で `os` / `pathlib` を許可していれば、sandbox 内コードは自由にファイル書き込み可能。**ただしコンテナ内では root 権限がなく、`/shared/thread-files/` は other user の folder にも書ける** ← Phase 37 既知リスク。実装としては「sandbox から writable な箇所は thread-files volume のみ + AppArmor / seccomp で更に制約」が理想だが本 phase scope 外 (CONTEXT.md `<deferred>` 暗黙) |
| AI 応答内の被害的な markdown レンダリング (例: 巨大な `<img>` で DoS) | Denial of Service | チップ + モーダル経路で raw bytes は `FileResponse` (FastAPI) 経由のみ → Content-Disposition: inline + MIME 推定。inline 描画しない (D-13) ため markdown のサニタイズ自体は ReactMarkdown の既存 sanitize (HTML 自動 escape) を踏襲 |
| 大きいファイルでブラウザ DoS | Denial of Service | AttachmentModal のサイズキャップ (Pitfall 7) で 1MB 超は DL のみ |
| LangGraph checkpoint JSONB inject (AsyncPostgresSaver) | Tampering | `additional_kwargs.attachments` は型固定 dict、psycopg のパラメータ化クエリ + JSONB 型で外部 input が直接埋まらない (既存) |

### Phase 38 で **新規** 出現するセキュリティ懸念

- **`_generated/` への AI 任意書き込み**: AI が無害な python コードに見せかけてユーザーの thread folder 内に巨大ファイルを書き込む (disk DoS)。
  - Mitigation candidates: (1) disk quota — Linux quota / cgroup v2、(2) `_generated/` のサイズ上限を post-process で確認 (≦ 100MB/turn 等)、(3) v6.1+ で TTL-based GC (Deferred 済)。Phase 38 では **観察ベースで v6.1+ 判断** (CONTEXT.md `<deferred>` の「中間ファイル / 失敗 tool 呼び出し orphan」と同枠) — 本 phase で実装しない。
- **subprocess 内中間ファイル (`.pyc` 等) の累積**: Pitfall 5 で除外フィルタを推奨、ただし accumulation 自体は thread 削除 hook (ADR-0048) で清掃される。

## Sources

### Primary (HIGH confidence)
- `app/api/routes/attachments.py` (Phase 36 完成版) — `_resolve_thread_folder` / `_safe_resolve_file` / `get_attachment` 雛形 [VERIFIED: 直接読込]
- `mcp_server/tools/attachments.py` (Phase 37 完成版) — `attachments_list_core` 拡張対象 [VERIFIED: 直接読込]
- `mcp_server/tools/execute_python.py` (Phase 28 + Phase 37) — `headers` 受領経路 (L139-148) と cwd 切替対象 (L155) [VERIFIED: 直接読込]
- `mcp_server/tools/claude_code.py` (Phase 23) — シグネチャ削除対象 (L55, 74) [VERIFIED: 直接読込]
- `app/jobs/handlers/langgraph_handler.py` — turn 完了 hook (L228-241) [VERIFIED: 直接読込]
- `app/jobs/handlers/attachments_helper.py` — scan 拡張対象 [VERIFIED: 直接読込]
- `frontend/src/components/MessageArea.tsx` (Phase 36 D-21) — `AttachmentChipRow` 拡張対象 (L52-115, L340, L411) [VERIFIED: 直接読込]
- `frontend/src/components/ChatAgGridTable.tsx` — CSV テーブル基盤 [VERIFIED: 直接読込]
- `frontend/src/components/MarkdownMessage.tsx` — Monaco editor 既存使用パターン [VERIFIED: 直接読込]
- `frontend/package.json` — 既存 dep バージョン [VERIFIED: 直接読込]
- `config/mcp_tools.yaml` — attachments_list 拡張対象 (L160-182) [VERIFIED: 直接読込]
- `docker-compose.yml` — thread-files volume + worker RO 制約 [VERIFIED: 直接読込]
- `.planning/patterns.md` — `additional_kwargs` envelope (L79-85) / Wave 0 risk-gate (L94-99) / thread-files 規約 (L312-319) [VERIFIED: 直接読込]
- `docs/adr/0048-thread-files-folder-convention.md` — folder 規約根拠 [CITED via canonical_refs]
- `docs/adr/0050-copilot-sdk-multimodal-attachments.md` — additional_kwargs envelope の ADR [CITED via canonical_refs]
- `docs/adr/0044-mcp-tool-catalog-single-source-of-truth.md` — YAML SSoT と drift 検知 [CITED via canonical_refs]
- `.planning/REQUIREMENTS.md` — FOUT-01..04 [VERIFIED: 直接読込]
- `.planning/ROADMAP.md` §Phase 38 — Goal / Success Criteria [VERIFIED: 直接読込]
- `.planning/STATE.md` — recent decisions context [VERIFIED: 直接読込]
- `.planning/phases/36-text-code-image-multimodal/deferred-items.md` §Phase 38 hand-off — 出発点 [VERIFIED: 直接読込]

### Secondary (MEDIUM confidence)
- npm registry (`@monaco-editor/react@4.7.0`, `ag-grid-community@35.2.1`, `papaparse@5.5.3`) — 2026-05-12 確認 [VERIFIED: `npm view`]

### Tertiary (LOW confidence)
- snapshot diff vs mtime 判定の堅牢性比較 (一般則ベース) [ASSUMED]
- AI 生成 CSV は well-formed が期待できるという推定 [ASSUMED]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — 全 dep が既存導入済、npm view で版確認済
- Architecture: HIGH — D-01..D-19 で locked 済、研究は再利用点の特定のみ
- Pitfalls: HIGH — Phase 36 / 37 / 36-deferred-items の前例 + 既存テスト構造からの推定
- D-11 rename ロジック: MEDIUM — snapshot diff 推奨は本 RESEARCH の独自結論、planner 確認推奨
- AIMessage round-trip 永続化: MEDIUM-HIGH — patterns.md L82 は HumanMessage の前例、AIMessage 側は念のため Plan 01 Wave 0 で spike 確認

**Research date:** 2026-05-12
**Valid until:** 2026-06-12 (30 日、安定基盤の上の薄いレイヤーのため drift リスク小)

## RESEARCH COMPLETE

**Phase:** 38 - worker-dl (ファイル出力 — worker 生成 DL + プレビュー + ユーザー別保持)
**Confidence:** HIGH

### Key Findings
- **新規 npm install ゼロ** — Monaco / ag-grid / react-markdown / remark-gfm はすべて既存導入済 (Phase 35/36 で導入)。プレビュー 4 種は新規 dep 追加なしで構築可能
- **D-11 rename ロジック推奨: snapshot diff (before/after `os.listdir`)** — mtime 判定の NFS / Docker volume 解像度問題を回避、≦ 20 LOC、既存 prefix スキップガードで二重 prefix 事故防止
- **AIMessage.additional_kwargs.attachments bundle は安全** — patterns.md L79-85 で HumanMessage 側の AsyncPostgresSaver JSONB round-trip が検証済、AI 側にも同 envelope 適用、API `_messages_to_response` (chat.py:481-490) が既に透過返却している
- **claude_code の cwd 引数削除は完全に局所** — `app/` / `agents/` / `scripts/` 全 grep で外部 caller ヒット 0、影響範囲は `mcp_server/tools/claude_code.py` + 自動生成 mcp_helper.py のみ
- **outputs route は新規ファイル `outputs.py` 推奨** — `attachments.py` 追記より 50LOC で分離、`_resolve_thread_folder` / `_safe_resolve_file` は import 経由で完全再利用
- **multi-user isolation の検証は Wave 0 で 1 ファイル** — `tests/test_outputs_route.py` の `test_isolation_other_user_blocked` + `test_path_traversal_rejected` で十分 (D-19)

### File Created
`.planning/phases/38-worker-dl/38-RESEARCH.md`

### Confidence Assessment
| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | 全 dep verified via package.json + `npm view` |
| Architecture | HIGH | CONTEXT.md で D-01..D-19 locked、研究は再利用点特定のみ |
| Pitfalls | HIGH | Phase 36 / 37 / 36-deferred-items の実機観察 + ADR-0048 / patterns.md L79-99 から導出 |
| D-11 rename approach | MEDIUM | snapshot diff 推奨は本研究の独自結論 (一般則ベース) — planner 確認推奨 |
| AIMessage round-trip | MEDIUM-HIGH | HumanMessage 側で検証済の同 envelope、AI 側は Plan 01 Wave 0 で念のため確認推奨 |

### Open Questions
1. AI prompt 内に「`_generated/` への path 言及を抑制」hint を入れるか (≦ 5 LOC)
2. Phase 36 既存 `kind: 'file'` の正規化方針 (API で `'user_upload'` 化推奨)
3. AttachmentModal のサイズキャップ閾値 (暫定 1MB、UI-SPEC で確定)
4. post-process rename と handler turn-delta scan の race condition — turn 完了 (on_chain_end) 後に scan することで解消

### Ready for Planning
Research complete. Planner は次のことを進められる:
- Wave 0 (Plan 01): 既存テスト基盤上の test scaffold + AIMessage round-trip spike
- Wave 1 (Plan 02-03): MCP tool 拡張 (YAML + python + 自動生成) + execute_python/claude_code cwd 切替 + post-process rename
- Wave 2 (Plan 04): outputs route + langgraph_handler の turn-delta bundle
- Wave 3 (Plan 05): frontend AttachmentChipRow kind 拡張 + AttachmentModal + 4 renderer
- Wave 4 (Plan 06): docker compose 実機 integration check + ADR-0052 (任意) + patterns.md 追記
