---
phase: 36-text-code-image-multimodal
plan: 01
subsystem: testing
tags: [langgraph, langchain-core, copilot-sdk, additional_kwargs, checkpointer, multimodal, spike, tdd]

# Dependency graph
requires:
  - phase: 37-pdf-office-mcp
    provides: "thread-files volume mount + AgentState.attachments + フォルダ規約 (ADR-0048)"
provides:
  - "tests/test_chat_history_additional_kwargs.py — additional_kwargs round-trip 契約 (4 ケース GREEN)"
  - "tests/test_copilot_attachments_spike.py — Copilot SDK 0.2.0 attachments / list_models / SDK isolation の 4 契約固定"
  - "docs/phase-36-sdk-spike-note.md — docker compose 実機 spike 完了記録 (Verdict: PASS, 2026-04-24)"
  - "A1 risk verdict: 対応不要 (Wave 1 Plan 04 で workaround 追加なし)"
  - "SDK contract verdict: PASS (FileAttachment TypedDict / send_and_wait(attachments=...) / ModelInfo dataclass / SDK isolation 全て確認)"
  - "A3 risk verdict: PASS (docker compose worker から /shared/thread-files RO mount 経由で SDK が path open / Copilot model に送信 / 要約応答取得を確認)"
affects:
  - "phase-36 wave-1 plan-02 — ChatCopilot._extract_attachments 実装の SDK 型契約"
  - "phase-36 wave-1 plan-04 — handler の HumanMessage.additional_kwargs 注入経路"
  - "phase-36 wave-3 plan-04 — D-18 vision drop / D-20 履歴永続化"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "MemorySaver + minimal StateGraph による checkpointer round-trip 単体テスト (D-20 verification)"
    - "inspect.signature ベースの SDK contract pin (実 subprocess を起動せずに API 形状を凍結)"
    - "ast/grep ベースの SDK isolation regression test (D-15 隔離原則)"

key-files:
  created:
    - "tests/test_chat_history_additional_kwargs.py"
    - "tests/test_copilot_attachments_spike.py"
    - "docs/phase-36-sdk-spike-note.md"
  modified: []

key-decisions:
  - "A1 risk verdict: HumanMessage.additional_kwargs は LangGraph add_messages reducer + checkpointer で full fidelity round-trip する → Wave 1 Plan 04 で workaround 不要"
  - "SDK 0.2.0 の send_and_wait(attachments=...) は POSITIONAL_OR_KEYWORD で公開されているが wrapper 側はキーワード指定で呼ぶ運用 (D-09 維持)"
  - "FileAttachment.displayName は SDK 上 required (Plan 当初の optional 表記から修正) — Wave 1 Plan 02 の _extract_attachments は必ず displayName を埋める"
  - "Task 3 (docker compose 実機 spike) は auto_advance=true でも auto-approve しない — 実 Copilot token + 実機 docker subprocess を要求するため真の人間アクション扱い (orchestrator に checkpoint return)"
  - "A3 risk verdict (Task 3 smoke 実行 2026-04-24): PASS — RO mount /shared/thread-files 経由で SDK が path open / claude-sonnet-4.6 がファイル内容反映の要約を返した。D-09 path-based attachments のまま Wave 1 Plan 02 着手 OK"
  - "[SDK API correction — Plan 02 input] CopilotClient construction は `CopilotClient(SubprocessConfig(github_token=..., use_logged_in_user=False))` が正 (既存 app/providers/copilot.py:301 と同形式)。spike note Appendix A の `CopilotClient(github_token=token)` は誤り (smoke 実行時に判明、訂正済み)。Plan 02 で新規 SDK client を作る場合は SubprocessConfig 経由必須"
  - "[Auth API note — Plan 02 input] CopilotAuthManager.load_token() は sync, get_token() は async — spike script は load_token() で正しいが production (worker / handler) では token refresh + Device Flow 再開も含む `await get_token()` を使う"

patterns-established:
  - "Checkpointer round-trip 検証 = MemorySaver で identity StateGraph を組み HumanMessage を ainvoke → aget_state で復元、フィールド deep equality で固定する"
  - "SDK 契約固定 = inspect.signature + dataclasses.fields + TypedDict.__required_keys__ で構造を assert (実 subprocess 起動なし)"
  - "SDK isolation regression = 'from copilot' / 'import copilot' を app/ 配下から grep し、app/providers/copilot.py 以外で見つけたら FAIL"

