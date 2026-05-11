# 0051. Multi-app 機能展開フェーズの工程パターン (Phase 36 retrospective)

**Date:** 2026-05-11
**Status:** Accepted
**Phase:** 36 (text/code + image multimodal) 振り返り
**Related ADRs:** ADR-0050 (Phase 36 技術判断本体), ADR-0046 (integration check), ADR-0048 (Phase 37 thread-files 規約, scope hand-off の対照), ADR-0038 (AIMessage.name 喪失, A1 risk 先行例)

## Context

Phase 36 (text/code + image multimodal) を 7 plans / 4 Success Criteria 全 PASS で完了した。技術判断本体は **ADR-0050** に集約済 (FileAttachment + additional_kwargs サイドカー + SDK 隔離 + vision fallback 2 段 + 履歴 UI 真実源 + A1 risk Wave 0 先行検証)。

しかし本 phase の実行を通じて、**今後 v6.0 milestone の Phase 32/33/34/38/39 や類似の "multi-app に跨る単一機能の展開" 系 phase で再利用すべき工程パターン**が 4 件浮かび上がった。これらは「特定機能の技術判断」ではなく「**フェーズ運用の工程設計**」レイヤの決定であるため、ADR-0050 とは分離して本 ADR で記録する。

具体的に解決したい問題:
- 同様の "checkpointer round-trip" risk を持つ機能 (例: 引用 source / tool_call_id / usage payload) を後続 phase で扱うとき、どのタイミングで risk 検証するか
- 1 phase で SuperChat / Gem / Canvas / Debate / Chat の 5 アプリすべて完全対応するのは時間的に不可能 — どこを切るか
- 動作確認で見つけた問題を後続 phase に持ち越す instrumentation
- chrome-devtools MCP を使った自動 E2E テストで遭遇する Chromium 制約の扱い

## Decision

### 1. Wave 0 risk-gate pattern: checkpointer round-trip risk を MVP 前に潰す

**ルール:** 新規機能が **LangGraph checkpointer** (PostgreSQL JSONB) で保存される `BaseMessage` 系フィールドに新規データを載せる場合、**Plan 01 (Wave 0)** に round-trip 検証を必ず置く。

具体策 (Phase 36 で機能した):
- Plan 01 = `tests/test_chat_history_additional_kwargs.py` (4 tests) + `tests/test_copilot_attachments_spike.py` (4 tests) を**実装前に書く**
- LangGraph `MemorySaver` + `AsyncPostgresSaver` 両方で round-trip を確認
- SDK の挙動を spike test で固定 (`session.send_and_wait(attachments=...)` の戻り値が SDK breaking change で変わるか検証)

なぜ MVP 前か: ADR-0038 (AIMessage.name が checkpointer の (de)serialize で落ちる) と同系統の risk は、機能を完全実装してから発覚すると **データモデル全体の手戻り** になる。Wave 0 で 1 plan 使って先に潰すと、Plan 02-06 (provider / route / worker / handler / frontend) を安心して並列展開できる。

対象判定 (Wave 0 risk-gate が必要な機能):
- per-message metadata を新規 field で運ぶ (`additional_kwargs` / 新規 reducer)
- AIMessage / HumanMessage の追加属性 (`name`, `tool_calls`, `tool_call_id` 等)
- 外部 SDK の Technical Preview API に依存する状態保存

対象外:
- frontend-only / route-only の追加 (checkpointer に到達しない)
- 既存 field の値変更のみ (型・構造は不変)

### 2. Single-app focus + multi-app defer: scope 制限の許容

**ルール:** 1 phase で **5 アプリ (Chat / SuperChat / Gem / Canvas / Debate) 完全対応** は時間配分上不可能と認める。中核アプリ (通常 ChatApp) のみフル対応、他は SubAgent 配線を **v6.1 defer** で許容する。

Phase 36 での適用:
- ChatApp: useAttachments + AttachmentButton + AttachmentChips + VisionWarningBanner + 履歴 bubble 復元すべて配線済
- SuperChat / Gem / Canvas / Debate: `useAttachments` import ゼロ、添付ボタン非表示
- `36-VERIFICATION.md` Open Issues に v6.1 hand-off を明文化

