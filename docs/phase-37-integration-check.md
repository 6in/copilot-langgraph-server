# Phase 37 Integration Check

**Date:** 2026-04-22
**Executor:** 6in (with Claude Code)
**Branch:** gsd/phase-37-pdf-office-mcp
**App tested:** SuperChat (`app_id=superchat`, OrchestratorHandler)
**Agent:** general-assistant (gpt-4.1)
**Thread:** `d039d335-2508-4d85-accd-877f4479f5be` (fresh)
**Sample file:** `/shared/thread-files/6in/d039d335-.../20260422T093000_sample.pdf` (632 bytes、テキスト "Phase 37 integration check / Hello from sample.pdf")

## 観察結果

### Scenario A: 添付 scan + SystemMessage prepend

- [x] AI が添付ファイルを認識して応答した — `20260422T093000_sample.pdf` を識別
- [x] `attachments_list` が実 thread のファイル 1 件を返した
- 経過時間: 11.2s
- worker トレース ID: `1a9f4756-73a9-46cf-8906-00e48589e347`
- 結果抜粋:
  ```
  result_prefix: [{"name":"20260422T093000_sample.pdf","size":632,"modified_at":1776818759.0,"ext":".pdf","mime_type":"application/pdf"}]
  ```

### Scenario B: attachments_extract via MCP

- [x] AI が `attachments_extract` ツールを呼び、PDF 内容を要約して返した
- [x] `result_prefix` に `content: "Phase 37 integration check\nHello from sample.pdf"` が観察できた (D-08 / FIN-03 SC-1)
- [x] mcp-server log に POST /mcp の 200 OK が複数記録された
- 経過時間: 12.2s (extract 単独は 507ms)
- worker トレース ID: `f427869c-ba50-464a-96d2-a3671fc290ce`

### Scenario C: Path traversal 拒否

- [x] unit test で検証 (`tests/test_attachments_extract.py::test_path_traversal`)
- `attachments_extract_core("t","u","../../etc/passwd")` → `error.code == "corrupt"` (W-04)
- realpath prefix guard 実装: `mcp_server/tools/attachments.py:_safe_resolve`

### Scenario D: delete_thread で folder 削除

- [x] unit test で検証 (`tests/test_api_chat.py::test_delete_thread_removes_folder`)
- [x] traversal 拒否も検証 (`tests/test_api_chat.py::test_delete_thread_rejects_path_traversal`)
- 実装: `app/api/routes/chat.py::delete_thread` の `shutil.rmtree(safe_thread_folder, ignore_errors=True)`

### Scenario E: 0 文字 PDF (D-08 検証)

- 実環境テストは未実施 (OCR 未対応 PDF をユーザーが手元に持っていなかった)
- D-08 ロジックは `attachments_extract_core` 末尾で実装済 — テキスト 0 文字でも `error: None`、`content: ""` を返す
- ADR-0048 の "## Decision > 抽出失敗時の挙動 (D-08)" セクションに方針明記済
- 後続 phase で OCR 対応 PDF を用意して実機確認するのが望ましい (Phase 37.2 backlog 候補)

## Silent failure 検知

整合性検証中に複数発覚し、すべて Phase 37.1 として修正コミット済み:

| # | 問題 | 修正 | コミット |
|---|------|------|---------|
| 1 | `general-assistant/AGENT.md` に attachments_list/extract が宣言されておらず agent toolbelt に出てこなかった | tools リストに 2 ツール追加 + system prompt にツール利用指示追加 | `5070b5c` |
| 2 | `OrchestratorHandler` (SuperChat 経路) に Plan 04 改修が入っておらず、scan/prepend/per-job MCP client がすべて欠落 | `attachments_helper.py` に scan/build を抽出し、`OrchestratorHandler._handle_inner` で per-job `MultiServerMCPClient` を作成 (`x-thread-id` / `x-github-login` headers) → `get_tools()` を `SubAgentRegistry` に渡す。`scan_thread_attachments` で input prepend、`AgentState.attachments` 設定 | `13ec129`, `4842c04` |
| 3 | `mcp_server/tools/attachments.py::_classify_error` が markitdown を `TimeoutError` 経路でも eager import → ルート env で `ModuleNotFoundError` | markitdown import を TimeoutError 判定後に遅延 | `ada73db` |
| 4 | `mcp_server/uv.lock` に Plan 02 で追加した markitdown 依存がコミットされていなかった | docker rebuild 時の uv sync で生成された lock を取り込み | `59cb5ff` |
| 5 | Copilot SDK `send_timeout=120s` が tool schema bloat + 履歴蓄積で不足 (実測 124s で TimeoutError) | 既定値を 300s に延長、`COPILOT_SEND_TIMEOUT` env var で上書き可能化 | `6ee36d4` |

新スレッドで送信 → 11-12s で応答という結果から、上記 5 修正で end-to-end が通る状態となった。
古いスレッドは累積した failure メッセージで履歴肥大化し timeout 域に入りやすい (運用上の留意点)。

## 起動時間

- mcp-server healthcheck first-ready: 約 60s 以内 (start_period=60s で間に合った)
- magika/onnxruntime 初回 import は spike では 18s 程度を観測 (Plan 01 spike-mcp-headers.md 参照)
- 1 回目の `attachments_extract` は 507ms (PDF が小さいため magika/markitdown のロードコストは観測時点ではキャッシュ済み)
