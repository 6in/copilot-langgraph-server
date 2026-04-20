# 0047. Milestone cleanup phase — 帳簿整合 bookkeeping を独立 decimal phase に分離

**Date:** 2026-04-20
**Status:** Accepted
**Related:** ADR-0026 (ADR patterns.md + GSD 統合), ADR-0045 (Phase 31 observability), ADR-0046 (integration-check surfaced silent failures)

## Context

v5.0 Agent Tool Platform milestone (Phases 20–31, 25 REQ-ID) が機能的に全完了した 2026-04-20 時点で、`gsd-integration-checker` 監査は全 17 wiring / 7 E2E flow PASS を返したが、planning ドキュメント側に 6 件の bookkeeping drift が残存していた:

- ROADMAP.md に Progress table が 2 つあり Phase 30 / 31 の状態が食い違う
- milestone マーカーが `📋 active` のまま
- REQUIREMENTS.md 全 25 REQ-ID が traceability table で `Not started` のまま
- Phase 20/21/22/23/24/25/27/28/29 の 9 本の VALIDATION.md が `status: draft` / `nyquist_compliant: false` のまま（`verify-phase` 完了時に `validated` 遷移が抜けていた）
- Phase 30 には VALIDATION.md 自体が存在しない（Phase 26 で導入された artifact 規約より前に完了したため）

監査レポートは全体を `tech_debt` と分類 — 機能に影響なしだが、`/gsd-complete-milestone v5.0` で archive 前に整合させるべき帳簿不一致。

選択肢は 2 つ:

- **Option A:** `/gsd-complete-milestone v5.0` をそのまま実行し、tech debt として受容
- **Option B:** cleanup 先行 — 独立 phase として bookkeeping を plan → execute → verify し、帳簿 100% 整合後に archive

単純な機械的作業 (YAML frontmatter 9 件書き換え + 新規 VALIDATION.md 1 本作成) だが、履歴として archive されるドキュメントなので後から見た人の混乱を避けたい。

## Decision

**Option B を採用し、decimal phase `31.1` (`v5-milestone-cleanup`) を独立 phase として作成**。以下の運用パターンを確立する:

1. **decimal phase 番号の用途拡張**: これまで `15.1` のように「実機能の後処理」に使っていた decimal numbering を、milestone archive 直前の bookkeeping 集約にも流用する。次 milestone の主番号 (32+) を汚さず、かつ独立 phase として plan → execute → verify の GSD 規律を通す。

2. **作業を 2 層に分離**:
   - **Setup commit (phase 定義時に同一コミットで完結)**: ROADMAP.md と REQUIREMENTS.md の drift — 全 25 REQ-ID の `[x]` 化、milestone マーカー `📋 → ✅`、Progress table 統合、traceability status 更新。これらは「計画」ではなく事実の記録なので plan 化せず setup 時に一括修正する
   - **Plan → execute (GSD 規律を通す)**: artifact 書き換え作業 — VALIDATION.md frontmatter backfill と Phase 30 VALIDATION.md 新規作成。commit 粒度・atomic 性が重要なのでここは plan 化して executor agent を通す

3. **VALIDATION.md 遡及更新の正当化ルール**: `status: draft → validated` への後追い更新を許容するが、以下を満たすこと:
   - 対応 phase の VERIFICATION.md (または integration-check レポート) で PASS が確定している
   - `validated:` フィールドに backfill 実施日を入れる (`created:` は保持 — 当時の日付)
   - 本文末の Approval 行に backfill 経路を明記する（例: `validated 2026-04-20 (v5.0 milestone audit cleanup phase 31.1 で backfill)`）
   - VALIDATION.md 本文の Test Map や Wave 0 チェックボックスは当時のまま (stub 的な `⬜ pending` を残す) — 履歴として保持、Approval 行が代替表現

4. **Phase が存在しなかった VALIDATION.md の新規作成**: VERIFICATION.md が PASS 済みの phase (今回の Phase 30) に対しては、既存 VERIFICATION の Observable Truths と Required Artifacts を根拠に Phase 31 format の VALIDATION.md を遡及作成する。`status: validated` で直接登録し、`created:` も backfill 日。本文の Per-Task Verification Map は当該 phase の PLAN.md 群から機械的に抽出。

5. **Milestone audit report は不変**: `.planning/milestones/vN.0-MILESTONE-AUDIT.md` は時点スナップショットとして上書きしない。`missing_phases: [30]` 等の drift 記述はそのまま残し、解消は target artifact 側 (VALIDATION.md / ROADMAP.md / REQUIREMENTS.md) で表現する。

## Alternatives Considered

