---
created: 2026-05-13T14:50:00Z
title: Canvas Editor に「現在 HTML vs デプロイ済 HTML」の Diff タブを追加
area: ui
files:
  - frontend/src/components/CanvasPane.tsx
  - frontend/src/api/client.ts
  - app/api/routes/canvas.py
  - app/api/models.py
---

## Problem

現状、CanvasChat の Editor が表示する HTML は **DB の `canvas_apps.html`** (最新の保存内容)。一方、デプロイ先 `/apps/{app_id}/index.html` は **deploy 時にコピーされた静的ファイル**で、deploy 後にエディタで編集→保存しても自動更新されない。

結果として:

- ユーザーが「保存はしたが deploy していない変更」を持っていることに気付きにくい
- 「いまホストされているサイトの HTML」と「エディタの HTML」がずれているのに UI 上の signal がない
- 「何を変えたから再デプロイすべきか」を確認できない

## Solution

**Option A (推奨): `canvas_apps.deployed_html` カラムを追加してスキーマで snapshot を保持**

DB が single source of truth という設計方針に合致 (今回のシステム全体パターン)。

### バックエンド変更

1. **schema migration**: `canvas_apps` テーブルに `deployed_html TEXT NULL` を追加 (未 deploy なら null)
2. **deploy handler** (`app/api/routes/canvas.py:224` 付近の `deploy_app`):
   - 既存処理: `html` → `./static/apps/{app_id}/index.html` 書き出し
   - 追加: `UPDATE canvas_apps SET deployed_html = html, deployed = TRUE, deployed_at = NOW() WHERE app_id = %s`
3. **CanvasAppInfo モデル** (`app/api/models.py`): `deployed_html: str | None = None` フィールド追加
4. **GET handlers** (`get_app` / `list_or_get_by_thread`): SELECT に `deployed_html` を含める

### フロントエンド変更

1. **`CanvasAppInfo` 型** (`frontend/src/types.ts`): `deployed_html?: string | null` 追加
2. **`CanvasPane.tsx`**:
   - 現在 `'editor' | 'preview'` の `TabId` に `'diff'` を追加
   - Monaco の `DiffEditor` (`@monaco-editor/react` から import) で `original={canvasApp.deployed_html ?? ''}` vs `modified={htmlContent}` を表示
   - `deployed_html === null` (未 deploy) のときは Diff タブ無効化 + 「未デプロイ」表示
   - Editor / Preview / Diff の 3 タブ表示

### UI 案

```
[Editor] [Preview] [Diff ⚠]
                       ↑ 差分があれば badge を出す
```

`Diff ⚠` の `⚠` バッジは `canvasApp.deployed_html != null && canvasApp.deployed_html !== htmlContent` のときだけ表示。

## Alternatives Considered

### Option B: 静的ファイル `/apps/{app_id}/index.html` を直接 fetch して比較

- ✅ schema 変更不要、即実装可能
- ❌ ファイルが削除された場合 (`/apps/` クリーンアップ等) に diff 不能
- ❌ `hosted_apps.py` 経由のアクセス権チェックが絡みそう
- ❌ DB を single source とする方針に反する

**却下理由**: DB が single source of truth 設計に合致しない。ファイルシステム状態に依存するのは脆い。

## Out of Scope (defer)

- 「再 deploy ボタン」を Diff タブから直接押せるようにする UX 強化 (まずは Diff 表示までで段階分割)
- deploy 履歴 (複数バージョン) 表示 — `deployed_html` は最新 1 件のみ保持。履歴が欲しい場合は別テーブル `canvas_app_deployments` を追加する必要あり
- Worker 経由で AI が再生成した場合の deployed_html との diff (同じ仕組みで自然に動くはず、追加実装不要)

## Related

- `app/api/routes/canvas.py` の `_row_to_canvas_app()` も `deployed_html` を含める必要あり
- 既存 todo `2026-04-23-fix-askme-button-regression...` (Phase 39 で解決済) と同様の「フロント単体の機能追加」レベル — 工数推定 1-2 plan
- Phase 39 Code Review WR-01 (CanvasPane dark mode 漏れ) と一緒に修正してもよい
