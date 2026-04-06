---
created: 2026-04-06T14:17:45.555Z
title: chat / superchat のチャット上部の Agent 列挙表示がライト/ダークモード未対応
area: ui
files: []
---

## Problem

Chat および SuperChat のチャット画面上部に表示されている Agent の列挙 UI（バッジ・タグ等）が、ライトモードとダークモードの切り替えに対応していない。
具体的にはテキスト色・背景色がハードコーディングされており、ダークモード時に視認性が低下する（または逆にライトモードで崩れる）。

## Solution

対象コンポーネント（`frontend/src/components/` 配下の Chat / SuperChat 関連コンポーネント）の Agent 列挙部分のスタイルを、CSS 変数またはテーマ対応クラス（`dark:` Tailwind プレフィックス等）で定義し直す。
ライト/ダーク双方で視認性を確認してからコミットする。
