---
created: 2026-04-06T02:58:44.970Z
title: Gem の公開共有機能を追加する（is_public フラグ + Shared Gems セクション）
area: api
files:
  - app/api/models.py
  - app/api/routes/gems.py
  - app/api/main.py
  - frontend/src/types.ts
  - frontend/src/components/GemsScreen.tsx
---

## Problem

現在 Gem はオーナー（github_login）にのみ紐付いており、他ユーザーから参照できない。
社内 200 名規模での運用を想定すると、FAQ Bot・コードレビュー Bot など
共通ペルソナを全ユーザーが使えるようにしたい。

## Solution

アプローチ C: オーナーが Gem をグローバルに公開できるフラグを追加し、
公開 Gem は GemsScreen に「Shared Gems」セクションとして分けて表示する。

- バックエンド:
  - `gems` テーブルに `is_public: bool DEFAULT false` カラム追加（ALTER TABLE IF NOT EXISTS）
  - `GemCreate` / `GemUpdate` / `GemInfo` に `is_public` フィールド追加
  - `list_gems` API: `WHERE github_login = %s OR is_public = true` に変更
  - 他ユーザーの public Gem は読み取り専用（編集・削除不可）— `github_login` チェックで弾く
  - `update_gem` / `delete_gem`: 引き続き `WHERE gem_id = %s AND github_login = %s` で所有者のみ変更可

- フロントエンド:
  - `GemInfo` 型に `is_public: boolean` と `is_owner: boolean`（またはオーナー判定）を追加
  - GemsScreen を「My Gems」と「Shared Gems」の2セクションに分ける
  - My Gems: 編集・削除・Chat ボタン表示
  - Shared Gems: Chat ボタンのみ（編集・削除ボタンを非表示）
  - 作成・編集フォームに「公開する」トグルを追加
