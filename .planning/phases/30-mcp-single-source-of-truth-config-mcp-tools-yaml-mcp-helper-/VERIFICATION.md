---
phase: 30-mcp-single-source-of-truth-config-mcp-tools-yaml-mcp-helper-
verified: 2026-04-18T10:42:00Z
status: passed
score: 7/7 goals verified
overrides_applied: 0
---

# Phase 30: MCP ツールカタログ single-source-of-truth 化 Verification Report

**Phase Goal:** `config/mcp_tools.yaml` を MCP ツールカタログの single source of truth にし、`mcp_helper.py` / `tool-catalog-generated.js` / `docs/mcp-tools.md` をジェネレータから決定論的に自動生成する。新規ツール追加手順 (`/add-mcp-tool` + マニュアル) を標準化し、pre-commit hook で drift 検知を強制する。ToolRegistry との後方互換は維持する。

**Verified:** 2026-04-18T10:42:00Z
**Status:** PASS
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `config/mcp_tools.yaml` が拡張スキーマで 6 ツールを宣言している | ✓ VERIFIED | 6 ツール (ping / web_search / db_query / claude_code / execute_python / get_current_datetime)、privileged=[claude_code, execute_python]、python_wrapper 付与=[ping, web_search, db_query, get_current_datetime]、sandbox_exposed=false=[claude_code, execute_python] を Python 検証で確認 |
| 2 | ジェネレータが決定論的で drift なし | ✓ VERIFIED | `python3 scripts/generate_mcp_artifacts.py --check` exit=0。`--target helper/js/docs` を 2 回ずつ走らせて byte-identical (diff 空)。かつ on-disk 3 ファイルとも byte-identical |
| 3 | ランタイム後方互換（4 関数 import 可 + primitives は utils で共用） | ✓ VERIFIED | sandbox-style `from mcp_helper import search, query_db, get_datetime, ping` 成功。mcp_helper.py L10 に `from mcp_helper_utils import _call_tool, _clean_content` 固定、`_INTERNAL_URL` / `_TIMEOUT` / `_call_tool` / `_clean_content` は mcp_helper_utils.py L20-46 に集約 |
| 4 | JS カタログ移行（生成版を iframe-rpc.js が import、旧同期スクリプト削除） | ✓ VERIFIED | `static/js/tool-catalog-generated.js` (2751 bytes, DO NOT EDIT ヘッダ, AVAILABLE_TOOLS 6 エントリ, privileged: true × 2) 存在。`iframe-rpc.js` L22 に `export { AVAILABLE_TOOLS } from './tool-catalog-generated.js'`。`scripts/sync-tool-list-to-js.py` は削除 (ls 失敗確認) |
| 5 | Docs & 運用ドキュメント完備 | ✓ VERIFIED | `docs/mcp-tools.md` (120 行、DO NOT EDIT、6 ツール詳細)、`docs/mcp-tool-add-manual.md` (151 行、手書き)、`.claude/commands/add-mcp-tool.md` (125 行、7 ステップ)、`CLAUDE.md` L302 `## MCP Tool Catalog (Phase 30)` セクション追加、`.planning/patterns.md` MCP・Tools カテゴリに `iframe-rpc.js ツールカタログは独立 ES module 参照` 更新 + `MCP ツール single-source-of-truth 化` 新規エントリ追加 |
| 6 | pre-commit drift 検知 hook が ADR INDEX + MCP 両方を持つ | ✓ VERIFIED | `bash scripts/install-hooks.sh` 再インストール成功。`.git/hooks/pre-commit` に `generate_adr_index` / `generate_mcp_artifacts` の双方が present (grep count=3)。hook 内で MCP_PATHS_REGEX が YAML / helper / js / docs 4 パスを判定し `--check` を呼んで exit 1 |
| 7 | テストスイート全体 pass + 既存回帰なし | ✓ VERIFIED | Phase 30 新規/更新テスト 51 件 (tool_registry / generate_mcp_artifacts / mcp_helper_generated / tool_catalog_js / install_hooks) が全 PASS。隣接回帰テスト (test_generate_adr_index + test_subagent_registry_tools) 12 passed, 1 skipped (既存スキップ枠) |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `config/mcp_tools.yaml` | 拡張スキーマで 6 ツール + 4 python_wrapper | ✓ VERIFIED | `yaml.safe_load` 成功、names/privileged/wrapped/sandbox_exposed_false 分布がすべて期待通り |
| `scripts/generate_mcp_artifacts.py` | 3 ターゲット + `--check` で決定論的 | ✓ VERIFIED | `--check` exit 0、3 ターゲット byte-identical、on-disk ファイル 3 種とも一致 |
| `mcp_server/tools/mcp_helper.py` | 自動生成 (DO NOT EDIT、4 関数、utils import) | ✓ VERIFIED | L1 `# DO NOT EDIT`、L10 `from mcp_helper_utils import _call_tool, _clean_content`、`^def ` が 4 件 (ping / search / query_db / get_datetime)、claude_code / execute_python 関数は生成されていない |
| `mcp_server/tools/mcp_helper_utils.py` | 手書き基盤 (primitives 4 種) | ✓ VERIFIED | 新規追加、`_INTERNAL_URL` L20, `_TIMEOUT` L21, `_call_tool` L24, `_clean_content` L46。挙動は逐語コピー |
| `static/js/tool-catalog-generated.js` | 自動生成 (DO NOT EDIT、AVAILABLE_TOOLS export、6 エントリ) | ✓ VERIFIED | L1 `// DO NOT EDIT`、tool entry 6 件、privileged: true × 2 |
| `static/js/iframe-rpc.js` | 新生成版を re-export | ✓ VERIFIED | L22 `export { AVAILABLE_TOOLS } from './tool-catalog-generated.js'`、RPC 本体は無変更 |
| `scripts/sync-tool-list-to-js.py` | 削除済み | ✓ VERIFIED | ls 失敗 (No such file) |
| `docs/mcp-tools.md` | 自動生成 (DO NOT EDIT、6 ツール) | ✓ VERIFIED | 120 行、概要表 + 6 詳細セクション、`--check` drift なし |
| `docs/mcp-tool-add-manual.md` | 手書きマニュアル | ✓ VERIFIED | 151 行、YAML スキーマ / 手書き境界 / privileged 基準 / pre-commit 挙動 記述 |
| `.claude/commands/add-mcp-tool.md` | スラッシュコマンド | ✓ VERIFIED | 125 行、7 ステップ構成 |
| `scripts/install-hooks.sh` | ADR + MCP 両方の drift 検知を持つ | ✓ VERIFIED | ADR セクション (L28-32) と MCP セクション (L37-57) を並列配置 |
| `CLAUDE.md` | `## MCP Tool Catalog (Phase 30)` セクション追加 | ✓ VERIFIED | L302〜。手書き/自動生成境界、`/add-mcp-tool` 誘導、install-hooks 指示あり |
| `.planning/patterns.md` | MCP・Tools カテゴリに Phase 30 エントリ追加 | ✓ VERIFIED | L94 `iframe-rpc.js ツールカタログは独立 ES module 参照` 更新 + L99 `MCP ツール single-source-of-truth 化` 新規 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `mcp_helper.py` | `mcp_helper_utils.py` | `from mcp_helper_utils import _call_tool, _clean_content` | ✓ WIRED | L10 import + 5 箇所で `_call_tool(...)` 呼出、web_search 内で `_clean_content(...)` 呼出 |
| `iframe-rpc.js` | `tool-catalog-generated.js` | `export { AVAILABLE_TOOLS } from './tool-catalog-generated.js'` | ✓ WIRED | L22 re-export。既存 consumer は import path 変更不要 |
| pre-commit hook | `generate_mcp_artifacts.py --check` | `.git/hooks/pre-commit` の MCP_PATHS_REGEX ブロック | ✓ WIRED | 4 パス (YAML / helper / js / docs) がステージされたとき `cd "$REPO_ROOT" && python3 scripts/generate_mcp_artifacts.py --check` を実行、非 0 で exit 1 |
| `app/orchestrator/tool_registry.py` | `config/mcp_tools.yaml` | `yaml.safe_load` → `entry["name"]` / `entry.get("privileged")` | ✓ WIRED | 拡張フィールド (python_wrapper / sandbox_exposed) を無視しつつ既存契約維持、回帰テスト `test_tool_registry_real_yaml_contract` / `test_tool_registry_extended_schema_ignored` で実証 |
| `config/sandbox_allowlist.yaml` | `mcp_helper_utils` | `allowed_modules:` に追加 | ✓ WIRED | L47 `mcp_helper_utils` が allowed_modules に明示 |