許容判断基準:
- 中核アプリでユーザーが機能を **体験できる** ことが Success Criteria 達成に十分か
- 他アプリで機能が **無いこと** が regression (既存機能を壊した) と区別されるか — 「ボタンが出ないが既存会話は動く」なら PASS

不許容ケース:
- 認証 / Auth / セキュリティ系: 全アプリで一貫しないとリスク
- データモデル変更: scope 制限すると schema drift

### 3. Hand-off discipline: deferred-items.md を後続 phase の input にする

**ルール:** 動作確認 / 実機テスト / E2E で発見した「本 phase スコープ外の問題」は、解決を試みず `.planning/phases/<NN-name>/deferred-items.md` の **指定 section** に追記する。次の関連 phase の input として明示的に参照される。

Phase 36 で機能した運用:
- セクション題: `## Phase <N> 完了後の動作確認で発見 (YYYY-MM-DD manual check)`
- 1 サブ section = 1 hand-off。**現象 / 現状の設計根拠 / 対応候補 / 推奨対応先 phase** の 4 項目で記述
- 例: 「Phase 38 hand-off: AI 生成ファイルの chat 内 inline プレビュー」を Phase 38 計画時の必読 input に指定

避けるべきパターン (やってはいけない):
- 発見した瞬間に scope を広げて当該 phase で fix → schedule slip + 過剰 scope creep
- 口頭 / Slack メモのみで残し、後続 phase planning で参照されない → silent debt
- VERIFICATION.md `Sign-off` に [x] を付けつつ deferred を `Open Issues` に書かない → 検証 PASS の根拠が曖昧

### 4. MCP test isolation: chrome-devtools MCP 環境の制約を E2E 知見に明文化

**ルール:** `chrome-devtools` MCP を使う自動 E2E は、Chromium が DevTools Protocol で intercept する `Page.setInterceptFileChooserDialog` / drag-drop DataTransfer 経路の挙動が **OS 経由と異なる** ことを前提に組む。テスト時は別ブラウザ実機 + 自動化は `DataTransfer + dispatchEvent('change')` で代替する。

具体的な既知制約 (Phase 36 で観測):
1. **File picker intercept**: `<input type="file">.click()` で OS ダイアログが開かない (Page.fileChooserOpened が MCP 側に飛ぶ)。E2E checklist のメモにも 5/11 時点で同様事象記録あり
2. **Drag-drop DataTransfer の差異**: MCP 接続中 Chromium で drag drop すると `useAttachments.onDrop` 経由の D-14 dict 構築が壊れ、SDK に空 prompt が渡って `ValueError("No generation chunks were returned")` が発生する (別ブラウザでは正常)

対応方針:
- E2E 自動テスト: `DataTransfer + dispatchEvent('change')` で添付経路を再現
- 人間 manual check: chrome-devtools MCP **に接続していない** 別ブラウザ window で行う
- 本制約は Phase の bug ではないため、deferred-items にも fix 対象として書かず、**E2E 知見** として ADR に記録 (次 phase で同じ罠を踏まないため)

## Alternatives Considered

### 代替 1A: Wave 0 risk-gate を省略し full 実装中に検証

ADR-0038 (AIMessage.name 喪失) の発覚は実装後で、修正に大幅な手戻りが発生した。Phase 36 は同系統 risk を Wave 0 で先取りすることで Plan 02-06 を並列展開できた。省略すれば手戻り risk が再発する → 採用しない。

### 代替 2A: 1 phase で全アプリ完全対応を強行

時間的に 2-3 weeks の phase が 1-2 month に伸び、milestone schedule が崩れる。SuperChat / Gem / Canvas / Debate での attachment UX は中核機能ではなく、ChatApp で動作確認できれば Success Criteria は満たせる。

### 代替 2B: 中核アプリ + Phase 36.1 polish phase で他アプリ対応

Decimal phase (X.1) は本来 gap closure 用。新規アプリ配線を polish 扱いするのは責務不整合。v6.1 milestone で正規 phase として扱う方が文脈一貫性がある → 採用しない。

### 代替 3A: hand-off を新規 ADR に書く

