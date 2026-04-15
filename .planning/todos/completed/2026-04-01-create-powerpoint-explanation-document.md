---
created: 2026-04-01T08:45:37.319Z
title: 今回の仕組みの説明資料をPowerPointで作成する
area: docs
files: []
---

## Problem

Copilot LangGraph Chat の仕組み（アーキテクチャ・認証フロー・非同期ジョブ設計など）を他者に説明するための資料がない。口頭説明だけでは伝わりにくいため、視覚的なスライド資料が必要。

## Solution

PowerPoint（.pptx）形式でアーキテクチャ説明資料を作成する。想定する内容:

- プロジェクト概要（何を作っているか・なぜ Copilot SDK を使うか）
- 全体アーキテクチャ図（FastAPI / LangGraph / Copilot SDK / Redis / PostgreSQL）
- 認証フロー（GitHub Device Flow）
- 非同期ジョブ処理フロー（POST → job_id → Worker → SSE/Polling）
- LangGraph グラフ構造と Checkpointer の役割
- 今後の拡張計画（マルチユーザー・Slack Bot 等）

python-pptx ライブラリで生成するか、Marp/Slidev 等の Markdown → スライド変換ツールを検討。
