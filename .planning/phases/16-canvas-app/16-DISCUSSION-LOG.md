# Phase 16: Canvas App — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the Q&A.

**Date:** 2026-04-07
**Phase:** 16-canvas-app
**Mode:** discuss
**Areas analyzed:** アプリ構造, エントリーポイントと Canvas App 一覧, システムプロンプト, Canvas Gem との差別化

---

## Area 1: アプリ構造 — CanvasChatApp レイアウト

| Question | Options Presented | Answer |
|----------|-------------------|--------|
| CanvasChatApp の基本レイアウト | GemChatApp + CanvasPane 統合 / 上下分割 | 左右分割（左チャット・右Canvas・サイズ変更可）|
| CanvasPane の表示タイミング | AI 応答時のみ自動表示 / 常時表示 | 最初から表示。Gem の画面とは切り離す |

---

## Area 2: エントリーポイントと Canvas App 一覧

| Question | Options Presented | Answer |
|----------|-------------------|--------|
| MenuScreen のエントリーポイント | Canvas カード1枚追加 / Canvas ハブ画面 | Canvas ハブ画面（一覧 + 新規作成）を指す |
| Canvas App 管理（一覧画面）の必要性 | スレッド単位で十分 / デプロイ済みアプリ一覧別途必要 | デプロイ済みアプリ一覧が別途必要 |

---

## Area 3: システムプロンプト — AI の振る舞い設定

| Question | Options Presented | Answer |
|----------|-------------------|--------|
| システムプロンプト設定方法 | コード内固定 HTML プロンプト / Canvas 専用 Gem（type=canvas）を内部作成 | Canvas 専用 Gem（type=canvas）を内部作成して使う |
| HTML 生成のプロンプト内容 | 「HTML のみで返す」お任程式 / 会話形式も許可 | 「HTML のみで返す」お任程式のプロンプト |

---

## Area 4: Canvas Gem との差別化

| Question | Options Presented | Answer |
|----------|-------------------|--------|
| MenuScreen 表示方式 | Gems カードの横に Canvas カード追加 / 「AI Apps」セクション新設 | Gems カードの横に Canvas カードを追加（推奨） |
| Canvas Gem との将来マージ | Phase 16 では完全独立 / GemsScreen からも起動可能に | Phase 16 では完全独立。将来のマージは検討しない |

---

## Corrections Made

なし — すべてのアサンプションがユーザーによって確認または訂正なく受け入れられた。

---

*Generated: 2026-04-07*