ADR は「決定」記録。動作確認の発見は "open question" であり ADR にはまだ早い。当該 phase の `deferred-items.md` が短命でテキストが軽い受け皿 → 採用。

### 代替 4A: chrome-devtools MCP を使わず Playwright / Puppeteer 直接利用

OS ダイアログ操作は確かに楽になるが、Claude Code session から制御できなくなる (orchestrator が MCP 経由で見える browser 状態を活用できない)。本制約は ADR 知見化で十分回避可能 → MCP は維持。

## Consequences

### Positive

- **後続 multimodal / metadata 系 phase** (例: 引用 source 表示, tool_call_id usage UI, conversation export) で同じ Wave 0 risk-gate を再利用できる。Phase 36 が確立した `tests/test_chat_history_additional_kwargs.py` テンプレートを model にできる
- **scope 制限が明示** されるので、v6.0 milestone schedule に対する phase 工数見積もりが安定。SuperChat etc. の addressing は v6.1 milestone で正規 phase 化することで milestone 単位の計画性が出る
- **動作確認の発見が後続 phase の input** になることで、user feedback / manual check の結果が "feedback log" として蓄積する。Phase 38 計画時に Phase 36 deferred-items.md を必読化する運用が成立
- **MCP test isolation** が明文化されているので、E2E checklist 起票時に「別ブラウザで実施」「MCP 経由は `DataTransfer + dispatchEvent('change')`」が default 手順として記載できる

### Negative

- **scope 制限の許容** は user 体験で「機能が部分的にしか出ない」状態を作る。SuperChat で添付ボタンが見えない疑問が出る可能性は残る — `36-VERIFICATION.md` Open Issues + UI 上の tooltip / placeholder で誘導が必要 (Phase 34 で検討)
- **Wave 0 risk-gate** は plan 1 個を消費するため phase 全体の plan 数が増える (Phase 36 は 7 plans = うち 1 plan 検証専用)。小規模機能では overhead になりうるので「対象判定」基準で除外できることを明示
- **MCP 制約は将来 chrome-devtools MCP のバージョンアップで変わる可能性**。本 ADR の §4 はそのまま固定化せず、MCP version up 時に再検証 (例: 2026 後半に MCP が file chooser handler を user-friendly に exposed する可能性)

### Neutral

- 本 ADR は **process / workflow** レイヤなので、特定の技術 stack に依存しない。将来 Copilot SDK → 別 provider / LangGraph → 別 framework に移行しても、§1 / §2 / §3 / §4 の patterns はそのまま再利用可能

## Implementation References

- Wave 0 risk-gate 実装例: `.planning/phases/36-text-code-image-multimodal/36-01-PLAN.md`, `tests/test_chat_history_additional_kwargs.py`, `tests/test_copilot_attachments_spike.py`
- scope 制限の明文化: `.planning/phases/36-text-code-image-multimodal/36-CONTEXT.md` D-? (Claude's Discretion: ChatApp 中心), `36-VERIFICATION.md` Open Issues, ADR-0050 §Consequences (SubAgent 配線は v6.1)
- hand-off 運用: `.planning/phases/36-text-code-image-multimodal/deferred-items.md` (§Phase 36 完了後の動作確認で発見)
- MCP test isolation: `.planning/phases/36-text-code-image-multimodal/36-E2E-CHECKLIST.md` (Page.handleFileChooser 注記), `36-MANUAL-CHECK.md` (A-2 / A-4 メモ — 別ブラウザで PASS 確認)

## Notes

- 本 ADR の §1 (Wave 0 risk-gate) は ADR-0038 (AIMessage.name 喪失) を **先行例** として参照する。`AIMessage.name` が落ちる現象は本来 Phase 35 以前で発覚すべきだったが、当時 Wave 0 検証 pattern が確立していなかった
- §2 (scope 制限) は ADR-0048 (Phase 37 thread-files folder 規約) と **対の構造**。Phase 37 が読取側 / Phase 36 が書込側を担い、SubAgent 配線は v6.1 でまとめて完成させる
- §4 (MCP test isolation) は次 phase で `playwright-skill` 等の代替自動化を試す際にも参照される予定