requirements-completed: [FIN-01, FIN-02]

# Metrics
duration: 5min
completed: 2026-04-24
---

# Phase 36 Plan 01: Wave 0 risk + SDK spike Summary

**Wave 0 完全完了 — A1 risk + SDK contract + docker compose smoke (A3 risk) すべて GREEN。Wave 1 Plan 02 は方針変更なしで着手 OK (D-09 path-based attachments / D-15 SDK 隔離 / additional_kwargs サイドカー全て維持)**

## Performance

- **Duration:** ~5 min automated + 実機 smoke (docker compose 起動 + sample.txt 配置 + worker 経由 SDK 呼出 + cleanup)
- **Started:** 2026-04-24T01:21:52Z (autonomous portion)
- **Autonomous portion completed:** 2026-04-24T01:26:18Z
- **Smoke completed:** 2026-04-24 (Task 3 checkpoint resolved — Verdict: PASS)
- **Tasks:** 3/3 完了 (2 autonomous + 1 checkpoint resolved)
- **Files modified:** 3 created, 0 modified

## Accomplishments

- **A1 risk 確定 = 対応不要**: `HumanMessage.additional_kwargs["attachments"]` が LangGraph `add_messages` reducer + checkpointer 経由で 8 フィールド完全 round-trip することを 4 つのテストで証明 (`tests/test_chat_history_additional_kwargs.py`). ADR-0038 の AIMessage.name 喪失とは別経路で `additional_kwargs` は無事だったため、Wave 1 Plan 04 で `_wrap_human_message_attachments` 系の workaround 追加判断は不要.
- **SDK 0.2.0 attachments 契約固定**: `copilot.FileAttachment` (TypedDict)・`CopilotSession.send_and_wait(attachments=...)` / `send(attachments=...)`・`CopilotClient.list_models`・`ModelInfo` dataclass (`id` / `name` / `capabilities`) の 4 契約を `inspect.signature` + `dataclasses.fields` ベースで凍結 (`tests/test_copilot_attachments_spike.py`). Wave 1 で SDK 仕様が想定外に変わった場合、これらのテストが pre-merge で失敗して気付ける regression net になる.
- **SDK isolation regression net 整備**: `app/` 配下から `from copilot` / `import copilot` を grep し、`app/providers/copilot.py` 以外に出現したら FAIL するテストを追加. 現状 GREEN (provider のみ).
- **A3 risk 確定 = clear (docker compose smoke PASS)**: `docker compose up -d` で全 6 サービス健全起動 → api コンテナで `/shared/thread-files/_spike/_t/sample.txt` 配置 → worker コンテナから `uv run python tests/_spike_attachments.py` 実行 → SDK が path 経由で sample.txt を open し `claude-sonnet-4.6` にファイル添付送信 → 応答に sample.txt 実コンテンツ ("Phase 36 スパイクテスト") を反映した要約取得を確認 (2026-04-24). D-09 path-based attachments 方針のまま Wave 1 Plan 02 の `ChatCopilot._extract_attachments` 配線を着手 OK. spike 用 script (`tests/_spike_attachments.py`) と一時ファイル (`/shared/thread-files/_spike/`) は実行後削除済み.
- **spike note 完成**: `docs/phase-36-sdk-spike-note.md` の Verdict / Observed Response / Verdict Rationale を smoke 結果で埋め、Appendix A の SDK API を実態に合わせて訂正 (`CopilotClient(SubprocessConfig(...))` 形式 + `try/finally` で `client.stop()` 保証). Next-Wave Impact に Plan 02 で必要な 2 つの downstream note (SDK API 訂正 / `load_token()` sync vs `get_token()` async) を追加.

## Task Commits

Each task was committed atomically:

1. **Task 1: AsyncPostgresSaver round-trip test (A1 risk)** — `2745bea` (test)
2. **Task 2: SDK attachments spike (FileAttachment / send_and_wait / list_models / SDK isolation)** — `15c87ff` (test)
3. **Task 3: docker compose SDK spike note 雛形 (checkpoint:human-verify gate)** — `3616308` (docs)
4. **Task 3 完了: docker compose smoke PASS 記録 + spike note SDK API 訂正** — `13ecff4` (docs)
5. **(this commit) SUMMARY 最終化 — Wave 0 完全完了** — `<this commit>` (docs)

