---
created: 2026-04-14T06:35:25.435Z
title: AI が操作しやすい画面構成を考える（data-ai-role 属性の導入）
area: ui
files: []
---

## Problem

AIエージェント（Claude Code や Chrome DevTools MCP 経由のブラウザ操作）が画面を自動操作する際、
DOM 要素を意味的に識別する手段が乏しい。CSS クラス名や要素の階層構造に依存するため、
UIの実装変更によって壊れやすく、AIが「どのボタンが何のためにあるか」を判断しにくい。

例：DebateChat の「送信ボタン」「ターン切り替え」「エージェント選択」が要素の構造からしか判別できない。

## Solution

フロントエンドコンポーネントに `data-ai-role` / `data-ai-label` 等のカスタム属性を付与する設計を導入する。

例：
- `data-ai-role="send-button"` — メッセージ送信ボタン
- `data-ai-role="thread-item"` — スレッドリストの各アイテム
- `data-ai-label="新しいスレッド"` — ボタンの意味的ラベル

これにより AI は `querySelector('[data-ai-role="send-button"]')` で確実に要素を特定でき、
自動テスト・操作スクリプトも安定する。設計方針（どの属性を標準化するか）を先に決めてから
主要コンポーネントに順次付与する形が望ましい。
