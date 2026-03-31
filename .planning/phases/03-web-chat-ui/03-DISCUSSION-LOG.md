# Phase 3: Web + Chat UI - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.

**Date:** 2026-04-01
**Phase:** 03-web-chat-ui

---

## Areas Discussed

User selected all 4 gray areas: Auth flow UX, レイアウト構造, モデル選択 UI, ローディング表示.

---

## Auth flow UX

| Question | Options Presented | User Selected |
|----------|-------------------|---------------|
| GitHub URL はどう開く？ | 自動で指定タブ開き (Recommended) / リンク表示のみ | リンク表示のみ |
| コード表示のコピーボタンは？ | Copy ボタンから表示 (Recommended) / コード表示のみ | Copy ボタンから表示 |
| 認証完了の検知は？ | ポーリング（自動検知）(Recommended) / 手動リロード | ポーリング（自動検知） |
| AUTH-03: Re-authenticate ボタンはどこに出す？ | バナー表示 (Recommended) / ヘッダーの認証ステータス変更 / モーダル | ヘッダーの認証ステータス変更 |

---

## レイアウト構造

| Question | Options Presented | User Selected |
|----------|-------------------|---------------|
| サイドバーは有り？ | なし（シンプル単一画面）(Recommended) / あり（履歴サイドバー） | あり（履歴サイドバー） |
| ヘッダーはどうする？ | 最小限のヘッダー (Recommended) / ヘッダーにコントロールまとめ | 最小限のヘッダー |
| メッセージバブルのスタイルは？ | 左右で区別 (Recommended) / ラベル文字のみ | 左右で区別 |
| 履歴サイドバーの v1 趄め込み内容は？ | New Chat ボタンのみ / スレッド履歴一覧も v1 に含める | スレッド履歴一覧も v1 に含める |

**Note:** SESS-01/02（スレッド履歴永続化・一覧表示）を v1 Phase 3 に前倒しすることを決定。AsyncSqliteSaver が既にインフラとして揃っているため。

---

## モデル選択 UI

| Question | Options Presented | User Selected |
|----------|-------------------|---------------|
| モデル選択は UI からできるようにする？ | UI にドロップダウンを置く (Recommended) / config ファイルのみ | UI にドロップダウンを置く |
| モデルリストはどう管理する？ | ハードコード (Recommended) / API から取得 | ハードコード |

---

## ローディング表示

| Question | Options Presented | User Selected |
|----------|-------------------|---------------|
| AI の応答待ち中のフィードバックは？ | 打鍵アニメ（チャット内に）(Recommended) / スピナー（入力欄内）/ プログレスバー | 打鍵アニメ（チャット内に） |
