---
created: 2026-04-16T10:08:34.157Z
resolved: 2026-05-13
resolution: Phase 39 Plan 39-02 (D-01) で「ドキュメント化のみ」と decision を確定し ADR-0053 (`docs/adr/0053-mermaid-source-default-rationale.md`) に明文化。`'source'` default を恒久化する根拠が記録され、MermaidBlock.tsx 冒頭コメントから 1-hop でリンク。View hang の本質調査・修正は v6.1+ spike として STATE.md "Hand-offs to next phases" に defer 済。
title: Mermaid View デフォルト時の OS ハング問題を調査・修正
area: ui
files:
  - frontend/src/components/MermaidBlock.tsx
---

## Problem

MermaidBlock の初期表示モードを `'view'` にすると、チャットで Mermaid コードブロックを含む応答を受信した際にブラウザ（および OS 全体）がハングする。

原因候補:
- `mermaid.render()` がコンポーネントマウント時に呼ばれ、複数ブロックの同時 render で無限ループ的なレイアウト計算が発生
- `dangerouslySetInnerHTML` で挿入された SVG 内の `<style>` / `<foreignObject>` が継続的なレイアウト再計算を引き起こす
- mermaid ライブラリ内部の DOM ウォッチャーが React の再レンダリングと競合

現状は `'source'` デフォルトで回避しているが、ユーザー体験としては View デフォルトが理想。

## Solution

調査方針:
1. Chrome DevTools Performance タブでプロファイリング（render 1 回の CPU 時間を計測）
2. `mermaid.render()` の戻り SVG に含まれる `<style>` タグの animation/transition を除去してみる
3. SVG を `<iframe srcdoc>` で完全隔離して描画する方式を検証
4. Web Worker で mermaid render を実行し、結果の SVG 文字列のみメインスレッドに返す方式を検討
5. `mermaid.renderAsync()` やキュー制御で同時 render 数を制限する
