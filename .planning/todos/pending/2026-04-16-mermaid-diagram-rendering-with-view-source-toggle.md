---
created: 2026-04-16T04:00:00.000Z
title: チャットパネルに Mermaid.js ダイアグラム描画 + ビュー/ソース切り替え機能を追加
area: ui
files:
  - frontend/src/components/MarkdownMessage.tsx
  - frontend/package.json
---

## Problem

AI がチャットで Mermaid 記法（```mermaid ブロック）を返した場合、現在は Monaco エディタでソースコードとして表示されるだけで、ダイアグラムとしてレンダリングされない。フローチャート・シーケンス図・ER 図などを視覚的に確認できず、ユーザーは別ツールにコピペして描画する必要がある。

## Solution

`MarkdownMessage.tsx` の code ブロック処理で `language === 'mermaid'` を検出し、Mermaid.js でダイアグラムを描画する専用コンポーネントを追加:

### 1. 依存追加

```bash
cd frontend && bun add mermaid
```

### 2. MermaidBlock コンポーネント

- `React.lazy` で遅延読み込み（mermaid は ~1MB のバンドル）
- `mermaid.render()` で SVG を生成し `dangerouslySetInnerHTML` で描画
- ThemeContext 連動: `mermaid.initialize({ theme: isDark ? 'dark' : 'default' })`

### 3. ビュー/ソース切り替え

```
[▶ View] [< > Source]
┌─────────────────────┐
│  (Mermaid SVG 図)    │  ← View モード（デフォルト）
└─────────────────────┘

[▶ View] [< > Source]
┌─────────────────────┐
│  graph TD            │  ← Source モード（Monaco エディタ）
│    A --> B           │
└─────────────────────┘
```

- デフォルトは View（ダイアグラム描画）
- Source クリックで既存の Monaco エディタ表示に切り替え
- タブ風のトグルボタンを CodeBlock ヘッダーバーに配置

### 4. MarkdownMessage への組み込み

```tsx
if (language === 'mermaid') {
  return <MermaidBlock value={value} monacoTheme={monacoTheme} theme={theme} />;
}
```

既存の `canvashtml` (CollapsibleCodeBlock) と同様のパターンで分岐追加。

### 注意

- Mermaid の `render()` はエラーを投げうる（不正な記法）→ try/catch でソースフォールバック
- SVG はインラインなのでサイズ制御が必要（max-width: 100%, overflow: auto）
- dark/light 切り替え時に再レンダリングが必要（mermaid の theme は初期化時に決まる）