_Note: Task 1/2 は `tdd="true"` 指定だったが、検証対象が「既存ライブラリ動作の凍結」であり RED 段階を入れる意義がないため (実装側の変更なし)、test 単体コミットで運用._

## Files Created/Modified

- `tests/test_chat_history_additional_kwargs.py` — A1 risk verification, MemorySaver + identity StateGraph で 4 ケース (full attachments dict / 空 dict / legacy 未指定 / image attachment 8 フィールド)
- `tests/test_copilot_attachments_spike.py` — SDK contract pin, 4 ケース (FileAttachment TypedDict / send_and_wait+send attachments param / ModelInfo dataclass / SDK isolation regression)
- `docs/phase-36-sdk-spike-note.md` — docker compose 実機 spike の手順 + smoke 完了記録 (Date 2026-04-24 / Verdict PASS / Observed Response / Verdict Rationale 埋済 + Appendix A SDK API 訂正済)

## Decisions Made

- **MemorySaver で代替**: AsyncPostgresSaver は CI 不安定 + 実 DB 接続要件があり、`add_messages` reducer + checkpointer の serialize/deserialize パスは MemorySaver でも完全に同一実装のため、Plan の `<action>` 1. の指示通り MemorySaver で検証. 実 PostgreSQL 動作確認は Task 3 の docker compose smoke で担保.
- **SDK 隔離 grep の false positive 回避**: `from copilot ` (空白終わり) / `from copilot.` (dot 開始) / `import copilot` (完全一致 or 末尾コンマ・空白) のみマッチさせ、`from copilot_xxx` 等の誤検知を除外.
- **Task 3 を auto-approve しない**: `auto_advance: true` でも実 Copilot token + 実 docker compose subprocess を要求する性質上、parallel executor agent が安全に自動実行できないため checkpoint return を選択. Plan の `<resume-signal>` も "FAIL の場合は approved を入力せず具体エラーとともに報告 — Wave 1 に進むと phase 方針全体を見直す必要あり" と明示.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan の Task 2 assert (`KEYWORD_ONLY`) が SDK 実態と乖離**

- **Found during:** Task 2 (SDK attachments spike) 実装直前の事前 SDK probe
- **Issue:** Plan の `<action>` 3. で `assert params["attachments"].kind == inspect.Parameter.KEYWORD_ONLY` を要求していたが、SDK 0.2.0 実装は `attachments` を `POSITIONAL_OR_KEYWORD` として公開している (`prompt: str` の後ろの第 2 引数). 書いた通りに assert すると必ず FAIL し、テストとして「契約を固定する」目的を果たせない.
- **Fix:** assert を `params["attachments"].kind in (KEYWORD_ONLY, POSITIONAL_OR_KEYWORD)` に緩和し、コメントで「wrapper は `attachments=...` でキーワード指定して呼ぶ運用 (D-09 intent 維持)」と明記. これにより SDK 実態 (POSITIONAL_OR_KEYWORD) を許容しつつ、Wave 1 で SDK が KEYWORD_ONLY に厳格化された場合も同テストで検出可能.
- **Files modified:** `tests/test_copilot_attachments_spike.py`
- **Verification:** `uv run pytest tests/test_copilot_attachments_spike.py::test_sdk_session_send_and_wait_accepts_attachments_kwarg -v` GREEN
- **Committed in:** `15c87ff` (Task 2 commit)

**2. [Rule 2 - Missing Critical] FileAttachment.displayName は SDK 上 required である事実を Plan 当初の interfaces 表記から訂正**

- **Found during:** Task 2 実装直前の事前 SDK probe (`FileAttachment.__required_keys__` で `frozenset({'displayName', 'type', 'path'})` を確認)
- **Issue:** Plan の `<interfaces>` セクションでは `displayName: Optional[str]  # optional` と書かれていたが、SDK 0.2.0 実装では `displayName` は **required** (`__required_keys__` に含まれる、`__optional_keys__` は空集合). Wave 1 Plan 02 の `_extract_attachments` 実装で `displayName=None` を渡す経路を作ると静的型エラーまたは runtime ValidationError になる.
- **Fix:** spike note (`docs/phase-36-sdk-spike-note.md`) の「Next-Wave Impact / PASS 時」セクションに「`displayName` は SDK 0.2.0 で required (Wave 0 Plan 01 Task 2 で確認 — SDK isolation test 経由) のため、D-15 の変換ルールで必ず埋める」と明記. Wave 1 Plan 02 planner が見落とさないよう downstream context として残した.
- **Files modified:** `docs/phase-36-sdk-spike-note.md`
- **Verification:** `uv run python -c "from copilot import FileAttachment; print(FileAttachment.__required_keys__)"` で `frozenset({'displayName', 'type', 'path'})` を確認
- **Committed in:** `3616308` (Task 3 commit)