### Data-Flow Trace (Level 4)

Phase 30 はコード生成・ドキュメント・hook 整備が主で、「ランタイムで動的にデータをレンダリングする UI コンポーネント」は追加していない。
ただし、生成物 → 実ファイルのデータフローは決定論性チェックで実証済み:

| Artifact | Data Source | Produces Real Data | Status |
|----------|-------------|--------------------|--------|
| `mcp_helper.py` | `config/mcp_tools.yaml` の python_wrapper 4 ツール | はい (4 関数を含む 94 行、2 回生成で byte-identical) | ✓ FLOWING |
| `tool-catalog-generated.js` | `config/mcp_tools.yaml` の 6 ツール | はい (AVAILABLE_TOOLS に 6 entry、2 回生成で byte-identical) | ✓ FLOWING |
| `docs/mcp-tools.md` | `config/mcp_tools.yaml` 全 6 ツール | はい (120 行、6 詳細セクション、2 回生成で byte-identical) | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| YAML パース | `python3 -c 'import yaml; yaml.safe_load(open("config/mcp_tools.yaml"))'` | 例外なし、6 ツール取得 | ✓ PASS |
| drift 検知 (ok 系) | `python3 scripts/generate_mcp_artifacts.py --check` | exit=0 | ✓ PASS |
| ジェネレータ決定論性 | `diff <(python3 scripts/generate_mcp_artifacts.py --target helper) <(python3 scripts/generate_mcp_artifacts.py --target helper)` (3 ターゲット全て) | 空 diff | ✓ PASS |
| sandbox-style helper import | `cd mcp_server/tools && python3 -c 'from mcp_helper import search, query_db, get_datetime, ping'` | 4 関数 import 成功 | ✓ PASS |
| hook 再インストール冪等 | `bash scripts/install-hooks.sh` | "Installed pre-commit hook at: ..." 出力、.git/hooks/pre-commit に adr/mcp 3 箇所言及 | ✓ PASS |
| Phase 30 テスト 51 件 | `python3 -m pytest tests/test_tool_registry.py tests/test_generate_mcp_artifacts.py tests/test_mcp_helper_generated.py tests/test_tool_catalog_js.py tests/test_install_hooks.py -v` | 51 passed in 0.56s | ✓ PASS |
| 隣接テスト回帰 | `python3 -m pytest tests/test_generate_adr_index.py tests/test_mcp_server.py tests/test_subagent_registry_tools.py` | 12 passed, 1 skipped | ✓ PASS |

