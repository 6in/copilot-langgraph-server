# Phase 16: Canvas App — AIチャットで HTML アプリを作成・プレビュー・デプロイ - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Phase Boundary

MenuScreen から直接起動できる独立した Canvas アプリ体験を実装する。
AI チャットで HTML アプリを生成・編集・プレビュー・デプロイできる専用画面（CanvasChatApp）を提供する。

### このフェーズで実装すること

1. **MenuScreen に「Canvas」カードを追加** — Gems カードの横に Canvas カードを固定追加
2. **CanvasScreen 新規作成** — Canvas App ハブ画面（Canvas App 一覧 + 新規チャット起動）
3. **CanvasChatApp 新規作成** — 左右分割レイアウト（左: チャット+スレッド、右: CanvasPane 常時表示）
4. **Canvas 専用内部 Gem 登録** — type='canvas' の Gem を内部的に用意し、HTML 生成プロンプトを設定
5. **デプロイ済みアプリ一覧** — CanvasScreen 内にデプロイ済み HTML アプリの一覧を表示
6. **App.tsx ナビゲーション拡張** — canvas / canvaschat スクリーンを追加

### スコープ外（将来検討）

- Canvas Gem（GemsScreen 起動）との統合・マージ — 将来検討しない
- Canvas 専用 Gem を GemsScreen に表示 — 内部 Gem として隠蔽
- バージョン管理・ロールバック
- 生成アプリからの社内 DB アクセス API

</domain>

<decisions>
## Implementation Decisions

### レイアウト構成 (CanvasChatApp)

- **D-01:** 左右分割レイアウト。左: ThreadSidebar + MessageArea（チャット）、右: CanvasPane（Canvas エディタ/プレビュー）
- **D-02:** CanvasPane は最初から常時表示。AI 応答前も右パネルは空の状態で存在する（Gem の Canvas モードとは異なりトグル不要）
- **D-03:** 左右パネルはドラッグでリサイズ可能（GemChatApp.tsx の drag handle パターンを流用）
- **D-04:** GemChatApp.tsx を参照実装として使い、ThreadSidebar + MessageArea + ヘッダーバーを踏襲する

### エントリーポイント (MenuScreen)

- **D-05:** MenuScreen に「Canvas」カードを1枚固定追加。Gems カードの横に配置する
- **D-06:** Canvas カードをクリックすると CanvasScreen（ハブ画面）を表示する
- **D-07:** App.tsx に `currentScreen: 'canvas' | 'canvaschat'` を追加し、GemsScreen パターンに準じたナビゲーションを実装する

### CanvasScreen（ハブ画面）

- **D-08:** CanvasScreen コンポーネントを新規作成（`frontend/src/components/CanvasScreen.tsx`）
- **D-09:** CanvasScreen は 2 つのセクションを持つ:
  1. **デプロイ済みアプリ一覧** — `GET /api/canvas/apps` で取得、deployed=true のものを表示
  2. **新規チャット起動ボタン** — クリックで CanvasChatApp を起動
- **D-10:** 既存 Canvas App をクリックすると、その app_id に関連するスレッドで CanvasChatApp を起動
- **D-11:** Back ボタンで MenuScreen に戻る（`onBack` コールバック）

### システムプロンプト（AI の振る舞い）

- **D-12:** Canvas 専用 Gem（type='canvas'）を内部的に作成する。GemsScreen には表示しない（通常の Gem 一覧から隠蔽）
- **D-13:** システムプロンプト方針: 「HTML のみで返す」形式。AI は ```html ... ``` ブロックで完全な HTML を返すよう指示
- **D-14:** Canvas 専用 Gem の gem_id を useChat に渡すことで、worker 側で HTML 抽出ロジックが発動する（Phase 15 実装済みの CANVAS-03 ロジックを活用）

### Canvas Gem との差別化

- **D-15:** Phase 16 の CanvasChatApp は GemsScreen から完全独立。Canvas 専用 Gem は GemsScreen の Gem 一覧に表示しない
- **D-16:** MenuScreen では「Gems」と「Canvas」を別カードとして並列表示。将来的なマージは Phase 16 では検討しない
- **D-17:** Canvas App のスレッドは `gem_id` = Canvas 専用 Gem の gem_id でフィルタリングすることでチャット履歴を分離

### Claude's Discretion

