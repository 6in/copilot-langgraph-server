# 0037. チャット UI 一括機能強化（レンダリング・操作・AG Grid）

**Date:** 2026-04-16  
**Status:** Accepted

## Context

チャット UI に複数の改善要望が溜まっていた。個別に対応すると main へのマージが頻繁になるため、関連する TODO を 3 グループに分類し、グループごとに親ブランチ → 子ブランチの 2 段階 squash merge 構成で一括実装した。

- **グループ A（レンダリング）**: Markdown スペーシング縮小、Mermaid.js ダイアグラム描画
- **グループ B（操作）**: AI 応答キャンセルボタン（SSE 中断）、スレッド一括削除
- **グループ C（AG Grid）**: セルブロック選択フック移植、Canvas テンプレートに AG Grid 追加

## Decision

### ブランチ戦略

```
main
 ├─ feature/chat-rendering-enhancements   ← A 親
 │   ├─ feature/markdown-spacing           → squash → 親
 │   └─ feature/mermaid-rendering          → squash → 親
 ├─ feature/chat-interaction-enhancements ← B 親
 │   ├─ feature/cancel-button              → squash → 親
 │   └─ feature/bulk-delete-threads        → squash → 親
 └─ feature/ag-grid-enhancements          ← C 親
     ├─ feature/ag-grid-block-selection    → squash → 親
     └─ feature/canvas-ag-grid-template    → squash → 親
```

子ブランチ → 親に squash merge → 子ブランチ削除、最後に親 → main に squash merge。

### Mermaid.js の設計判断

1. **デフォルト Source モード** — View モードをデフォルトにすると mermaid の render がページ読み込み時に走り、ブラウザがハングする。オンデマンド render（View ボタンクリック時のみ）で回避。
2. **`dangerouslySetInnerHTML` で SVG を描画** — blob URL + `<img>` アプローチは `<foreignObject>`（絵文字・HTML テキスト）がブラウザのセキュリティ制限で描画されない。インライン SVG で表示し、SVG の固定 width/height を除去して viewBox ベースのスケーリングに。
3. **Monaco Editor で編集可能な Source モード** — ユーザーが Mermaid ソースを修正して View で即確認できる。編集はローカル状態のみ（チャット履歴に保持しない）。
4. **PNG 画像コピーは見送り** — `<foreignObject>` を含む SVG は Canvas API で taint される制限があり、PNG 変換が失敗する。テキストコピーに統一。

### キャンセルボタン（Phase 1）

フロントエンドのみの実装（SSE の `EventSource.close()` + polling timer クリア + 状態リセット）。バックエンドのジョブは走り続けるが、UX として十分実用的。Phase 2（バックエンドキャンセル）は別 TODO。

### セルブロック選択

既存の `useBlockSelection` フックを `work/web-api-proxy/packages/apps/app-template/` から移植。`redrawRows()` による全行再描画でドラッグ中にちらつきがあるが、機能は問題なし。

## Alternatives Considered

- **Mermaid: `<img src={blobUrl}>` アプローチ** — foreignObject が描画されず断念
- **Mermaid: detached container / visibility:hidden で render** — `getBBox` エラーまたは無限レイアウト計算でブラウザハング
- **Mermaid: `useEffect` で自動 render** — コンポーネントマウント時に走ると OS レベルでハングする場合あり。オンデマンドに変更
- **一括削除: バッチ API エンドポイント追加** — フロントの `Promise.all` で単体 DELETE を並列実行する方が実装コストが低く、200 名規模では十分
- **キャンセル: バックエンド側のジョブ中断** — Copilot SDK の `send_and_wait` がブロッキングで途中キャンセル不可。Phase 2 として分離

## Consequences

### Positive

- 6 つの TODO を 1 セッションで完了、main への影響を最小化
- Mermaid 描画は foreignObject 付きの複雑な図も正しく表示
- キャンセルボタンにより長時間応答待ちの UX が改善
- 一括削除でテスト中のスレッド整理が大幅に効率化

### Negative / Gotchas

- **Mermaid のパフォーマンス**: mermaid パッケージは ~1MB。lazy load しているが、View クリック時の初回ロードは遅い
- **Mermaid View デフォルト化は危険**: 複数の Mermaid ブロックが同時に render されると OS ハングの可能性あり。Source デフォルトを維持すること
- **PNG コピー未対応**: foreignObject + Canvas API の制限は根本的。将来 `html-to-image` 等のライブラリ導入が必要
- **AG Grid ちらつき**: `redrawRows()` の代わりに `refreshCells()` で部分更新すれば改善可能だが、優先度低
- **キャンセル Phase 1 のみ**: バックエンドジョブは走り続ける。リソース浪費は 200 名規模では許容範囲
