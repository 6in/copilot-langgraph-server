# 0029. UI Todo バッチ実装 — Orochi ブランディング・Canvas/DebateChat 機能改善

**Date:** 2026-04-14  
**Status:** Accepted

## Context

v5.0 Agent Tool Platform（Phase 20–25）完了後に蓄積された UI 系 Todo 4件を一括実装した。

1. **アプリタイトル変更** — "Copilot Chat" → "Orochi Chat"（社内名称統一）
2. **CanvasChat New Chat HTML 漏れ** — 新規スレッドに前回の HTML がプロンプトとして混入する不具合
3. **CanvasScreen インクリメンタルサーチ** — アプリ数増加時の UI 課題
4. **DebateChat 継続討論コメント入力** — ターン終了後に補足コメントを添えて延長できない

## Decision

### Orochi ブランディング

- `frontend/index.html`・`static/index.html` の `<title>` を "Orochi Chat" に変更
- `Header.tsx`・`MenuScreen.tsx` の表示テキストを変更
- Google Fonts **Rajdhani**（weight 600/700）を導入し、`#a78bfa → #7c6ff7 → #38bdf8` の CSS グラデーションテキストを適用

### CanvasChat HTML 漏れ修正（根本対処）

当初 `handleNewChat` で `setCurrentHtml(null)` を呼ぶ修正を実装したが、非同期レースで `CanvasPane` の `onHtmlChange` に上書きされることが判明。

根本修正として `handleSend` 内の埋め込み条件を変更した:

```ts
// 変更前
const prompt = currentHtml ? `${text}\n\n（現在の HTML）\n\`\`\`html\n${currentHtml}\n\`\`\`` : text;

// 変更後
const shouldEmbed = currentHtml && canvasApp && canvasApp.thread_id === threadId;
const prompt = shouldEmbed ? `${text}\n\n（現在の HTML）\n\`\`\`html\n${currentHtml}\n\`\`\`` : text;
```

`canvasApp.thread_id === threadId` の確認により、旧スレッドの `canvasApp` が残留している状態でも新規スレッドへの HTML 漏れを防止する。

### CanvasScreen インクリメンタルサーチ

`useState` + `Array.filter` のシンプルな実装。アプリが1件以上存在する場合のみ検索バーを表示。検索対象は `thread_label ?? name`。

### DebateChat 継続討論コメント入力

`ExtensionBanner` に `<textarea>` を追加し、`extensionComment` state を `DebateChatPanel` で管理。`handleExtend` でコメントがある場合は `延長\n\n${comment}` として送信。コメント送信後は `setExtensionComment('')` でリセット。

## Alternatives Considered

- **HTML 漏れ: `setCurrentHtml(null)` のみ** — 実装したが非同期レースで不十分と判明。`thread_id` チェックの方が状態の正確性に依存しないため優れている。
- **CanvasScreen: 外部ライブラリ（fuse.js 等）** — アプリ数が多い場合でも `Array.filter` で十分なシンプルさのため却下。
- **Rajdhani 以外のフォント** — Orbitron（SF 的すぎる）・Exo 2（汎用的すぎる）と比較し、Rajdhani の鋭い幾何学的スタイルが "Orochi" の名称イメージに合致と判断。

## Consequences

**ポジティブ:**
- アプリ名が社内名称 "Orochi Chat" に統一された
- Canvas の New Chat で前回 HTML が混入しなくなった（`thread_id` チェックは将来のスレッド切り替え時も機能する）
- DebateChat で討論終了後にコメントを添えて継続できるようになった

**注意点:**
- Rajdhani は Google Fonts CDN に依存。オフライン環境ではフォールバック（sans-serif）になる
- `canvasApp.thread_id` が `null` の canvas app（旧データ）では HTML 埋め込みがスキップされる。旧データのマイグレーションは未対応
