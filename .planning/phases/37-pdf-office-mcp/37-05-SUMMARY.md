---
phase: 37
plan: 05
status: complete
completed: 2026-04-22
requirements: [FIN-03, FIN-04]
---

# Plan 37-05 — ADR + patterns integration

## What was built

Phase 37 の Success Criteria 5 を満たすドキュメント整備と、実環境 integration check による end-to-end 動作確認。途中で SuperChat 経路の構造ギャップ (Phase 37.1) が発覚し、その場で修正コミットを 5 本追加して完結させた。

### Task 1: ADR-0048 + patterns + adr-categories
- `docs/adr/0048-thread-files-folder-convention.md` (157 行) を新規作成
  - パス階層 `/shared/thread-files/<github_login>/<thread_id>/` (D-01/D-04)
  - ファイル命名 `YYYYMMDDTHHMMSS_<original>.<ext>` (D-04)
  - mount マトリクス (api: RW / mcp-server: RW / worker: RO) (D-09)
  - ライフサイクル (delete_thread と同期、TTL なし) (D-03)
  - **D-08**: テキスト 0 文字 PDF は `error` ではなく `content: ""` を返す方針 (S-02 対応)
  - Phase 36 (アップロード UI) / Phase 38 (出力ストレージ) との接続契約
- `.planning/adr-categories.yaml` の `Data・Persistence` カテゴリに 0048 を追加
- `.planning/patterns.md` の `Data・Persistence` セクションに "thread-files 共有フォルダ規約" エントリを 1 件追記 (D-15: 手動更新ルールに従う)
- commit: `e8be962`

### Task 2: docs/adr/INDEX.md 再生成
- `python3 scripts/generate_adr_index.py` で INDEX.md を再生成
- Total: 44 → 45 件
- commit: `92da65b`

### Task 3: Integration check (human-verify checkpoint)
- ユーザー (6in) が docker compose 実環境で 5 シナリオを手動実施
- 結果は `docs/phase-37-integration-check.md` に記録
- **PASS:** Scenario A (scan + SystemMessage prepend) / B (attachments_extract via MCP) を新スレッドで end-to-end 動作確認
- C / D は unit test で同等保証
- E (0 文字 PDF) は OCR 未対応 PDF のサンプル不足のため D-08 ロジック実装と ADR-0048 記載で代替 (Phase 37.2 backlog)

### Task 4: VALIDATION.md 最終化
- frontmatter `status: validated` / `nyquist_compliant: true` / `validated: 2026-04-22`
- Per-Task Map に 37-05-XX 4 行追加 (合計 19 行、4 Wave 全網羅)
- Sign-Off チェックボックス 6 項目すべて [x]
- `Approval: approved`

## Phase 37.1 in-place fixes (integration check で発覚した silent failures)

| # | 問題 | 修正 | コミット |
|---|------|------|---------|
| 1 | `general-assistant/AGENT.md` に attachments_list/extract が宣言されておらず agent toolbelt から欠落 | tools リストに 2 ツール追加 + system prompt に "推測せず必ず attachments_extract を呼ぶ" 旨を明記 | `5070b5c` |
| 2 | `OrchestratorHandler` (SuperChat 経路) に Plan 04 改修が入っておらず、scan/prepend/per-job MCP client がすべて欠落 → MCP ツールに RPCContext が伝わらず空配列 | `attachments_helper.py` を新規作成して scan/build を抽出。`OrchestratorHandler._handle_inner` で per-job `MultiServerMCPClient(headers={x-thread-id, x-github-login})` を構築 → `get_tools()` を `SubAgentRegistry` に渡す。`scan_thread_attachments` で input prepend、`AgentState.attachments` 設定 | `13ec129`, `4842c04` |
| 3 | `mcp_server/tools/attachments.py::_classify_error` が markitdown を `TimeoutError` 経路でも eager import → ルート env で `ModuleNotFoundError` | markitdown import を TimeoutError 判定後に遅延 | `ada73db` |
| 4 | `mcp_server/uv.lock` に Plan 02 で追加した markitdown 依存がコミットされていなかった | docker rebuild 時の uv sync で生成された lock を取り込み | `59cb5ff` |
| 5 | Copilot SDK `send_timeout=120s` が tool schema bloat + 履歴蓄積で不足 (実測 124s で TimeoutError) | 既定値を 300s に延長、`COPILOT_SEND_TIMEOUT` env var で上書き可能化 | `6ee36d4` |

## Key files

### created
- `docs/adr/0048-thread-files-folder-convention.md` (157 行)
- `docs/phase-37-integration-check.md` (66 行)
- `app/jobs/handlers/attachments_helper.py` (Phase 37.1 抽出モジュール)
- `.planning/phases/37-pdf-office-mcp/37-05-SUMMARY.md` (本ファイル)

### modified
- `.planning/adr-categories.yaml` (0048 追加)
- `.planning/patterns.md` (Data・Persistence エントリ 1 件追加)
- `docs/adr/INDEX.md` (自動再生成)
- `.planning/phases/37-pdf-office-mcp/37-VALIDATION.md` (最終化)
- `app/jobs/handlers/orchestrator_handler.py` (Phase 37.1 per-job MCP + scan/prepend)
- `app/jobs/handlers/langgraph_handler.py` (Phase 37.1 共有 helper 経由に変更)
- `app/providers/copilot.py` (Phase 37.1 send_timeout 拡張)
- `agents/general-assistant/AGENT.md` (Phase 37.1 tools 追加)
- `mcp_server/tools/attachments.py` (Phase 37.1 markitdown lazy import)
- `mcp_server/uv.lock` (Phase 37.1 markitdown 依存追加)
- `tests/test_langgraph_handler_attachments.py` (Phase 37.1 helper モジュール参照に更新)

## Self-Check: PASSED

- [x] Task 1-4 全て実施・コミット済
- [x] ADR-0048 が D-08 (S-02) を含む形で書かれている
- [x] patterns.md / adr-categories.yaml に整合する追記
- [x] INDEX.md 自動再生成 (Total 45)
- [x] integration-check.md に 5 シナリオの結果記録 (うち A/B は実環境 PASS、C/D は unit test 経由、E は ADR 文書 + ロジックで代替)
- [x] VALIDATION.md `nyquist_compliant: true` / `status: validated` / Sign-Off 全 [x]
- [x] Phase 37.1 silent failure 5 件を即時修正コミット
- [x] No modifications to STATE.md or ROADMAP.md (orchestrator が後で更新)
