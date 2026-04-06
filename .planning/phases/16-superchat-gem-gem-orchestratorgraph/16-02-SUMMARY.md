---
phase: 16-superchat-gem-gem-orchestratorgraph
plan: "02"
status: complete
subsystem: api + frontend
tags: [gem, superchat, gem-selector, api-extension]
dependency_graph:
  requires: []
  provides:
    - ChatRequest.gem_ids フィールド (API)
    - useGemSelector フック (フロントエンド)
    - GemSelector コンポーネント (フロントエンド)
  affects:
    - app/api/models.py
    - app/api/routes/chat.py
    - frontend/src/hooks/useChat.ts
    - frontend/src/components/SuperChatApp.tsx
tech_stack:
  added: []
  patterns:
    - AgentSelector と対称的な chip UI パターン（GemSelector）
    - listGems() 既存 API クライアント関数を再利用
key_files:
  created:
    - frontend/src/hooks/useGemSelector.ts
    - frontend/src/components/GemSelector.tsx
  modified:
    - app/api/models.py
    - app/api/routes/chat.py
    - frontend/src/hooks/useChat.ts
    - frontend/src/components/SuperChatApp.tsx
    - frontend/src/types.ts
decisions:
  - "D-10: ChatRequest に gem_ids: list[str] | None = None を独立フィールドとして追加"
  - "D-11: enqueue_job に gem_ids=body.gem_ids を追加"
  - "D-12: gem_id（単数）と gem_ids（複数）を独立フィールドとして共存 — 型安全性保証"
  - "D-13: GemSelector は緑（#28a745）— AgentSelector（青 #0366d6）と視覚的に区別"
  - "D-14: useGemSelector はデフォルト全未選択 — ユーザーが明示的に招待する設計"
  - "D-15: GemSelector を AgentSelector の直後に配置"
  - "D-16: useChat に gemIds?: string[] パラメータ追加 — POST ボディに gem_ids として含める"
  - "D-17: Gem 選択は React state（useGemSelector）でセッション保持 — DB 永続化なし"
  - "Deviation: useGems 命名衝突 — 既存 CRUD フック（useGems.ts）と衝突するため useGemSelector.ts として命名"
  - "Deviation: apiFetch 非エクスポート — 既存の listGems() API クライアント関数を使用"
metrics:
  duration: "~15 minutes"
  completed_at: "2026-04-06T05:57:39Z"
  tasks: 2
  files: 7
---

# Phase 16 Plan 02: API gem_ids フィールド追加と GemSelector フロントエンド実装 Summary

**One-liner:** ChatRequest に `gem_ids` フィールドを追加し、SuperChatApp に緑色チップの GemSelector コンポーネントを統合して Gem 招待経路を確立した。

## What Was Implemented

### Task 1: API 拡張

`app/api/models.py` の `ChatRequest` に `gem_ids: list[str] | None = None` フィールドを追加した（`gem_id` 単数フィールドの直後）。`app/api/routes/chat.py` の `enqueue_job` 呼び出しに `gem_ids=body.gem_ids` を追加し、arq ジョブキューに Gem ID リストを渡す経路を確立した。

既存の `gem_id`（Phase 15、GemChatApp 用、単数、threads テーブルへの永続化）は変更なし。`gem_ids` はジョブキューへの受け渡しのみで DB 永続化は行わない（D-17）。

### Task 2: フロントエンド実装

**`useGemSelector.ts`（新規）:** `GET /api/gems` から Gem 一覧を取得し、マルチ選択状態を管理するフック。デフォルト全未選択（ユーザーが明示的に招待する設計）。0個選択が有効（Gem 招待なし）。

**`GemSelector.tsx`（新規）:** AgentSelector と対称的な chip UI コンポーネント。緑色（#28a745）のチップで AgentSelector（青 #0366d6）と視覚的に区別。Gem が存在しない場合は行を非表示。ラベルは "Gems:"。

**`useChat.ts`（変更）:** `UseChatOptions` に `gemIds?: string[]` を追加。`sendMessage` の POST ボディに `gem_ids` として含める。`useCallback` の依存配列にも追加。

**`SuperChatApp.tsx`（変更）:** `useGemSelector` をインポートして `useAgents()` 直後に呼び出し。`useChat` に `gemIds: selectedGemIds` を渡す。JSX の `<AgentSelector>` 直後に `<GemSelector>` を追加。

**`types.ts`（変更）:** `ChatRequest` インターフェースに `gem_ids?: string[]` を追加。`GemInfo` 型は Phase 15 で既に定義済み。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] useGems 命名衝突**
- **Found during:** Task 2 実装開始時
- **Issue:** プランでは `useGems.ts` として作成するよう指示していたが、同名ファイルが既に存在（Phase 15 の Gem CRUD フック）。上書きすると GemsScreen.tsx が破損する。
- **Fix:** SuperChat 用フックを `useGemSelector.ts` / `useGemSelector()` として命名。SuperChatApp.tsx での import も `useGemSelector` を使用。
- **Files modified:** `frontend/src/hooks/useGemSelector.ts`（新規）

**2. [Rule 3 - Blocking] apiFetch 非エクスポート**
- **Found during:** TypeScript ビルド実行時（`TS2459: 'apiFetch' locally but not exported`）
- **Issue:** プランのコードサンプルでは `apiFetch('/api/gems')` を直接呼び出していたが、`apiFetch` は `client.ts` の内部関数でエクスポートされていない。
- **Fix:** 既存のエクスポート済み関数 `listGems()` を使用（`listGems` は `apiFetch<GemInfo[]>('/api/gems')` のラッパー）。
- **Files modified:** `frontend/src/hooks/useGemSelector.ts`

## Verification Results

**Python 検証:**
```
gem_ids field OK
```
`ChatRequest(message='test', thread_id='t')` → `gem_ids is None` 確認。
`ChatRequest(message='test', thread_id='t', gem_ids=['id1','id2'])` → `gem_ids == ['id1','id2']` 確認。

**TypeScript ビルド:**
```
✓ built in 252ms
```
`tsc -b && vite build` がエラーなしで完了。404 モジュール変換済み。

## Commits

| Hash | Message |
|------|---------|
| `5a4a57d` | feat(16-02): add gem_ids field to ChatRequest and enqueue_job |
| `83bd764` | feat(16-02): add GemSelector frontend component and useGemSelector hook |

## Known Stubs

なし — GemSelector は `GET /api/gems` から実データを取得する。Gem が存在しない場合は行を非表示にする実装済み。

## Threat Flags

計画済みの脅威境界（T-16-04, T-16-05, T-16-06）に対応:
- `POST /api/chat` は既存の JWT 認証 (`get_github_token` dependency) で保護済み
- `GET /api/gems` は `WHERE github_login = %s OR is_public = true` フィルタ済み（既存実装）
- 不正な gem_id は OrchestratorHandler（Plan 01）で DB クエリ時に検証される

## Self-Check: PASSED

- `frontend/src/hooks/useGemSelector.ts` — FOUND
- `frontend/src/components/GemSelector.tsx` — FOUND
- commit `5a4a57d` — FOUND (feat(16-02): add gem_ids field to ChatRequest and enqueue_job)
- commit `83bd764` — FOUND (feat(16-02): add GemSelector frontend component and useGemSelector hook)