- Canvas 専用 Gem の name/system_prompt の具体的な文言（HTML 生成に適した内容で実装者が判断）
- CanvasScreen でのデプロイ済みアプリカードのデザイン詳細（既存 FeatureCard スタイルに倣う）
- CanvasChatApp の初期状態（Canvas App がないとき右パネルに表示するプレースホルダー）
- Canvas 専用 Gem の内部登録タイミング（起動時に DB チェック + 存在しなければ自動作成 OR 環境変数/設定で固定 gem_id を管理）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### フロントエンド（主要変更・参照ファイル）
- `frontend/src/App.tsx` — ナビゲーション追加先（currentScreen に canvas/canvaschat を追加、GemsScreen パターンを参照）
- `frontend/src/components/MenuScreen.tsx` — Canvas カード追加先（FeatureCard/Gems カードと同列）
- `frontend/src/components/GemChatApp.tsx` — CanvasChatApp の参照実装（ThreadSidebar + MessageArea + ヘッダーバー + drag handle）
- `frontend/src/components/GemsScreen.tsx` — CanvasScreen の参照実装（ハブ画面パターン）
- `frontend/src/components/CanvasPane.tsx` — Canvas エディタ/プレビュー/デプロイUI（そのまま流用）
- `frontend/src/hooks/useCanvas.ts` — Canvas 状態管理フック（useCanvas — そのまま流用）
- `frontend/src/types.ts` — CanvasAppInfo / GemInfo 型定義
- `frontend/src/api/client.ts` — Canvas API クライアント関数

### バックエンド（参照・活用）
- `app/api/routes/canvas.py` — Canvas Apps CRUD + デプロイ API（実装済み）
- `app/api/routes/gems.py` — Gem CRUD API（Canvas 専用 Gem の内部作成に使用）
- `app/api/models.py` — CanvasAppInfo, GemInfo, CanvasDeployResponse モデル
- `app/jobs/handlers/langgraph_handler.py` — Canvas HTML 抽出ロジック（CANVAS-03、gem_id を渡すと発動）

### Phase 15/15.1 実装参照
- `.planning/phases/15-gem-canvas/15-CONTEXT.md` — Canvas 基盤設計の原点（canvas_apps テーブル、API 設計）
- `.planning/phases/15.1-gem-canvas-gem-ux/15.1-CONTEXT.md` — GemChatApp / GemsScreen パターンの確立

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CanvasPane` (`frontend/src/components/CanvasPane.tsx`) — エディタ/プレビュータブ切替・Save・Deploy ボタン付き。props: `{canvasApp, isSaving, isDeploying, deployUrl, deployError, onSave, onDeploy, onClose}`
- `useCanvas` hook — canvasApp 状態・saveCanvas・deployCanvas を管理。CanvasChatApp でそのまま使える
- `GemChatApp.tsx` — ThreadSidebar + MessageArea + drag handle の完全な実装。SIDEBAR_MIN/MAX 定数込み。CanvasChatApp の直接ベース
- `GemsScreen.tsx` — 一覧・作成・編集・削除・選択の Gem ハブ画面パターン。CanvasScreen の参照実装

### Established Patterns
- `useThreads(undefined, gem.gem_id)` — Gem 単位のスレッド分離パターン（GemChatApp L37）。Canvas 専用 Gem の gem_id でも同様に使える
- `useChat({ gemId: gem.gem_id })` — gem_id を渡すと worker が HTML を抽出して CanvasPane に流す（Phase 15 実装済み）
- Screen 追加パターン: App.tsx の `type Screen = '...' | 'new'` に追加 → MenuScreen に props追加 → App.tsx 内に条件分岐追加
- Canvas 専用 Gem の隠蔽: Gems API の `GET /api/gems` はすでに github_login でフィルタしているが、type フィルタは未実装。GemsScreen 側で type='default' のみ表示するフィルタを追加するか、Canvas 専用 Gem を別 github_login(システム) で管理するかは実装者判断

### Integration Points
- MenuScreen → `onOpenCanvas` コールバック追加（`onOpenGems` / `onOpenDebate` と同パターン）
- App.tsx: `currentScreen` に `'canvas' | 'canvaschat'` を追加、`activeCanvasApp` state
- CanvasScreen で `onStartChat` / `onOpenApp` コールバックを受け取り、App.tsx でナビゲーションを処理
- CanvasChatApp: `useChat` で `onCanvasResponse` コールバックを受け取り、Canvas App 生成時に右パネルを更新

</code_context>

<specifics>
## Specific Ideas

- CanvasPane は最初から常時右側に表示（Gem の Canvas モードと異なる体験: チャット前からエディタが見えている）
- Canvas 専用 Gem は GemsScreen に出さない（内部 Gem として隠蔽）
- デプロイ済みアプリ一覧は CanvasScreen（ハブ画面）に表示

</specifics>

<deferred>
## Deferred Ideas

- Canvas Gem（GemsScreen から起動）と Canvas App のマージ — 将来的に検討しない
- Canvas バージョン管理・ロールバック — スコープ外
- 生成アプリからの社内 DB アクセス API — 将来フェーズ

</deferred>

---

*Phase: 16-canvas-app*
*Context gathered: 2026-04-07*
