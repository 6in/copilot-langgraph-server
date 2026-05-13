---
phase: 38
plan: 3
plan_id: 38-03-sandbox-cwd-and-rename
subsystem: mcp-tools-sandbox
tags: [sandbox, execute-python, claude-code, post-process-rename, snapshot-diff, cwd-switch]
requirements: [FOUT-01, FOUT-02]
dependency_graph:
  requires:
    - "Phase 38 Plan 01 (38-01-types-and-roundtrip-gate) — test scaffold (test_post_process_rename.py / test_execute_python_output.py / test_claude_code_no_cwd_arg.py)"
    - "Phase 37 D-17 RPCContext 伝搬経路 (mcp_server/tools/execute_python.py:139-148 x-thread-id / x-github-login headers)"
    - "Phase 37 D-04 thread-files volume mount (mcp-server=RW)"
  provides:
    - "_resolve_generated_folder(headers) — realpath guard 込みの _generated/ path 解決 helper (claude_code / 後続 plan も import 再利用)"
    - "_rename_new_outputs(folder, before) — snapshot diff で {ts}_{name} に rename + .pyc 除外 + 既存 prefix スキップ"
    - "_is_already_prefixed(name) — YYYYMMDDTHHMMSS_ prefix 判定 helper"
    - "execute_python / claude_code の tool wrapper が `generated_files: list[str]` を結果 dict に追加するインタフェース"
    - "claude_code 新シグネチャ: (prompt: str, headers: dict | None = None) — cwd 引数削除"
  affects:
    - "Plan 04 (handler turn-delta bundle) — generated_files が wrapper 結果に乗るため AIMessage.additional_kwargs.attachments bundle のソースが定まる"
    - "Plan 02 (outputs route + attachments_list kind 拡張) — _generated/ 配下のファイル命名規約 (timestamp prefix) が確定したためそのままハンドリング可能"
tech_stack:
  added: []
  patterns:
    - "snapshot diff (before/after listdir) で新規ファイル検出 — mtime / inotify を避ける (NFS / 9p 解像度問題回避)"
    - "tool wrapper 責任で timestamp prefix を付与 — AI プロンプト依存ゼロで Phase 37 D-02 命名規約と統一"
    - "realpath prefix guard 込みの path traversal 防御 — headers 経由でも _shared/thread-files 配下を物理的に守る"
    - "DRY: claude_code が execute_python.py の helper を import で再利用 — single source of truth"
    - "破壊変更だが外部 caller ゼロ前提の signature 変更 (claude_code cwd 削除)"
key_files:
  created: []
  modified:
    - mcp_server/tools/execute_python.py
    - mcp_server/tools/claude_code.py
    - tests/test_post_process_rename.py
    - tests/test_execute_python_output.py
    - tests/test_claude_code_no_cwd_arg.py
decisions:
  - "D-08 実装確定: execute_python の cwd を `/shared/thread-files/<login>/<tid>/_generated/` に切替、headers 不足や path traversal は `/tmp` に fallback"
  - "D-09 実装確定: claude_code から cwd 引数を完全削除、headers 経由で _generated/ 固定実行。overflow output (OUTPUT_DIR) は debug 用 global volume として現状維持"
  - "D-10 実装確定: timestamp prefix の付与責任は MCP tool wrapper が持つ — AI プロンプトには依存しない"
  - "D-11 実装確定: rename 検出は snapshot diff (before/after listdir) を採用 — mtime / inotify ではなく堅牢性を取った"
  - "DRY: claude_code は execute_python.py の _resolve_generated_folder / _rename_new_outputs を import 再利用 (single source of truth)"
metrics:
  duration_minutes: 5
  completed_date: 2026-05-12
  tasks_completed: 2
  files_modified: 5
  files_created: 0
  commits: 4
---

# Phase 38 Plan 03: sandbox cwd 切替 + post-process rename Summary