### Requirements Coverage

PLAN 各ファイルの `requirements:` は全て `[TBD]` / `[]` となっており、Phase 30 は正式な REQUIREMENTS.md 項目に紐づいていない（ROADMAP.md でも `**Requirements**: TBD`）。そのため requirement ID ベースのカバレッジ検証は対象外。Goal-level 7 項目を代替指標とし全て PASS。

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `.planning/ROADMAP.md` | 281-283 | Phase 30 Plans 04/05/06 が `[ ]` のまま | ℹ️ Info | 実コミット・SUMMARY・artifact は全て完了しているが ROADMAP のチェックボックス更新漏れ。Phase 完了判定・マイルストーン進捗に軽微な影響。マージ時 or `/gsd-next` 運用で修正推奨 |
| `.planning/patterns.md` | 97, 101 | `Phase 30 (ADR 番号未定 — /create-adr で追補予定)` | ℹ️ Info | Plan 06 SUMMARY の明示的方針通り。Phase 30 マージ前に `/create-adr` で番号確定する運用で問題なし |
| `.planning/todos/pending/2026-04-18-mcp-tool-registration-consumer-propagation.md` | 11, 23 | 旧 `sync-tool-list-to-js.py` を参照 | ℹ️ Info | pending todos にまだ旧手順記述。Phase 30 で自動反映体制ができたため、この todo 自体を completed に移すか手順を更新する必要がある |
| `docs/adr/0040-*.md` | 40 | 旧 `sync-tool-list-to-js.py で自動更新可能` の記述が残存 | ℹ️ Info | 過去の ADR 本文なので書き換え不可（ADR は不変）。patterns.md と CLAUDE.md で新方針に置き換え済みなので実運用には影響なし |

すべて ℹ️ Info レベル。🛑 Blocker / ⚠️ Warning は検出されなかった。

### Human Verification Required

None — 本 Phase はインフラ・コード生成・pre-commit hook・ドキュメントの整備であり、UI 可視的挙動・リアルタイム動作・外部サービス連携は新たに追加していない。`/add-mcp-tool` スラッシュコマンドと実 MCP ツールの end-to-end 追加検証は本 Phase の goal スコープ外 (Phase 30 完了後の運用で自然に検証される)。

### Gaps Summary

ゴール 7 項目すべて VERIFIED。ブロッカーなし。軽微な bookkeeping drift (ROADMAP チェックボックス、pending todos) のみ。これらはマージ時 or Phase クローズ運用で解消可能で、本 Phase の deliverable の成立を阻害しない。

---

*Verified: 2026-04-18T10:42:00Z*
*Verifier: Claude (gsd-verifier, Opus 4.7 1M context)*
