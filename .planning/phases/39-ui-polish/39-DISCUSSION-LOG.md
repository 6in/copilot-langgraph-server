# Phase 39: UI バグ潰し + Polish 枠 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-12
**Phase:** 39-ui-polish
**Areas discussed:** UIFIX-04 確定リスト, UIFIX-03 整理範囲, UIFIX-02 修正方針, UIFIX-01 踏み込み, UIFIX-04 上限ポリシー

---

## 議論する範囲（メタ選択）

| Option | Description | Selected |
|--------|-------------|----------|
| UIFIX-04 確定リスト | polish 枠で潰す小バグの確定。AskMe regression は ROADMAP hand-off 確定。それ以外 (📎 入口段差 / TS 7件 / pytest 数値 drift / pre-existing 14+4 / cross-browser) を選別 | ✓ |
| UIFIX-01 落とし所 | Mermaid hang の踏み込み深さ。'source' default 維持のみ / 恒久修正 / spike どまり | （後段で別途確認） |
| UIFIX-03 整理範囲 | test_sse + JobStore dead code の整理深さ。最小 / 中 / 大 | ✓ |
| UIFIX-02 修正方針 | CollapsibleCodeBlock 横幅。Message バルーン full-width / min-width 実値 / Message group 分離 / 現状維持 | ✓ |

**User's choice:** UIFIX-04 確定リスト, UIFIX-03 整理範囲, UIFIX-02 修正方針 を選択。UIFIX-01 は明示的に再確認するため別途。

---

## UIFIX-04 確定リスト

AskMe regression (5 apps) は ROADMAP hand-off で確定済みのため option から除外。選ばなかったものは v6.1+ へ defer。

| Option | Description | Selected |
|--------|-------------|----------|
| Phase 38 TSエラー 7件 | useThreads.bulkRemoveThreads return 型不足 (6 consumer) + ThemeContext.Theme 型未 export (MermaidBlock import)。tsc surface | ✓ |
| test もろもろ修正バンドル | test_generate_mcp_artifacts.py の == 6 → == 8 + test_mcp_server.py の cwd 引数 7 件 (TypeError) | ✓ |
| Phase 36 pre-existing 14+4errors | test_api_chat / test_api_jobs / test_sse / test_worker / test_graph etc 計 14 failures + 4 errors。JWT cookie / psycopg AsyncMock / LLM mock astream / catalog drift / hook env の 5 パターン | ✓ |
| 📎 入口段差 (option A) | activeThreadId === null 時の AttachmentButton tooltip 文言改善 (5-10 行)。本質修正 (lazy auto-create option B) は Phase 34 候補のまま | ✓ |

**User's choice:** 全 4 option + AskMe regression。
**Notes:** Phase 36 14+4 errors は量が多いため polish phase 肥大化リスクを認識した上で取り込み。Phase 36 deferred-items.md の分類表を planner が wave 分割の判断材料に使う。

---

## UIFIX-03 test_sse + JobStore dead code 整理範囲

| Option | Description | Selected |
|--------|-------------|----------|
| 最小 (test 修正のみ) | test_sse_done_signal を Redis polling mock 化 or 削除。JobStore.queues / register_sse / unregister_sse / notify の queue 枝削除。test_job_store.py の register/unregister 削除。notifier.py は no-op として残す | ✓ |
| 中 (notify() も整理) | 最小 + notify() も削除し、notifier.py を Redis 直接書き込み形に簡素化。notifier 表面 API は維持 | |
| 大 (notifier を Redis 専用に再設計) | notifier 構造そのものを見直し Redis polling モデルを明示的にした API に再設計。Phase 4 設計負債の clearing | |

**User's choice:** 最小 (test 修正のみ)
**Notes:** notifier.py の表面 API（progress / done / send_token）は handlers 4 経路で使われているため温存。将来 SSE backend 切替の拡張余地として残す。

---

## UIFIX-02 CollapsibleCodeBlock 横幅修正アプローチ