sandbox (execute_python + claude_code) の subprocess cwd を `/shared/thread-files/<login>/<tid>/_generated/` に切替え、tool wrapper が snapshot diff で生成ファイルを `{ts}_{name}` 規約に揃える設計を実装した。`claude_code` からは破壊変更で `cwd` 引数を削除（外部 caller ゼロを再確認）。helper は execute_python.py を single source of truth として claude_code.py から import 再利用する DRY 構造に統一。

## Tasks Completed

| # | Task | Test commit | Impl commit | Files |
|---|------|-------------|-------------|-------|
| 1 | execute_python に `_resolve_generated_folder` / `_rename_new_outputs` / `_is_already_prefixed` を追加し cwd を切替 | `4c4d5d0` | `ce39a78` | mcp_server/tools/execute_python.py, tests/test_post_process_rename.py, tests/test_execute_python_output.py |
| 2 | claude_code から cwd 引数を削除、headers 引数を追加、execute_python helper を import 再利用 | `689ab33` | `c43fb51` | mcp_server/tools/claude_code.py, tests/test_claude_code_no_cwd_arg.py |

## Key Decisions / Implementation

### D-08 — execute_python の cwd 切替 (realpath guard 込み)

```python
THREAD_FILES_DIR = os.environ.get("THREAD_FILES_DIR", "/shared/thread-files")

def _resolve_generated_folder(headers: dict | None) -> str:
    h = headers or {}
    tid = h.get("x-thread-id") or ""
    login = h.get("x-github-login") or ""
    if not tid or not login:
        return "/tmp"
    folder = os.path.join(THREAD_FILES_DIR, login, tid, "_generated")
    real = os.path.realpath(folder)
    base = os.path.realpath(THREAD_FILES_DIR)
    if not real.startswith(base + os.sep):
        return "/tmp"
    return real
```

- subprocess 呼び出し直前で `os.makedirs(cwd, exist_ok=True)` を実行し冪等化 (Pitfall 3)
- realpath prefix guard で `x-thread-id` に `../` を埋め込まれても THREAD_FILES_DIR 配下から逸脱しないことを担保 (T-38-03-01 mitigate)
- 全ての fallback 経路は `/tmp` に縮退 — 既存 sandbox 動作と互換性維持 (test / spike / 直接呼び出しの後方互換)

### D-10 / D-11 — snapshot diff 方式の post-process rename

```python
def _rename_new_outputs(folder: str, before: set[str]) -> list[str]:
    if not os.path.isdir(folder):
        return []
    ts = _utc_ts()
    after = set(os.listdir(folder))
    new_files = sorted(after - before)
    renamed: list[str] = []
    for name in new_files:
        if os.path.splitext(name)[1].lower() in _PYC_EXCLUDES:
            continue
        src = os.path.join(folder, name)
        if os.path.islink(src) or not os.path.isfile(src):
            continue
        if _is_already_prefixed(name):
            renamed.append(name)
            continue
        dst_name = f"{ts}_{name}"
        os.rename(src, os.path.join(folder, dst_name))
        renamed.append(dst_name)
    return renamed
```

- **mtime ではなく snapshot diff を採用** した理由 (RESEARCH §Pattern 1): Docker volume を NFS / 9p で mount すると `mtime` 解像度が 1s に落ちて取りこぼしが出る既知問題を回避
- `.pyc` 除外 + symlink 除外 + 既に prefix 付きならスキップ の 3 段ガードで二重 prefix / 中間ファイルの AI 露出を防止 (Pitfall 5, T-38-03-05)
- tool wrapper 側で `folder != "/tmp"` ガードを置き、fallback 経路で `/tmp` 全体の diff になる事故を回避 (Pitfall: `set(os.listdir("/tmp"))` が爆発しないよう)

### D-09 — claude_code 破壊変更 (cwd 引数削除)

```python
# Before:
async def claude_code(prompt: str, cwd: str = "/tmp") -> dict:
# After:
async def claude_code(prompt: str, headers: dict | None = None) -> dict:
```