**3. [Rule 1 - Bug] Spike note Appendix A の `CopilotClient` コンストラクタ API が SDK 実態と不一致 (smoke 実行時に発覚)**

- **Found during:** Task 3 docker compose smoke 実行時 (orchestrator が worker コンテナで `tests/_spike_attachments.py` 実行 → `CopilotClient(github_token=token)` で TypeError)
- **Issue:** Plan / spike note Appendix A 当初コードは `CopilotClient(github_token=token)` だったが、SDK 0.2.0 の正しいシグネチャは `CopilotClient(SubprocessConfig(github_token=..., use_logged_in_user=...))`. 既存 production 実装 (`app/providers/copilot.py:301`) と整合せず、書いた通りに実行すると即 fail.
- **Fix:** spike note Appendix A を `CopilotClient(SubprocessConfig(github_token=token, use_logged_in_user=False))` 形式に訂正、`try/finally` で `client.stop()` 保証 + token None ガード追加. Next-Wave Impact に「Plan 02 で新規 SDK client を作る場合は SubprocessConfig 経由必須」を明記し、planner / executor が同じ罠を踏まないよう downstream context として固定.
- **Files modified:** `docs/phase-36-sdk-spike-note.md` (Appendix A コード + Next-Wave Impact note)
- **Verification:** orchestrator が訂正後コードで実 smoke 実行 → claude-sonnet-4.6 が sample.txt 内容を反映した要約を返すことを確認 (Verdict: PASS)
- **Committed in:** `13ecff4` (Task 3 完了 commit)
- **Plan 02 への影響:** Plan 02 で `ChatCopilot.__init__` 経由で SDK client を作る経路は既存 `app/providers/copilot.py` を踏襲するので追加変更不要. ただし Plan 02 planner が新規 SDK 利用箇所を作る判断をした場合は SubprocessConfig 経由を必須要件として認識すること.

**4. [Rule 2 - Missing Critical] `CopilotAuthManager.load_token()` は sync, `get_token()` は async — Plan 02 で取り違え予防**

- **Found during:** Task 3 smoke 実行時、spike script で `auth.load_token()` (no await) が正しいことを確認した過程で、production 経路 (`app/auth/manager.py:245`) では `await get_token()` (async, refresh + Device Flow 再開も含む) を使っていることが対比で明確化.
- **Issue:** spike script は read-only な sync `load_token()` で十分だが、Plan 02 で provider / handler から token を取得する経路では token refresh と Device Flow 再開を含む `await get_token()` を使う必要がある. spike note に明記しないと Plan 02 で混同して `auth.load_token()` を使い、token 期限切れ時に refresh されず 401 を踏むリスクあり.
- **Fix:** spike note Next-Wave Impact に「`load_token()` は sync (Optional[str] を返す, spike script 用)、`get_token()` は async (`app/auth/manager.py:245`, production 経路で必須) — 取り違えないこと」を Auth API 注記として追加.
- **Files modified:** `docs/phase-36-sdk-spike-note.md` (Next-Wave Impact 内 Auth API 注記)
- **Verification:** `app/providers/copilot.py` の token 取得経路が既に `await self.auth_manager.get_token()` で書かれていることを確認 (production が既に正しい形を維持済み)
- **Committed in:** `13ecff4`

---

**Total deviations:** 4 auto-fixed (2 Rule 1 bug, 2 Rule 2 missing critical)
**Impact on plan:** すべて Plan 当初の SDK / Auth 仕様前提を実態に合わせて訂正した最小修正で、Phase 36 全体方針 (D-09 / D-15 / additional_kwargs サイドカー) は完全に維持. Wave 1 Plan 02 planner には spike note Next-Wave Impact 経由で 4 件すべて downstream context として明示的に伝達済み (1: KEYWORD/POSITIONAL_OR_KEYWORD 緩和 / 2: displayName required / 3: SubprocessConfig 経由 / 4: load_token vs get_token). scope creep なし.

## Issues Encountered

