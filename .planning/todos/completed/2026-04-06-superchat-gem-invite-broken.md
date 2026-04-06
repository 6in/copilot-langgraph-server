---
created: 2026-04-06T14:17:45.555Z
title: SuperChat で Gem を招待できないバグを修正する
area: ui
files:
  - frontend/src/components/ChatApp.tsx
---

## Problem

SuperChat において、Gem（エージェント）を会話に招待する操作が機能しなくなっている。
招待ボタンを押しても反応がない、またはエラーが発生して Gem が追加されない状態。

## Solution

SuperChat の Gem 招待フロー（フロントエンドのイベントハンドラ → API 呼び出し → バックエンド処理）を調査し、どのレイヤーで失敗しているかを特定して修正する。
ブラウザの DevTools コンソールおよびネットワークタブでエラーを確認するところから始める。