- 外部 caller ゼロを最終確認: `grep -rn "claude_code(" app/ agents/ scripts/` = 0 hit (RESEARCH §Pattern 6 と一致)
- MCP tool は `MultiServerMCPClient.get_tools()` 経由でしか呼ばれないため、影響範囲は局所的
- `_save_overflow_output` / `OUTPUT_DIR=/shared/claude-code-outputs` は **触らない** — debug 用 global volume として現状維持 (D-09 / Pitfall 8)
- `config/mcp_tools.yaml` の `claude_code` block は `sandbox_exposed: false` で python_wrapper を持たない (args 定義なし) → YAML 変更不要、drift 検査も無走 (checker I8 通過)

### DRY — execute_python.py を single source of truth に

```python
# mcp_server/tools/claude_code.py
from mcp_server.tools.execute_python import _resolve_generated_folder
# ...
from mcp_server.tools.execute_python import _rename_new_outputs, _resolve_generated_folder
```

helper 重複定義を避け、後続 plan が新たな tool を追加する際も `mcp_server/tools/execute_python.py` の helper を import 再利用するだけで `_generated/` 経路に乗せられる。

## Verification

| Check | Result |
|-------|--------|
| `uv run pytest tests/test_post_process_rename.py -x -v` | ✅ 3 passed (snapshot_diff / skips_already_prefixed / excludes_pyc) |
| `uv run pytest tests/test_execute_python_output.py -x -v` | ✅ 2 passed (writes_to_generated_folder / falls_back_to_tmp_without_headers) |
| `uv run pytest tests/test_claude_code_no_cwd_arg.py -x -v` | ✅ 1 passed (signature_has_no_cwd) |
| 全 6 ケース合算 | ✅ 6 passed in 0.05s |
| Source assertion: `grep -c "def _resolve_generated_folder" mcp_server/tools/execute_python.py` | ✅ 1 |
| Source assertion: `grep -c "def _rename_new_outputs" mcp_server/tools/execute_python.py` | ✅ 1 |
| Source assertion: `grep -c "def _is_already_prefixed" mcp_server/tools/execute_python.py` | ✅ 1 |
| Source assertion: hardcoded `cwd="/tmp"` (fallback return 除外) | ✅ 0 |
| Source assertion: `grep -c "_PYC_EXCLUDES" mcp_server/tools/execute_python.py` | ✅ 2 (定義 + 使用) |
| Source assertion: `grep -E "before = set\(os\.listdir" mcp_server/tools/execute_python.py` | ✅ ヒット |
| Source assertion: `grep -E 'if folder != "/tmp"' mcp_server/tools/execute_python.py` | ✅ ヒット |
| Source assertion: `python3 -c "...assert 'cwd' not in inspect.signature(claude_code).parameters"` | ✅ exit 0 |
| Source assertion: `grep "^async def claude_code\(prompt: str, headers"` | ✅ ヒット |
| Source assertion: `grep -c "cwd: str = " mcp_server/tools/claude_code.py` | ✅ 0 |
| Source assertion: `grep -E "from mcp_server\.tools\.execute_python import" mcp_server/tools/claude_code.py` | ✅ ヒット (2 箇所 — 関数本体 + wrapper) |
| Source assertion: `grep -c "claude_code_with_headers" mcp_server/tools/claude_code.py` | ✅ 2 |
| Source assertion: overflow output 維持 — `grep -c "_save_overflow_output\|OUTPUT_DIR"` | ✅ 7 (D-09 維持) |
| External caller — `grep -rn "claude_code(" app/ agents/ scripts/` | ✅ 0 hit |
| YAML drift — claude_code block に cwd args が無いことを確認 | ✅ args フィールド自体が無い (sandbox_exposed: false) |
| Module import smoke test (`mcp_server.tools.execute_python` / `mcp_server.tools.claude_code`) | ✅ 新シグネチャ確認 / THREAD_FILES_DIR / _PYC_EXCLUDES 読み出し OK |

