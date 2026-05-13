# 0053. Mermaid View デフォルトを Source 固定とする (UIFIX-01)

**Date:** 2026-05-13
**Status:** Accepted

## Context

v5.0 期間中、複数の Mermaid コードブロックを含む AI 応答を受信した際に、`MermaidBlock` の初期表示モードを `'view'` にすると Chromium のみならず OS 全体がフリーズする現象 (OS-level hang) を観測した。再現は本プロジェクト docker-compose 環境 + 開発用ブラウザ (Chromium remote-debugging) 上で確実に発生し、復帰には強制終了を要する。

現状コード `frontend/src/components/MermaidBlock.tsx:36` では `useState<'view' | 'source'>('source')` により **source-default** に設定して回避済み。ただしこれは「観察ベースで View → Source に変えただけ」の暫定対応であり、根本原因の解明には至っていない。

根本原因候補は `.planning/todos/pending/2026-04-16-mermaid-view-os.md` で 5 つに整理してある:

1. `mermaid.render()` の同時呼び出し競合 — 複数ブロックが mount で同時に render する
2. SVG 内 `<style>` / `<foreignObject>` による継続的レイアウト再計算
3. Mermaid ライブラリの内部 DOM ウォッチャーと React 再レンダリングの衝突
4. 大量 SVG ノード生成によるブラウザのレイアウト/ペイント負荷
5. Monaco Editor (Source タブ用) と Mermaid 描画の競合

Phase 39 (ui-polish) では UIFIX-01 を「再現条件と回避策付きでドキュメント化」する方針 (D-01) を確定したため、観察ベースの暫定対応を明示的な **恒久対応** に格上げし、その根拠を ADR として記録する。

## Decision

1. `'source'` default を **恒久化** する (現状の `MermaidBlock.tsx:36` を維持)。
2. View モードへの切り替えは「ユーザーが View ボタンを押したときのみ」発生させる (lazy on-demand)。コンポーネント mount 時には View の `mermaid.render()` を一切呼ばない。
3. 恒久修正候補 (下記 Alternatives) は v6.1+ milestone の `/gsd-spike` セッションで個別に検証する。Phase 39 のスコープでは取り扱わない。
4. `frontend/src/components/MermaidBlock.tsx` 冒頭コメントに 1-2 行で本 ADR (0053) への pointer を埋める。後続レビュー者がコードから 1 hop で本 ADR を読めるようにする。

## Alternatives Considered

| 案 | 概要 | Trade-off |
|----|------|-----------|
| iframe srcdoc 隔離レンダリング | `<iframe srcdoc>` で SVG を完全に独立したドキュメントコンテキストに分離 | 開発・テスト負荷増 (postMessage 経路、サイズ計測、コピー機能の再実装)。Phase 39 polish の粒度には重い |
| Web Worker での mermaid render | SVG 生成処理を worker スレッドへ移し、結果文字列のみメインに返す | Mermaid SDK は main thread の DOM 前提で書かれている可能性が高く、対応状況が未確認。要事前 spike |
| 描画 queue (直列化制御) | 複数 Mermaid ブロックの render を直列に並べ、同時実行を 1 に制限 | UX が体感で遅くなる (ブロック数 N に対して N 倍の遅延)。根本原因は同時 render 以外の可能性もあり、解決保証なし |
| `mermaid.renderAsync()` (v11+ API) | Mermaid 公式の async render API を使う | プロジェクトの mermaid version pin を上げる必要があり、影響範囲が広い。v6.1+ で他の Mermaid 関連改善とまとめて検証するのが妥当 |

## Consequences

### Positive

- OS-level hang を確実に回避できる (v5.0 期間中に source-default で実績あり、UIFIX-01 の ROADMAP 合格基準 = 「再現条件と回避策付きで解消」を満たす)。
- Source モードでは Monaco Editor が即座に表示され、コードの確認・コピー・編集が初期表示時点で可能になる (View からの切り替え操作 1 回が不要)。
- ADR 化により「なぜ View default にしないのか」が後続レビュー者・AI agent から ADR INDEX 経由で追跡可能になる。

### Trade-offs

- 初見ユーザーは View ボタンを押さない限り図 (SVG) を視認できない。ただしヘッダー左の `View / Source` トグルは常時可視のため、操作は 1 クリックで完結する。
- 根本原因の特定と本質修正は v6.1+ に持ち越し。技術負債として `.planning/todos/pending/2026-04-16-mermaid-view-os.md` を引き続き残す。

## Related

- ADR-0037 (Chat UI batch enhancements — Mermaid 関連の初期実装)
- ADR-0040 (UI 改善バッチ — Mermaid 画像コピー、`html-to-image` 採用)
- todo: `.planning/todos/pending/2026-04-16-mermaid-view-os.md` (調査方針 5 案の原典)
