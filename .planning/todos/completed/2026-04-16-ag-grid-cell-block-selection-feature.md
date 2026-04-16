---
created: 2026-04-16T03:40:00.000Z
title: AG Grid にセル選択（ブロック選択）機能を追加
area: ui
files:
  - frontend/src/components/ChatAgGridTable.tsx
---

## Problem

チャット内の AG Grid テーブルでセル範囲をドラッグ選択してコピーする機能がない。現状は TSV コピーボタンで全行コピーのみ。特定のセル範囲だけを選択してクリップボードにコピーしたいケースに対応できない。

## Solution

`/media/psf/workspaces/poc/fenext` 配下の既存実装を参考に、`useBlockSelection` フックを移植する。

### 参考ドキュメント

| ファイル | 内容 |
|----------|------|
| `work/web-api-proxy/doc/ag-grid-enhance.md` | 移植ガイド（使い方・組み込み手順・カスタマイズ方法） |

### 参考ソースコード

| ファイル | 役割 |
|----------|------|
| `work/web-api-proxy/packages/apps/app-template/src/hooks/useBlockSelection.ts` | カスタムフック本体（テンプレート版 — 移植元として最適） |
| `work/web-api-proxy/packages/apps/app-dictionary/src/hooks/useBlockSelection.ts` | カスタムフック本体（app-dictionary 版） |
| `work/web-api-proxy/packages/apps/app-fp-cls-viewer/src/hooks/useBlockSelection.ts` | カスタムフック本体（app-fp-cls-viewer 版） |
| `work/web-api-proxy/packages/apps/app-template/src/ag-grid-overrides.css` | ドラッグ中テキスト選択抑制 CSS |
| `work/web-api-proxy/packages/apps/app-template/src/App.tsx` | フック使用箇所（組み込み例） |

### 移植手順（想定）

1. `app-template` の `useBlockSelection.ts` を `frontend/src/hooks/` にコピー・調整
2. `ag-grid-overrides.css` の必要部分を `theme.css` に追加
3. `ChatAgGridTable.tsx` で `useBlockSelection` を組み込み
4. 選択範囲のコピー（Ctrl+C / ボタン）を実装
5. ドラッグ中のテキスト選択抑制を確認

### 注意

- 参考実装のパスはすべて `/media/psf/workspaces/poc/fenext` 配下（Parallels 共有フォルダ）
- 実装時に `ag-grid-enhance.md` のガイドを先に読んでから着手すること