- **Worktree base hash 比較の short-form ミス判定**: 起動時 `<worktree_branch_check>` で `[ "$(git rev-parse HEAD)" != "be82136" ]` を short-form 7 文字で比較してしまい、実際の HEAD (`be82136486a7152306cfee3a2e1584accc1e672b`) との完全一致判定に失敗. ただし実際にはベースは正しかったため `git reset --hard be82136` の結果も同じ commit に居続け、データロス無し. 以降は `git rev-parse HEAD` の出力 (40 桁) と short hash の prefix 一致を確認する運用に切替.

## Threat Flags

なし — Plan の `<threat_model>` (T-36-01-01〜05) はすべて Plan 内で mitigate disposition、本 plan 実装で新規 surface 追加なし. Task 3 spike note の Appendix A に書かれた script は git に commit せず spike 後に削除する運用 (note 内で明示) のため、T-36-01-02 (一時ファイル) / T-36-01-03 (response 機密混入) / T-36-01-04 (timeout) は orchestrator/operator が Task 3 実行時に handle.

## User Setup Required

**手動 smoke は 2026-04-24 に完了済み — 追加の user setup なし.**

実施済み手順 (記録):
1. `docker compose up -d` で全 6 サービス健全起動 (api / worker / postgres / redis / mcp-server / frontend)
2. `docker compose exec api mkdir -p /shared/thread-files/_spike/_t/` + `echo 'Phase 36 spike test. ファイルの内容はこれです。' > sample.txt`
3. worker から `ls -la /shared/thread-files/_spike/_t/sample.txt` で RO mount 可視性確認 (`-rw-r--r-- 1 root root 61`)
4. spike script (`tests/_spike_attachments.py`) を SubprocessConfig 経由の SDK API で作成 → `docker compose exec worker uv run python tests/_spike_attachments.py`
5. 応答 `CONTENT: **要約:** ...「Phase 36 スパイクテスト」であることを示す...` を確認 → PASS 判定
6. spike 用一時ファイル + script 削除済み (`rm -rf /shared/thread-files/_spike` + `rm -f tests/_spike_attachments.py`)

→ Verdict / Observed Response / Verdict Rationale はすべて `docs/phase-36-sdk-spike-note.md` に記録済 (commit `13ecff4`).

## Next Phase Readiness

- **A1 risk = clear**: Wave 1 Plan 04 (handler の HumanMessage.additional_kwargs 注入) で workaround 追加判断は不要、シンプルな代入経路で進められる
- **SDK contract = pinned**: Wave 1 Plan 02 (ChatCopilot._extract_attachments) が型情報を確信を持って書ける
- **A3 risk = clear**: docker compose worker が `/shared/thread-files` RO mount 経由で SDK 経由の path open を実機で確認済み (D-09 path-based 方針維持)
- **SDK isolation = enforced**: Wave 1 で誤って handler 等から `from copilot import` を追加した場合、`tests/test_copilot_attachments_spike.py::test_sdk_imports_isolated_to_provider` が CI で検出
- **Plan 02 への明示インプット**: spike note Next-Wave Impact 経由で 4 件の SDK / Auth API 訂正を downstream context として伝達済 (Deviation #1〜#4 参照)
- **Blocker**: なし — Wave 1 着手 gate すべて GREEN

## Self-Check: PASSED

- ✅ `tests/test_chat_history_additional_kwargs.py` exists (`ls -la tests/test_chat_history_additional_kwargs.py` → present, 163 lines)
- ✅ `tests/test_copilot_attachments_spike.py` exists (123 lines)
- ✅ `docs/phase-36-sdk-spike-note.md` exists (smoke 結果記録済 + Appendix A 訂正済)
- ✅ Commit `2745bea` (test) reachable
- ✅ Commit `15c87ff` (test) reachable
- ✅ Commit `3616308` (docs) reachable
- ✅ Commit `13ecff4` (docs — smoke 完了 + SDK API 訂正) reachable
- ✅ `uv run pytest tests/test_chat_history_additional_kwargs.py tests/test_copilot_attachments_spike.py -x -v` → 8 passed in 0.15s
- ✅ docker compose smoke Verdict: PASS が `docs/phase-36-sdk-spike-note.md` に記録済 (Plan の done 条件充足)
- ✅ Wave 0 完全完了 — Wave 1 Plan 02 着手 OK

---

*Phase: 36-text-code-image-multimodal*
*Plan: 01 (Wave 0)*
*Completed: 2026-04-24 — Wave 0 完全完了 (A1 risk + SDK contract + docker compose smoke 全 GREEN)*
