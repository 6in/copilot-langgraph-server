---
created: 2026-04-16T12:33:29.310Z
title: CodeAct を実装してみる
area: general
files: []
---

## Problem

LangGraph エージェントの推論→実行ループをより柔軟にしたい。現在の ReAct パターン（ToolEnabledSubAgent）はツール呼び出しベースだが、CodeAct パターンでは LLM がコードを直接生成・実行し、その結果を観察して次のアクションを決定する。

## Solution

CodeAct パターンの実装を検討する。参考記事: https://qiita.com/nogataka/items/9924c97a74f63c5452eb

- LLM がPythonコードを生成 → サンドボックス内で実行 → 結果をフィードバック
- 既存の SubAgent / ToolEnabledSubAgent との共存方法を検討
- セキュリティ（サンドボックス、実行制限）の設計が必要
