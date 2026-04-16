---
created: 2026-04-15T14:20:00.000Z
title: README.md をリライト — 最新情報と実行方法を整える
area: docs
files:
  - README.md
---

## Problem

現在の `README.md` は 68 行程度で、プロジェクトが Chat / SuperChat / Gems / Canvas / DebateChat の 5 アプリ構成に拡張された現状や、Docker Compose 駆動・MCP サーバー・LangGraph Checkpointer・Device Flow 認証などの現状アーキテクチャを反映しきれていない。新規メンバーが READMEだけで「どう起動し、どう使うか」を把握しづらい。

## Solution

CLAUDE.md と `docs/slides/architecture.pptx` の内容を参考にして README.md をリライトする。最低限カバーするセクション:

1. **概要** — 何を作っているか / Copilot SDK を使う理由 / 想定ユーザー規模
2. **アプリ一覧** — Chat / SuperChat / Gems / Canvas / DebateChat の違いと画面イメージ
3. **アーキテクチャ概要** — FastAPI + arq worker + LangGraph + MCP + PostgreSQL + Redis の図（`docs/slides/architecture.pptx` からの抜粋でもよい）
4. **必要な前提** — Docker / Docker Compose / Copilot サブスクリプション / GitHub アカウント
5. **セットアップ** — `.env` に必要な変数、`docker compose up` の手順、初回の Device Flow ログイン
6. **開発時のアクセス URL** — `http://localhost:5173/orochi/` と nginx プレフィックスの説明
7. **開発者向け補足** — `uv` での venv、`bun` でのフロント、hook のインストール (`scripts/install-hooks.sh`)
8. **ADR と pattern カタログ** — `docs/adr/INDEX.md` と `.planning/patterns.md` へのリンク
9. **関連資料** — スライド (`docs/slides/architecture.pptx`)、CLAUDE.md

注意:

- 日本語（プロジェクトの既定言語）で書く
- スクショ or 簡易 Mermaid 図を入れる
- 動作確認コマンドは実際に叩いて正しいか検証してから掲載
- 本体の依存関係やポート番号が変わっていないか CLAUDE.md・docker-compose.yml と突き合わせる
