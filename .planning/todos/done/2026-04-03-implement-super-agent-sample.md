---
created: 2026-04-03T09:47:29.072Z
title: スーパーエージェントのサンプル実装を実施
area: api
files:
  - docs/pre/phase1_spec.md
---

## Problem

仕様書 `docs/pre/phase1_spec.md` に基づき、オーケストレータ＋サブエージェントの最小構成サンプル実装を行う必要がある。
現在のアプリにはスーパーエージェントチャット機能が存在しない。

実装内容：
- OrchestratorGraph（RouterNode + SubAgent）の実装
- AgentState, SubAgentRegistry, MenuDispatcher の実装
- メニューにスーパーエージェントチャット（super-chat）を追加
- サブエージェント（code-reviewer, sql-analyst）のAGENT.md定義

## Solution

`docs/pre/phase1_spec.md` の仕様に沿って実装する：
1. `agents/`, `menus/`, `src/` ディレクトリ構成を追加
2. `state.py`, `agent.py`, `graph.py`, `dispatcher.py`, `main.py` を実装
3. メニューに "スーパーエージェントチャット" を追加（UI側にも追加）
4. **別ブランチで作業すること**（feature/super-agent-sample 等）