| Option | Description | Selected |
|--------|-------------|----------|
| Message バルーン側を full-width 固定 | chatscope `.cs-message__content` を Phase 35 で確立した var() 駆動置換パターンで full-width / min-width 指定。CollapsibleCodeBlock 側は変えず、chat 全体で長いコードが安定 | ✓ |
| CollapsibleCodeBlock に min-width 実値 | コードブロック単体に min-width: min(640px, 100%) 等。実値で試せるが、chat コンテナ幅より広かった場合に overflow-x。他の Markdown 要素は依然バルーンが縮むため一貫性が低下 | |
| Message group 分離 | コードブロックを chatscope `Message` の外（独立 container）に切り出し、バルーン制約から離脱。レイアウト変更が大きく UX 上わかりづらくなるリスク | |
| 現状維持 + 折り返し挙動補正 | Monaco editor の wordWrap: 'on' だけで例外ケースを拾う。表面のバルーン縮みはなおらない | |

**User's choice:** Message バルーン側を full-width 固定
**Notes:** Phase 35 base layer の var() トークンを再利用。`!important` は据え置き、値のみ修正の境界ルール (35-CONTEXT.md D-02) を遵守。

---

## UIFIX-01 Mermaid hang 踏み込み

gray area として明示的に選ばれなかったため、Phase 39 の踏み込みを明示的にロック。

| Option | Description | Selected |
|--------|-------------|----------|
| ドキュメント化のみ | 'source' default を恒久化 + 再現条件 / OS hang トリガー / View default を試さない理由を ADR + コメントに記録。View default 復帰は v6.1+ spike 候補 | ✓ |
| 軽めの spike (タイムボックス 1-2h) | DevTools Performance での計測 + iframe srcdoc 隔離のプロトタイプだけ試し、結果をドキュメント化。中間案 | |
| 恒久修正まで踏み込む | iframe srcdoc / Web Worker で View default を復帰。Phase 39 スコープが大きく膨らみ polish phase の趣旨を超える | |

**User's choice:** ドキュメント化のみ
**Notes:** UIFIX-01 success criteria 「再現条件と回避策付きで解消されている (or 恒久修正適用)」の前半（前者）を選択。

---

## UIFIX-04 上限ポリシー

polish 枠の打ち切り基準。

| Option | Description | Selected |
|--------|-------------|----------|
| 入り口で確定リストを freeze | CONTEXT.md で今回取り込む項目を完全リスト化。実行中に発見されたものは deferred-items.md で v6.1+ へ defer。Phase 39 のサイズを予測可能に保つ | ✓ |
| Wave 1 fix 中の余波は許容 | 同一ファイル / 同一テストスイートを触る際に見つかったツイレージ fix は Phase 39 で拾う。スコープ揺れあり | |
| Time-box | 作業日数で打ち切る。期限内で潰せなかったものは defer。GSD ワークフローと相性が低い | |

**User's choice:** 入り口で確定リストを freeze
**Notes:** 実行中に新規発見した UI 小バグは `.planning/phases/39-ui-polish/deferred-items.md` に書き、v6.1+ で観察ベース再評価する運用。

---

## Claude's Discretion

- Plan の wave 分割（5 項目を 1 wave / 複数 wave のどちらに割るか）は planner 判断
- D-06 の `notify()` body 削除 vs no-op stub 残置の選択は planner 判断（外部影響なし）
- UIFIX-02 の CSS override を `frontend/src/styles/` のどのファイルに置くかは Phase 35 base layer の構造に従う

## Deferred Ideas

- Mermaid View default 復帰の本質調査（iframe srcdoc / Web Worker / queue 制御 / mermaid.renderAsync）— v6.1+ `/gsd-spike` 候補
- `notifier.py` の Redis pub/sub 専用への再設計 — Phase 4 SSE 導入時の設計負債整理として v6.1+
- 📎 入口段差 option B（lazy auto-create）— Phase 34 候補のまま（空スレッド lifecycle 設計が必要）
- Phase 35 から繰り越した cross-browser (Edge/Safari) UAT — 環境準備が要るため Phase 39 では取り込まず、v6.1+ もしくは別の cross-browser polish phase
