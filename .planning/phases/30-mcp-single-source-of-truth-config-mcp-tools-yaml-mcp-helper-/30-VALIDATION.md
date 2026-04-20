---
phase: 30
slug: mcp-single-source-of-truth-config-mcp-tools-yaml-mcp-helper-
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-20
validated: 2026-04-20
---

# Phase 30 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> 本ファイルは Phase 30 実行当時 (2026-04-18) には存在せず、v5.0 milestone audit cleanup
> (phase 31.1) で `.planning/phases/30-.../VERIFICATION.md` の 7/7 PASS を根拠として
> 遡及的に `status: validated` で作成したもの。

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >= 8.0 + pytest-asyncio >= 0.25 (pyproject.toml `[tool.pytest.ini_options]` asyncio_mode=auto) |
| **Config file** | `pyproject.toml` (root) |
| **Quick run command** | `uv run pytest tests/test_tool_registry.py tests/test_generate_mcp_artifacts.py tests/test_mcp_helper_generated.py tests/test_tool_catalog_js.py tests/test_install_hooks.py -x` |
| **Full suite command** | `uv run pytest tests/ -x` |
| **Determinism check** | `python3 scripts/generate_mcp_artifacts.py --check`（pre-commit hook と同一コマンド、exit 0 を要求） |
| **Estimated runtime** | Phase 30 固有 51 件 ~1s / 全体 ~30-60s |

---

## Sampling Rate

- **After every task commit:** `uv run pytest tests/test_tool_registry.py tests/test_generate_mcp_artifacts.py tests/test_mcp_helper_generated.py tests/test_tool_catalog_js.py tests/test_install_hooks.py -x`
- **After every plan wave:** `uv run pytest tests/ -x` + `python3 scripts/generate_mcp_artifacts.py --check`
- **Before `/gsd-verify-work`:** Full suite green + drift check exit 0 + sandbox-style import smoke (`cd mcp_server/tools && python3 -c 'from mcp_helper import search, query_db, get_datetime, ping'`)
- **Max feedback latency:** 5 秒（focused）/ 60 秒（full）

---

## Per-Task Verification Map

> Phase 30 の 6 plan を VERIFICATION.md の 7 Truths に対応させて記録。Phase 30 実行当時は per-task `<automated>` を事前宣言する Nyquist 運用規律が確立していなかったため、実際の verify は Plan 完了後の VERIFICATION.md で事後に行われた。本 map は事後的にトレーサビリティを補完する目的で作成。