- **Option A: tech debt として受容**: `/gsd-complete-milestone v5.0` を即時実行し、6 件を既知の帳簿 drift として next milestone に持ち越し。最速だが archive 後に遡及修正するのは心理的ハードルが高く、次 milestone 着手時の参照コストが増える。社内 200 名規模 ✕ 32 phases の規模では「archive 時点で帳簿整合」を規律として固めたほうが長期コストが低いと判断。
- **ROADMAP/REQUIREMENTS も plan 化して統一**: すべてを plan → execute で処理し setup commit を使わない案。しかし実作業は「監査レポート通りに値を書き換えるだけ」で設計判断要素ゼロ、plan 化のオーバーヘッド (plan 生成 + checker + executor subagent) が本体作業 (十数行の edit) を大幅超過する。`/gsd-quick` すら過剰なレベル。plan 化の価値は「変更粒度・atomic 性・タスク分解が非自明」なときに発生するため、drift 修正そのものは setup で済ませた。
- **Phase 番号を主番号 (32) にする**: bookkeeping を `Phase 32` として新 milestone 側に入れる案。しかし v5.0 の archive 条件であって v5.0 の責務 — 番号上も v5.0 側に保つべき。decimal phase は「親 phase のスコープを継承して追補する意味」なので `31.1` が妥当。
- **古い milestone (v1.0〜v4.0) の draft VALIDATION.md も一括 backfill**: scope に入れる案。しかし 16 件以上残存しており、かつ古い milestone は既に archive 済みで影響範囲が広い。本 phase は「これから archive する v5.0」に scope を限定。古い milestone 側の drift は別 phase（あるいは永久に deferred）として扱う。

## Consequences

**Positive:**

- v5.0 milestone が「帳簿 100% 整合」で archive 可能。後続 milestone (v6.0 等) から振り返ったとき v5.0 planning artifact が first-class reference として使える
- `decimal phase = bookkeeping 集約点` というパターンが確立。次回も `32.1`, `45.1` のように main 番号を汚さず後処理フェーズを立てられる
- VALIDATION.md backfill の判断基準 (VERIFICATION.md PASS + Approval 行で backfill 明記) が明文化され、将来的な nyquist compliance 復旧作業で再利用可能
- `gsd-integration-checker` による「機能的 PASS / 帳簿 drift」の切り分けと、それに対応する 2 選択肢 (Option A: accept / Option B: cleanup) の運用が形式化

**Negative / Gotchas:**

- **Subagent オーバーヘッド**: 本 phase の実作業は ~700 行の YAML 書き換え + 97 行の新規 md 1 本、人の手で 10 分。それを plan → planner → checker → executor × 2 → verifier の 5 agent spawn に載せたのは儀礼的側面が強い。単純 bookkeeping なら `/gsd-quick` で済ませる判断も合理的 — 今回は milestone archive 直前という象徴性を重視したが、毎回この ceremony を強制すべきではない
- **STATE.md と ROADMAP.md の progress 集計 scope 不整合**: STATE.md frontmatter は milestone scope (`total_phases: 13 / total_plans: 35`) だが ROADMAP.md frontmatter は project scope (`32 / 91`)。本 ADR ではこの不整合に触れず両者を 100% に合わせたが、次 milestone 遷移時に scope の再定義が必要（どちらを canonical にするか未決）
- **Audit レポートを書き換えない方針の副作用**: `v5.0-MILESTONE-AUDIT.md` は `missing_phases: [30]` / `partial_phases: [...]` のまま残る。解消は target artifact でのみ表現されるため、監査レポート単独を読んだ人は drift が現存すると誤解する可能性がある。AUDIT.md 側に `## Resolution` セクションで「Phase 31.1 にて解消」と 1 行書き足すのが軽い救済策だが本 phase では実施せず（次に cleanup phase を立てる際の検討事項）
- **遡及 VALIDATION.md の信憑性リスク**: Phase 30 の 30-VALIDATION.md は実行時点 (Phase 30 実行中) に書かれた一次資料ではなく、VERIFICATION.md を一次資料とする二次的な artifact。Test Map の精度は PLAN.md 読み取りの正確さに依存し、誤った Test Map が残れば将来の nyquist audit で誤診を招く可能性がある。`validated:` != `created:` の対関係と Approval 行で「遡及作成」を明示することで誤解は最小化しているが、PLAN と VALIDATION が同一人物・同一時点で書かれていないという質的差は残る
- **cleanup phase を常設化すると計画性が下がる**: 「後で cleanup phase で整えれば OK」という心理的エスケープが発生し、各 phase 実行時の verify-phase 規律 (`status: validated` 遷移) を後回しにするインセンティブが働く。本来は cleanup phase が不要であることが理想 — 今回の発生源は「Phase 23 以前は VERIFICATION.md 規約がなかった」「verify-phase の `status: validated` 自動遷移が抜けていた」という過去の規約変更。根治策は各 phase 完了時の verify-phase で `status: validated` が書き込まれることを確認する pre-archive チェックを `/gsd-complete-milestone` 側に組み込むこと（本 ADR の scope 外、別途検討）