## Deviations from Plan

### Auto-fixed Issues

**None.** プラン記載通りに実装。RULE 2 (`os.path.islink` での symlink 除外) を **Plan 03 の指示そのものに含まれていたガード** として `_rename_new_outputs` に組み込んだ (RESEARCH §Pitfall 1 「symlink 除外は Phase 37 LOW-04 と同じ」)。

### Authentication Gates

なし — 本 plan は MCP tool 内部実装とテストのみで認可境界に触れない。

## Threat Mitigation Coverage

| Threat ID | Disposition | 実装による mitigation |
|-----------|-------------|----------------------|
| T-38-03-01 (Tampering: x-thread-id `../` で folder 外実行) | mitigate | `_resolve_generated_folder` 内 `realpath` + prefix guard で逸脱検出 → `/tmp` fallback。`test_falls_back_to_tmp_without_headers` の 4 番目のケースで path traversal を assert |
| T-38-03-04 (Tampering: snapshot diff race) | accept | sandbox subprocess は分離プロセスで外部 actor が同 folder に同時書き込みする想定がない (CONTEXT D-19) |
| T-38-03-05 (Information Disclosure: `.pyc` 漏れ) | mitigate | `_PYC_EXCLUDES` で `.pyc` を rename 対象から除外、`test_excludes_pyc_files` で assert |

T-38-03-02 (spoofing) と T-38-03-03 (DoS) は accept で本 plan では何もしない (CONTEXT 既決定通り)。

## Files Modified

- `mcp_server/tools/execute_python.py` — `THREAD_FILES_DIR` / `_PYC_EXCLUDES` 定数 + `_utc_ts` / `_resolve_generated_folder` / `_is_already_prefixed` / `_rename_new_outputs` の 4 helper を新設、subprocess cwd を `_resolve_generated_folder` の戻り値に置換、register_tools wrapper を post-process rename 付きに拡張
- `mcp_server/tools/claude_code.py` — シグネチャから `cwd` を削除し `headers` を追加、execute_python helper を import 再利用 (DRY)、register_tools wrapper を `claude_code_with_headers` (CurrentHeaders DI + post-process rename) に置換、overflow output 処理は維持
- `tests/test_post_process_rename.py` — Plan 01 で scaffold 済の 3 ケースから skip マーカーを外し、assertion 本体を実装
- `tests/test_execute_python_output.py` — Plan 01 で scaffold 済の 2 ケース (asyncio.create_subprocess_exec を AsyncMock で wrap して cwd 引数を assert / `_resolve_generated_folder` を直接呼んで fallback を assert) を実装
- `tests/test_claude_code_no_cwd_arg.py` — Plan 01 で scaffold 済の 1 ケースを実装 (sys.path 工作を除去し `from mcp_server.tools.claude_code import claude_code` で直接 import)

## Self-Check: PASSED

- ✅ `mcp_server/tools/execute_python.py` exists (modified) with `_resolve_generated_folder` / `_rename_new_outputs` / `_is_already_prefixed`
- ✅ `mcp_server/tools/claude_code.py` exists (modified) with new signature `(prompt, headers=None)` and `cwd` removed
- ✅ `tests/test_post_process_rename.py` 3 ケース all PASSED
- ✅ `tests/test_execute_python_output.py` 2 ケース all PASSED
- ✅ `tests/test_claude_code_no_cwd_arg.py` 1 ケース PASSED
- ✅ Commit `4c4d5d0` (RED Task 1 tests) exists in git log
- ✅ Commit `ce39a78` (GREEN Task 1 impl) exists in git log
- ✅ Commit `689ab33` (RED Task 2 test) exists in git log
- ✅ Commit `c43fb51` (GREEN Task 2 impl) exists in git log
- ✅ External caller count = 0 (grep -rn "claude_code(" app/ agents/ scripts/)
- ✅ Module import smoke test passes (new signatures readable)
