# Phase 7: React Chat UI - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-02
**Phase:** 07-react-chat-ui-chatscope-vite-bun
**Areas discussed:** Feature scope, Auth handling, Theming & look, Production serving

---

## Feature Scope

| Option | Description | Selected |
|--------|-------------|----------|
| フル機能 | Vanilla JS 版と同等 — 認証フロー、スレッド管理、モデル選択、GitHub ユーザー情報表示、SSE + ポーリングをすべて React で実装 | ✓ |
| チャット機能のみ | 認証済み前提でチャット送受信・スレッド表示のみ。認証フローは Vanilla JS に委ねる | |
| chatscope UI のみ (最小) | chatscope コンポーネントの接続と表示確認だけ。API 統合は次フェーズ | |

**User's choice:** フル機能
**Notes:** —

---

## Auth Handling

| Option | Description | Selected |
|--------|-------------|----------|
| React 内で完結 | Device Flow 認証 UI も React で実装。Vanilla JS 排除で完全独立したアプリになる | ✓ |
| Vanilla JS 側で認証してから遷移 | /:8000 で認証後、React UI (/react) にリダイレクト。JWT cookie は共有できる | |

**User's choice:** React 内で完結
**Notes:** —

---

## Theming & Look

| Option | Description | Selected |
|--------|-------------|----------|
| 既存ダークテーマに合わせる | Vanilla JS 版のダークテーマに近い色やスタイルに chatscope をカスタマイズする | |
| chatscope デフォルトのまま | chatscope のデフォルト CSS をそのまま使う。視覚的な相違は許容 | ✓ |

**User's choice:** chatscope デフォルトのまま
**Notes:** —

---

## Production Serving

| Option | Description | Selected |
|--------|-------------|----------|
| FastAPI StaticFiles (/react) | bun run build の dist/ を FastAPI が /react でマウント。Vanilla JS は / のまま共存 | ✓ |
| dev モードのみ、本番配信は後回し | Phase 7 は Vite 開発サーバー (:5173) のみ。本番 serve 戦略は別フェーズで決定 | |

**User's choice:** FastAPI StaticFiles (/react)
**Notes:** —

---

## Claude's Discretion

- SSE クライアント選択（EventSource vs @microsoft/fetch-event-source）
- Markdown レンダリングライブラリ
- スレッド名表示方法
- エラー表示方法
- frontend/ ディレクトリ構造・コンポーネント設計
- docker-compose 統合要否

## Deferred Ideas

- nginx 振り分け
- Docker Compose frontend サービス
- ストリーミング応答
- モバイル対応
