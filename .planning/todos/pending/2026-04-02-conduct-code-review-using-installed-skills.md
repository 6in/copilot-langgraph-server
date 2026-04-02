---
created: 2026-04-02T07:05:54.734Z
title: インストールされているスキルを活用してコードレビューを実施する
area: general
files: []
---

## Problem

プロジェクトにはバックエンド（Python / FastAPI / LangGraph）とフロントエンド（React 19 + TypeScript + Vite）の両方が存在するが、コードレビューを体系的に実施していない。
以下のスキルがグローバルにインストール済みで、活用できる状態にある:

- `python-expert-best-practices-code-review` — Python コードレビュー・ベストプラクティス
- `typescript-react-reviewer` — React / TypeScript レビュー
- `langgraph` — LangGraph 設計パターン・Anti-pattern 検出
- `fastapi-python` / `fastapi-async-patterns` — FastAPI パターン

## Solution

1. 各スキルを活用したコードレビュープランを作成する（対象ファイル・観点を整理）
2. バックエンド（`app/` 配下）を `python-expert-best-practices-code-review` + `langgraph` スキルでレビュー
3. フロントエンド（`frontend/src/` 配下）を `typescript-react-reviewer` スキルでレビュー
4. 指摘事項をまとめ、優先度をつけて todo または phase として登録する
