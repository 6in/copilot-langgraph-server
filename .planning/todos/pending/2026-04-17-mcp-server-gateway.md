---
created: 2026-04-17T09:06:52.551Z
title: MCP サーバーゲートウェイ機能 — 別の MCP サーバーのツールを中継
area: api
files:
  - mcp_server/server.py
  - mcp_server/tools/stubs.py
  - app/jobs/worker.py
---

## Problem

現在の MCP サーバー (`mcp_server/`) は自前のツール（ping, web_search_stub 等）のみを提供している。
外部の MCP サーバーが持つツールを、このサーバーを経由してクライアント（worker）に公開する「ゲートウェイ」機能がない。

ユースケース:
- 社内の別チームが運用する MCP サーバーのツールを、本システムのチャットから利用可能にする
- 複数の MCP サーバーを 1 つのエンドポイントに集約し、worker 側の接続先を簡素化する
- ツールの追加・削除をゲートウェイ設定の変更だけで行えるようにする

## Solution

- `mcp_server/` に gateway / proxy 機能を追加
- 設定ファイル（YAML or env）で中継先 MCP サーバーの URL 一覧を定義
- 起動時に中継先からツール一覧を取得し、自サーバーのツールとマージして公開
- リクエスト受信時は該当ツールの中継先へプロキシ
- `fastmcp` の仕組みを活用できるか調査が必要