| Plan | Wave | Truth (VERIFICATION.md) | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|------|------|--------------------------|-----------------|-----------|-------------------|-------------|--------|
| 30-01 | 1 | Truth 1 | config/mcp_tools.yaml が 6 ツールを拡張スキーマ (python_wrapper / sandbox_exposed / privileged) で宣言 | yaml load | `python3 -c 'import yaml; print(len(yaml.safe_load(open("config/mcp_tools.yaml"))["tools"]))'` == 6 | ✅ | ✅ green |
| 30-01 | 1 | Truth 1 (regression) | ToolRegistry が拡張フィールドを無視しつつ既存契約を維持 | unit | `uv run pytest tests/test_tool_registry.py -x` | ✅ | ✅ green |
| 30-02 | 1 | Truth 2 | ジェネレータ 3 ターゲットが byte-identical で決定論的 | unit | `uv run pytest tests/test_generate_mcp_artifacts.py -x` | ✅ | ✅ green |
| 30-02 | 1 | Truth 2 | drift 検知モード (`--check`) が exit 0 / 非 0 を正しく返す | integration | `python3 scripts/generate_mcp_artifacts.py --check` → exit 0 | ✅ | ✅ green |
| 30-03 | 2 | Truth 3 | 自動生成 mcp_helper.py が手書き utils を import して 4 wrapper を再現 | unit | `uv run pytest tests/test_mcp_helper_generated.py -x` | ✅ | ✅ green |
| 30-03 | 2 | Truth 3 (smoke) | sandbox 互換 import が機能 | smoke | `cd mcp_server/tools && python3 -c 'from mcp_helper import search, query_db, get_datetime, ping'` | ✅ | ✅ green |
| 30-04 | 2 | Truth 4 | tool-catalog-generated.js が AVAILABLE_TOOLS を 6 entry export、privileged: true が 2 件 | unit | `uv run pytest tests/test_tool_catalog_js.py -x` | ✅ | ✅ green |
| 30-04 | 2 | Truth 4 | iframe-rpc.js が re-export、旧 sync-tool-list-to-js.py が削除済み | grep | `grep -q "export { AVAILABLE_TOOLS } from './tool-catalog-generated.js'" static/js/iframe-rpc.js && ! test -f scripts/sync-tool-list-to-js.py` | ✅ | ✅ green |
| 30-05 | 3 | Truth 6 | pre-commit hook が ADR INDEX + MCP drift 両方のブロックを保持 | unit | `uv run pytest tests/test_install_hooks.py -x` | ✅ | ✅ green |
| 30-05 | 3 | Truth 6 | hook 再インストール後 `.git/hooks/pre-commit` に両ブロックが共存 | integration | `bash scripts/install-hooks.sh && grep -cE 'generate_(adr_index|mcp_artifacts)' .git/hooks/pre-commit` >= 2 | ✅ | ✅ green |
| 30-06 | 2 | Truth 5 | docs/mcp-tools.md が自動生成 (DO NOT EDIT ヘッダ付 / 6 ツール詳細) | grep | `head -2 docs/mcp-tools.md \| grep -q 'DO NOT EDIT' && grep -c '^## ' docs/mcp-tools.md` >= 6 | ✅ | ✅ green |
| 30-06 | 2 | Truth 5 | /add-mcp-tool スラッシュコマンド + docs/mcp-tool-add-manual.md + CLAUDE.md セクション + patterns.md 更新 | grep | `test -f .claude/commands/add-mcp-tool.md && test -f docs/mcp-tool-add-manual.md && grep -q '## MCP Tool Catalog (Phase 30)' CLAUDE.md` | ✅ | ✅ green |
| all | — | Truth 7 | Phase 30 新規 51 件 + 隣接回帰 12 passed, 1 skipped | full | `uv run pytest tests/test_tool_registry.py tests/test_generate_mcp_artifacts.py tests/test_mcp_helper_generated.py tests/test_tool_catalog_js.py tests/test_install_hooks.py tests/test_generate_adr_index.py tests/test_mcp_server.py tests/test_subagent_registry_tools.py` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky — 全行 VERIFICATION.md (2026-04-18) の evidence を根拠に green 固定*

---

## Wave 0 Requirements

- [x] `tests/test_tool_registry.py` — YAML 拡張スキーマを ToolRegistry が無視しつつ既存契約を維持することを保証（30-01）
- [x] `tests/test_generate_mcp_artifacts.py` — ジェネレータ 3 ターゲットの決定論性 + `--check` モード（30-02）
- [x] `tests/test_mcp_helper_generated.py` — 自動生成 mcp_helper.py が 4 wrapper を正しく提供することの回帰テスト（30-03）
- [x] `tests/test_tool_catalog_js.py` — tool-catalog-generated.js のスキーマと privileged フラグ検証（30-04）
- [x] `tests/test_install_hooks.py` — install-hooks.sh の ADR + MCP 両ブロック同居 + 冪等性（30-05）
- [x] `pyproject.toml` への依存追加不要（pytest / pytest-asyncio / PyYAML は既存で充足）

*本 Wave 0 要件はすべて Phase 30 実行中に実ファイルとして追加済み。VERIFICATION.md Truth 7 で「Phase 30 新規 51 件が全 PASS」として実証済み。*

---

## Manual-Only Verifications

| Behavior | Requirement (Truth) | Why Manual | Test Instructions |
|----------|---------------------|------------|-------------------|
| 新規 MCP ツール追加手順 `/add-mcp-tool` の end-to-end 実行 | Truth 5 (運用ドキュメント完備) | スラッシュコマンドは人間インタラクティブ前提、追加後の手動レビューが必要 | 将来新規ツール追加時に `/add-mcp-tool <name>` を実行し、生成される YAML + 3 artifacts + pre-commit 通過を手動確認 |
| Canvas iframe 経由で AVAILABLE_TOOLS が実ランタイムに届くこと | Truth 4 (JS カタログ移行) | iframe postMessage + ブラウザ実行が必要 | `docker compose up` → Canvas アプリ起動 → devtools console で `AVAILABLE_TOOLS` の length が 6 であることを確認 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies（Per-Task Verification Map に全 plan の automated コマンド記載）
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references（Phase 30 で作成された 5 test file がすべて実在）
- [x] No watch-mode flags
- [x] Feedback latency < 60s（focused 51 件 ~1s、full suite ~30-60s）
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-04-20 (Phase 30 VERIFICATION.md 7/7 PASS を根拠に遡及作成、v5.0 milestone audit cleanup phase 31.1)
