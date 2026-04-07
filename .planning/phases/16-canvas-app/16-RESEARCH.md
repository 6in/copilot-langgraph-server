# Phase 16: Canvas App — Research

**Researched:** 2026-04-07
**Domain:** React フロントエンド画面追加 + バックエンド API 拡張（Canvas 専用 Gem 自動登録・デプロイ済みアプリ一覧取得）
**Confidence:** HIGH（既存コードを直接検証）

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** 左右分割レイアウト。左: ThreadSidebar + MessageArea（チャット）、右: CanvasPane（Canvas エディタ/プレビュー）
- **D-02:** CanvasPane は最初から常時表示。AI 応答前も右パネルは空の状態で存在する
- **D-03:** 左右パネルはドラッグでリサイズ可能（GemChatApp.tsx の drag handle パターンを流用）
- **D-04:** GemChatApp.tsx を参照実装として使い、ThreadSidebar + MessageArea + ヘッダーバーを踏襲する
- **D-05:** MenuScreen に「Canvas」カードを1枚固定追加。Gems カードの横に配置する
- **D-06:** Canvas カードをクリックすると CanvasScreen（ハブ画面）を表示する
- **D-07:** App.tsx に `currentScreen: 'canvas' | 'canvaschat'` を追加、GemsScreen パターンに準じたナビゲーション
- **D-08:** CanvasScreen コンポーネントを新規作成（`frontend/src/components/CanvasScreen.tsx`）
- **D-09:** CanvasScreen は 2 つのセクション: デプロイ済みアプリ一覧 + 新規チャット起動ボタン
- **D-10:** 既存 Canvas App をクリックすると、その app_id に関連するスレッドで CanvasChatApp を起動
- **D-11:** Back ボタンで MenuScreen に戻る（`onBack` コールバック）
- **D-12:** Canvas 専用 Gem（type='canvas'）を内部的に作成する。GemsScreen には表示しない
- **D-13:** システムプロンプト方針: 「HTML のみで返す」形式。```html ... ``` ブロックで返す
- **D-14:** Canvas 専用 Gem の gem_id を useChat に渡すことで CANVAS-03 ロジックが発動
- **D-15:** Phase 16 の CanvasChatApp は GemsScreen から完全独立
- **D-16:** MenuScreen では「Gems」と「Canvas」を別カードとして並列表示
- **D-17:** Canvas App のスレッドは gem_id = Canvas 専用 Gem の gem_id でフィルタリング

### Claude's Discretion

- Canvas 専用 Gem の name/system_prompt の具体的な文言
- CanvasScreen でのデプロイ済みアプリカードのデザイン詳細（既存 FeatureCard スタイルに倣う）
- CanvasChatApp の初期状態（Canvas App がないとき右パネルに表示するプレースホルダー）
- Canvas 専用 Gem の内部登録タイミング（起動時に DB チェック + 存在しなければ自動作成 OR 環境変数/設定で固定 gem_id を管理）

### Deferred Ideas (OUT OF SCOPE)

- Canvas Gem（GemsScreen 起動）と Canvas App のマージ
- Canvas バージョン管理・ロールバック
- 生成アプリからの社内 DB アクセス API
- Canvas 専用 Gem を GemsScreen に表示すること

</user_constraints>

---

## Summary

Phase 16 は既存コード（GemChatApp、GemsScreen、CanvasPane、useCanvas）を最大限に流用する「組み合わせ」フェーズである。新規実装より参照実装からのコピー+調整が中心になる。

ただし、**3つの実装ギャップ**が存在することが直接コード検証で判明した。①`GET /api/canvas/apps` に `deployed=true` フィルタが存在しない（CanvasScreen の一覧取得に必要）、②Canvas 専用 Gem の自動作成ロジックが存在しない（lifespan に追加が必要）、③`canvas_apps` テーブルの UNIQUE 制約 `(thread_id, github_login)` がすでに存在し、CanvasChatApp ではこれが正しく機能する前提を確認する必要がある。

また UI-SPEC が指定する drag handle 幅 4px に対して、現行 GemChatApp.tsx は 5px を使用しており、CanvasChatApp 作成時に修正する必要がある（既存コードのコピー時に注意）。

**主要推奨:** GemChatApp.tsx を直接ベースに CanvasChatApp を作成し、CanvasPane を右側に常時レンダリング。API 拡張（deployed フィルタ）と Canvas 専用 Gem 自動登録を先行して実装してからフロントエンドを構築する順序が安全。

---

## Standard Stack

### Core（既存スタック — 新規追加なし）

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React 19 + TypeScript | 19.2 / 5.9 | フロントエンド | プロジェクト標準 [VERIFIED: codebase] |
| @chatscope/chat-ui-kit-react | 2.1 | チャット UI | 既存 ThreadSidebar/MessageArea が使用 [VERIFIED: codebase] |
| FastAPI + psycopg | 0.135.2 / — | バックエンド API | プロジェクト標準 [VERIFIED: codebase] |
| PostgreSQL | — | データ永続化 | canvas_apps テーブル既存 [VERIFIED: codebase] |

### 新規依存ライブラリ

**なし。** このフェーズは既存スタックのみで完結する。

### Installation

```bash
# フロントエンド・バックエンド共に新規パッケージ追加なし
# Docker Compose 再ビルドのみ必要
docker compose build
```

---

## Architecture Patterns

### 推奨プロジェクト構造（新規ファイル）

```
frontend/src/
  components/
    CanvasScreen.tsx      (新規) — デプロイ済みアプリ一覧ハブ
    CanvasChatApp.tsx     (新規) — 左右分割チャット+Canvas
app/api/routes/
  canvas.py              (修正) — GET /api/canvas/apps に deployed フィルタ追加
app/api/
  main.py                (修正) — Canvas 専用 Gem の自動登録 lifespan 追加
frontend/src/
  App.tsx                (修正) — 'canvas' | 'canvaschat' Screen 追加
  components/MenuScreen.tsx  (修正) — Canvas FeatureCard + onOpenCanvas prop 追加
```

### Pattern 1: GemChatApp パターン（CanvasChatApp のベース）

**What:** GemChatApp.tsx の構造をほぼそのままコピーし、右側に CanvasPane を追加する

**Structural copy points:**
- ヘッダーバー（48px、Back ボタン、タイトル）
- ThreadSidebar + drag handle + MessageArea
- `useThreads(undefined, canvasGemId)` — gem_id によるスレッド分離
- `useChat({ gemId: canvasGemId, onCanvasResponse })` — Canvas レスポンス受信

**追加要素:**
- 右側の drag handle（MessageArea と CanvasPane の間）
- `useCanvas()` フック
- CanvasPane 常時レンダリング（`canvasApp` が null のときはプレースホルダー）

```typescript
// Source: GemChatApp.tsx L86-106 (drag handle パターン)
const handleDividerMouseDown = useCallback((e: React.MouseEvent) => {
  e.preventDefault();
  dragStartX.current = e.clientX;
  dragStartWidth.current = canvasPaneWidth;

  const onMouseMove = (ev: MouseEvent) => {
    if (dragStartX.current === null) return;
    const delta = ev.clientX - dragStartX.current;
    // CanvasPane の min を 320px に制約（UI-SPEC exceptions）
    const newWidth = Math.max(320, dragStartWidth.current - delta);
    setCanvasPaneWidth(newWidth);
  };
  // ...window.addEventListener パターン同じ
}, [canvasPaneWidth]);
```

**注意:** GemChatApp.tsx の drag handle は sidebar の右境界（左→右でサイドバー拡大）。CanvasChatApp では MessageArea と CanvasPane の境界（右→左で CanvasPane 拡大）なので delta の符号が反転する。

### Pattern 2: GemsScreen パターン（CanvasScreen のベース）

**What:** GemsScreen.tsx の骨格をベースに、Gem 一覧の代わりに Canvas App カード一覧を表示

**Key structural elements:**
```typescript
// Source: GemsScreen.tsx L259-278
<div style={{
  flex: 1, display: 'flex', flexDirection: 'column',
  alignItems: 'center', padding: '48px 32px',
  background: screenBg, overflowY: 'auto',
}}>
  <div style={{ maxWidth: '640px', width: '100%' }}>
    {/* Back ボタン + h1 */}
    {/* エラー表示 */}
    {/* ローディング: SkeletonCard x3 */}
    {/* 空状態 */}
    {/* Canvas App カード一覧 */}
    {/* + 新しいチャットを開始 ボタン */}
  </div>
</div>
```

### Pattern 3: App.tsx ナビゲーション拡張パターン

**現状の Screen type:**
```typescript
// Source: App.tsx L19
type Screen = 'menu' | 'superchat' | 'gems' | 'gemchat' | 'debate';
```

**追加パターン（gems/gemchat と同じ）:**
```typescript
type Screen = 'menu' | 'superchat' | 'gems' | 'gemchat' | 'debate' | 'canvas' | 'canvaschat';
```

追加の state:
```typescript
const [activeCanvasAppId, setActiveCanvasAppId] = useState<string | null>(null);
const [canvasGemId, setCanvasGemId] = useState<string | null>(null); // 起動時に取得
```

### Pattern 4: Canvas 専用 Gem の自動登録

**What:** lifespan の DB セットアップ末尾に Canvas 専用 Gem（type='canvas'、system ユーザー）を INSERT する。既存なら何もしない。

**システム Gem の隠蔽方法:**
- アプローチ A: `GET /api/gems` は `WHERE github_login = %s OR is_public = true` を返す → 専用 github_login（例: `_canvas_system_`）で登録すれば他ユーザーには表示されない
- アプローチ B: `is_public = false` + 特殊 github_login で登録 → フロントエンドで `gem.type === 'canvas'` でフィルタリング

**推奨: アプローチ A**（コードが最小、バックエンド変更不要、フロントエンドもフィルタ不要）

```python
# Source: app/api/main.py lifespan パターン（gems テーブル作成の直後に追加）
CANVAS_GEM_LOGIN = "_canvas_system_"
await conn.execute(
    """INSERT INTO gems (github_login, name, system_prompt, type, description)
       VALUES (%s, %s, %s, 'canvas', %s)
       ON CONFLICT DO NOTHING""",
    (CANVAS_GEM_LOGIN,
     "Canvas App Generator",
     "あなたはシングルファイル HTML アプリを生成する専門家です。\n"
     "ユーザーのリクエストに対して、必ず完全な HTML を ```html\n...\n``` ブロックで返してください。\n"
     "外部 CDN を使用してよいですが、HTML は必ず1ファイルで完結させてください。",
     "AI チャットで HTML アプリを生成・プレビュー・デプロイします")
)
```

ただし `UNIQUE` 制約が gems テーブルにないため、`ON CONFLICT DO NOTHING` は効かない。gems テーブルを確認:

```sql
-- gems テーブル CREATE 文（app/api/main.py L128-138）
-- UNIQUE 制約なし。ON CONFLICT は機能しない。
-- → SELECT でチェックしてから INSERT、またはスタートアップ時に gem_id を app.state に保存する必要がある
```

**[VERIFIED: app/api/main.py L128-138]** gems テーブルに UNIQUE 制約はない。Canvas Gem の自動登録には `SELECT → INSERT if not exists` パターンが必要。

```python
# 安全な実装例
row = await conn.execute(
    "SELECT gem_id FROM gems WHERE github_login = '_canvas_system_' AND type = 'canvas' LIMIT 1"
)
existing = await row.fetchone()
if not existing:
    row2 = await conn.execute(
        """INSERT INTO gems (github_login, name, system_prompt, type, description)
           VALUES ('_canvas_system_', 'Canvas App Generator', %s, 'canvas', %s)
           RETURNING gem_id""",
        (CANVAS_SYSTEM_PROMPT, CANVAS_DESCRIPTION),
    )
    canvas_gem = await row2.fetchone()
    canvas_gem_id = str(canvas_gem[0])
else:
    canvas_gem_id = str(existing[0])
app.state.canvas_gem_id = canvas_gem_id
```

フロントエンドは `GET /api/canvas/gem-id` エンドポイント or App.tsx 起動時取得で `canvasGemId` を保持する。

**最も単純な方法:** 新しいエンドポイント `GET /api/canvas/gem` を追加して gem_id を返す（1行クエリ）。または `app.state.canvas_gem_id` をフロントエンドに直接公開する `/api/canvas/config` を追加。

### Pattern 5: GET /api/canvas/apps の deployed フィルタ追加

**現状の API:**
- `?thread_id=xxx` → そのスレッドの最新アプリ1件を返す [VERIFIED: canvas.py L86-123]
- `?` (なし) → ユーザーの全アプリ最大20件

**不足機能:** `?deployed=true` フィルタがない。CanvasScreen の「Deployed Apps」一覧に必要。

**追加実装（canvas.py L86-123 の `list_or_get_by_thread` を修正）:**
```python
@router.get("/apps", response_model=list[CanvasAppInfo])
async def list_or_get_by_thread(
    request: Request,
    thread_id: str | None = None,
    deployed: bool | None = None,  # 追加
    payload: dict = Depends(get_jwt_payload),
) -> list[CanvasAppInfo]:
    ...
    else:
        query = """SELECT ... FROM canvas_apps WHERE github_login = %s"""
        params = [github_login]
        if deployed is not None:
            query += " AND deployed = %s"
            params.append(deployed)
        query += " ORDER BY created_at DESC LIMIT 20"
        await cur.execute(query, params)
```

**フロントエンド client.ts への追加:**
```typescript
export const listCanvasApps = (deployed?: boolean) => {
  const params = new URLSearchParams();
  if (deployed !== undefined) params.set('deployed', String(deployed));
  const qs = params.toString();
  return apiFetch<CanvasAppInfo[]>(`${API_BASE}/api/canvas/apps${qs ? `?${qs}` : ''}`);
};
```

### Anti-Patterns to Avoid

- **CanvasPane の `onClose` prop に dismissCanvas を渡さない:** CanvasChatApp では CanvasPane は常時表示。`onClose` は存在するが Phase 16 では閉じる操作がない。ダミー関数を渡すか、CanvasPane に optional props を追加する（最小変更はダミー関数）
- **GemChatApp の drag handle をそのままコピーしない:** delta の符号が異なる（サイドバー用 vs CanvasPane 用）
- **drag handle を 5px でコピーしない:** UI-SPEC は 4px を指定している（GemChatApp.tsx L178 は 5px — 既知の不一致）
- **Canvas 専用 Gem を GemsScreen に表示しない:** `github_login = '_canvas_system_'` で登録すれば GET /api/gems の WHERE 条件で自動除外される

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Canvas HTML エディタ | カスタムエディタコンポーネント | 既存 `CanvasPane` | Phase 15 実装済み、タブ切替・Save・Deploy 完備 |
| Canvas 状態管理 | useState x5 | 既存 `useCanvas()` | save/deploy/error 状態を一括管理 |
| スレッド管理 | カスタム fetch | 既存 `useThreads(undefined, gemId)` | Gem フィルタ付きスレッド一覧取得済み |
| チャット送受信 | カスタム SSE | 既存 `useChat({ gemId, onCanvasResponse })` | Canvas JSON 検出・CanvasPane 連携済み |
| drag handle リサイズ | カスタム drag実装 | GemChatApp.tsx のパターン | window.mousemove/mouseup 解除まで完備 |
| SkeletonCard | カスタムスケルトン | GemsScreen.tsx の SkeletonCard | pulse アニメーション済み |
| Canvas App 一覧取得 | 新規 hook | `getCanvasAppByThread` + 新規 `listCanvasApps` | client.ts 既存関数の流用 |

**Key insight:** このフェーズの "新規実装" のほぼすべては既存コードのコピー＋微修正である。0から書くコードは CanvasScreen.tsx と CanvasChatApp.tsx のシェルのみ。

---

## Common Pitfalls

### Pitfall 1: drag handle の delta 符号が逆
**What goes wrong:** GemChatApp の drag handle は左から右にドラッグするとサイドバーが拡大する（`delta = clientX - startX`、`newWidth = startWidth + delta`）。CanvasChatApp で CanvasPane のリサイズを実装する場合、右から左にドラッグすると CanvasPane が拡大するため delta の符号が逆になる。
**Why it happens:** パターンをそのままコピーすると drag 方向が反転したように見える。
**How to avoid:** CanvasPane の width 計算は `newWidth = Math.max(320, startWidth - delta)` にする。
**Warning signs:** ドラッグして右に動かすと CanvasPane が縮む。

### Pitfall 2: canvas_apps の UNIQUE 制約 (thread_id, github_login)
**What goes wrong:** 同じスレッドで AI に複数回話しかけると、2回目以降の upsert が ON CONFLICT により既存レコードを上書きする。これは意図した動作（CANVAS-03 の upsert 設計）だが、CanvasScreen でアプリが表示されなくなることはない。
**Why it happens:** Phase 15 の設計。1スレッド = 1アプリの仕様。
**How to avoid:** この制約を理解した上で実装する。問題ではなく仕様。

### Pitfall 3: Canvas 専用 Gem が毎回 INSERT される
**What goes wrong:** lifespan が再起動するたびに gems テーブルに Canvas 専用 Gem が追加される（UNIQUE 制約なし）。
**Why it happens:** gems テーブルに UNIQUE 制約なし、`ON CONFLICT DO NOTHING` が効かない。
**How to avoid:** SELECT → INSERT の冪等パターンで実装。`app.state.canvas_gem_id` にセッション間で同じ gem_id が参照されるよう保証する。

### Pitfall 4: CanvasPane の onClose prop
**What goes wrong:** CanvasPane は `onClose` prop を required で受け取る（CanvasPaneProps の定義）。CanvasChatApp では閉じる操作がないため、`() => {}` のダミー関数を渡さなければ TypeScript エラーになる。
**Why it happens:** Phase 15 の CanvasPane は ChatApp からのトグル表示を想定して設計された。
**How to avoid:** `onClose={() => {}}` を渡す。または CanvasPane.tsx の props を `onClose?: () => void` に変更する（後者の方が正しい修正）。

### Pitfall 5: GET /api/canvas/apps の deployed フィルタ不在
**What goes wrong:** `GET /api/canvas/apps` に `?deployed=true` クエリパラメータを渡しても無視される。全アプリ（非デプロイを含む）が返される。
**Why it happens:** canvas.py の `list_or_get_by_thread` は `thread_id` フィルタのみ実装。
**How to avoid:** バックエンド修正（deployed フィルタ追加）を Plan 1 に含める。

### Pitfall 6: Canvas 専用 Gem の gem_id 取得タイミング
**What goes wrong:** `canvasGemId` を App.tsx のマウント時に非同期で取得しようとすると、CanvasChatApp 起動前に gem_id が未定状態になる可能性がある。
**Why it happens:** lifespan での gem_id 確定 → フロントエンドへの公開のタイムラグ。
**How to avoid:** `GET /api/canvas/gem` エンドポイントを追加し、CanvasScreen マウント時に取得する（CanvasChatApp 起動前に必ず確定）。または App.tsx の `handleOpenCanvas` 内で `await fetchCanvasGemId()` してから `setCurrentScreen('canvaschat')` する。

### Pitfall 7: GemChatApp の sidebar collapse width が 40px（UI-SPEC は 32px）
**What goes wrong:** GemChatApp.tsx L167 の `width={sidebarCollapsed ? 40 : sidebarWidth}` を CanvasChatApp にそのままコピーすると UI-SPEC の 32px と不一致になる。
**Why it happens:** UI-SPEC では collapse width を 32px に更新しているが、GemChatApp.tsx はまだ 40px を使っている。
**How to avoid:** CanvasChatApp 実装時は `width={sidebarCollapsed ? 32 : sidebarWidth}` に修正する。

---

## Code Examples

### CanvasChatApp の右パネル構造

```typescript
// Source: GemChatApp.tsx 構造 + CanvasPane 追加パターン
<div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
  <MainContainer style={{ overflow: 'hidden' }}>
    <ThreadSidebar ... />

    {/* サイドバー ↔ チャット drag handle */}
    {!sidebarCollapsed && (
      <div onMouseDown={handleSidebarDividerMouseDown}
        style={{ width: '4px', cursor: 'col-resize', background: 'transparent', flexShrink: 0 }}
        onMouseEnter={(e) => { e.currentTarget.style.background = '#b0c4d8'; }}
        onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
      />
    )}

    {isLoadingMessages ? (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 1 }}>
        <p>Loading messages...</p>
      </div>
    ) : (
      <MessageArea ... />
    )}

    {/* チャット ↔ CanvasPane drag handle */}
    <div onMouseDown={handleCanvasDividerMouseDown}
      style={{ width: '4px', cursor: 'col-resize', background: 'transparent', flexShrink: 0 }}
      onMouseEnter={(e) => { e.currentTarget.style.background = '#b0c4d8'; }}
      onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
    />

    {/* CanvasPane: canvasApp が null のときはプレースホルダー */}
    {canvasApp ? (
      <CanvasPane
        canvasApp={canvasApp}
        isSaving={isSaving}
        isDeploying={isDeploying}
        deployUrl={deployUrl}
        deployError={deployError}
        onSave={saveCanvas}
        onDeploy={deployCanvas}
        onClose={() => {}}  // Pitfall 4: 常時表示のためダミー
      />
    ) : (
      <CanvasPanePlaceholder />
    )}
  </MainContainer>
</div>
```

### CanvasScreen のデプロイ済みアプリカード

```typescript
// Source: GemsScreen.tsx カードパターン準拠
<div style={{
  background: cardBg, border: `1px solid ${cardBorder}`,
  borderRadius: '12px', padding: '24px', marginBottom: '16px',
  cursor: 'pointer', transition: 'box-shadow 0.2s, transform 0.1s',
}}
  onMouseEnter={(e) => {
    e.currentTarget.style.boxShadow = '0 4px 16px rgba(0,0,0,0.18)';
    e.currentTarget.style.transform = 'translateY(-2px)';
  }}
  onMouseLeave={(e) => {
    e.currentTarget.style.boxShadow = 'none';
    e.currentTarget.style.transform = 'none';
  }}
  onClick={() => onOpenApp(app)}
>
  <div style={{ fontSize: '1rem', fontWeight: 600, color: textColor }}>
    {app.name}
  </div>
  <a href={`/apps/${app.app_id}/`} target="_blank" rel="noopener noreferrer"
    style={{ fontSize: '0.875rem', color: '#7c6ff7' }}>
    Open App
  </a>
  <button style={primaryBtnStyle} onClick={(e) => { e.stopPropagation(); onOpenApp(app); }}>
    チャットを開く
  </button>
</div>
```

### Canvas 専用 Gem ID 取得エンドポイント（バックエンド）

```python
# app/api/routes/canvas.py に追加
@router.get("/gem", response_model=dict)
async def get_canvas_gem(request: Request) -> dict:
    """Canvas 専用 Gem の gem_id を返す。認証不要（gem_id は公開情報）"""
    return {"gem_id": str(request.app.state.canvas_gem_id)}
```

---

## Implementation Gap Analysis

CONTEXT.md の決定事項と現行コードを照合した実装ギャップ一覧:

| Gap | 影響 | 対処 | Plan |
|-----|------|------|------|
| `GET /api/canvas/apps` に `?deployed=true` なし | CanvasScreen のデプロイ済み一覧が取得できない | canvas.py に deployed フィルタ追加 | Plan 1 |
| Canvas 専用 Gem の自動登録ロジックなし | CanvasChatApp が gem_id を持てない | lifespan に SELECT→INSERT 追加 | Plan 1 |
| `GET /api/canvas/gem` エンドポイントなし | フロントエンドが canvas gem_id を知る手段がない | 1行エンドポイント追加 | Plan 1 |
| `CanvasPane.onClose` が required | CanvasChatApp でコンパイルエラー | props を optional に変更 OR ダミー渡し | Plan 2 |
| drag handle 5px（GemChatApp）vs 4px（UI-SPEC） | UI-SPEC 不適合 | CanvasChatApp 実装時に 4px で作成 | Plan 2 |
| sidebar collapse width 40px（GemChatApp）vs 32px（UI-SPEC） | UI-SPEC 不適合 | CanvasChatApp 実装時に 32px で作成 | Plan 2 |

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| ChatApp で CanvasPane をトグル表示 | CanvasChatApp で CanvasPane を常時表示（Phase 16 の独自体験） | D-02 によりチャット前からエディタが見える |
| GemsScreen で Gem を選んでチャット起動 | CanvasScreen → CanvasChatApp（独立エントリーポイント） | D-15/D-16 による明確な分離 |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Canvas 専用 Gem は `github_login = '_canvas_system_'` で登録することで GemsScreen から自動除外できる | Architecture Patterns (Pattern 4) | `GET /api/gems` の WHERE 句 `github_login = %s OR is_public = true` を確認済み。`_canvas_system_` は JWT ユーザー名と一致しないため除外される [VERIFIED: gems.py L83-91] |
| A2 | `UNIQUE (thread_id, github_login)` 制約により1スレッド=1アプリの upsert が機能する | Common Pitfalls 2 | canvas_apps の CREATE TABLE 文で確認済み [VERIFIED: main.py L173] |
| A3 | CanvasChatApp で新規チャットを開始すると `useThreads` 経由で gem_id 付きスレッドが作成され、CANVAS-03 の HTML 抽出ロジックが発動する | Implementation Gap Analysis | useChat に gemId を渡す → langgraph_handler.py の `_get_gem_info` が gem_type='canvas' を検出 → extract_html → upsert [VERIFIED: langgraph_handler.py L89-113] |

**A1〜A3 はすべてコードで検証済み。ユーザー確認不要。**

---

## Open Questions

1. **Canvas 専用 Gem ID をフロントエンドに渡す方法の最終決定**
   - 選択肢 A: `GET /api/canvas/gem` 専用エンドポイント（推奨 — シンプル、1行）
   - 選択肢 B: `GET /api/canvas/config` でまとめて返す
   - 選択肢 C: Canvas 専用 Gem の gem_id をビルド時環境変数で固定（柔軟性なし）
   - 推奨: 選択肢 A（Canvas API の文脈で自然、既存パターンに合致）

2. **D-10「既存 Canvas App をクリックするとその app_id に関連するスレッドで CanvasChatApp を起動」の実現方法**
   - `canvas_apps.thread_id` から `useThreads` の `activeThreadId` を復元する
   - CanvasChatApp が `initialThreadId` prop を受け取り、useThreads に渡す形が最もクリーン
   - `canvas_apps` には `thread_id` が保存されている [VERIFIED: canvas.py L48]

---

## Environment Availability

Step 2.6: SKIPPED — このフェーズは既存 Docker Compose スタック上の コード/設定変更のみ。新規外部依存なし。

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest（バックエンド）/ TypeScript tsc（フロントエンド） |
| Config file | pyproject.toml [tool.pytest.ini_options] / tsconfig.json |
| Quick run command | `docker compose run --rm api pytest tests/ -x -q` |
| Full suite command | `docker compose run --rm api pytest tests/ -q` |

### Phase Requirements → Test Map

このフェーズは REQUIREMENTS.md に明示的な REQ-ID が割り当てられていない（TBD）。フェーズ内の検証ポイントを機能単位で定義する:

| Feature | Behavior | Test Type | Automated Command | Notes |
|---------|----------|-----------|-------------------|-------|
| GET /api/canvas/apps?deployed=true | deployed=true の場合のみデプロイ済みアプリを返す | unit | `pytest tests/test_canvas.py -k "deployed" -x` | Wave 0 で作成 |
| GET /api/canvas/gem | canvas_gem_id を返す | unit | `pytest tests/test_canvas.py -k "canvas_gem" -x` | Wave 0 で作成 |
| Canvas 専用 Gem の自動登録 | 起動後 gems テーブルに type='canvas' レコードが存在する | integration | `pytest tests/test_canvas.py -k "auto_register" -x` | Wave 0 で作成 |
| CanvasChatApp レンダリング | TypeScript コンパイルエラーなし | smoke | `docker compose run --rm frontend tsc --noEmit` | 既存コマンド |

### Wave 0 Gaps

- [ ] `tests/test_canvas.py` に deployed フィルタテスト追加 — 現在 deployed フィルタのテストなし
- [ ] `tests/test_canvas.py` に Canvas 専用 Gem 自動登録テスト追加

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes（既存） | JWT HS256 httpOnly cookie — 変更なし |
| V3 Session Management | no | スレッドは gem_id フィルタで分離済み |
| V4 Access Control | yes（既存） | github_login による所有権チェック — canvas.py の 404 返却パターン |
| V5 Input Validation | yes | Canvas Gem システムプロンプトは DB 経由、ユーザー入力は既存パターン |
| V6 Cryptography | no | 新規暗号化要件なし |

### 既存脅威モデルの継承

Phase 15 で確立されたセキュリティ制約は変更なく継承する:

| Pattern | 制約 | 確認 |
|---------|------|------|
| iframe sandbox | `sandbox="allow-scripts allow-forms"` — allow-same-origin なし | CanvasPane.tsx L304 [VERIFIED] |
| Canvas app_id | UUID（DB生成）— ユーザー入力ではない | path traversal 不可 [VERIFIED: canvas.py L205] |
| 所有権チェック | 404 返却（存在リーク防止） | canvas.py L150, L193 [VERIFIED] |
| Canvas 専用 Gem | `_canvas_system_` login — JWT ユーザーとは別 | 他ユーザーが編集・削除不可 |

**新規セキュリティ考慮:** `GET /api/canvas/gem` は gem_id を返すが、これは UUIDであり秘密情報ではない。認証なしで公開しても問題ない（任意ユーザーが canvas_gem_id を知っても、そのGemを使ってチャットするだけで悪用不可）。ただし一貫性のため JWT 保護を付けることを推奨。

---

## Sources

### Primary (HIGH confidence — コードベース直接検証)

- `frontend/src/components/GemChatApp.tsx` — CanvasChatApp の参照実装（drag handle、ThreadSidebar、useThreads/useChat パターン）[VERIFIED]
- `frontend/src/components/GemsScreen.tsx` — CanvasScreen の参照実装（カード一覧、SkeletonCard、inline スタイルパターン）[VERIFIED]
- `frontend/src/components/CanvasPane.tsx` — Canvas エディタ/プレビュー（再利用確認）[VERIFIED]
- `frontend/src/hooks/useCanvas.ts` — Canvas 状態管理（再利用確認）[VERIFIED]
- `frontend/src/hooks/useChat.ts` — Canvas レスポンス検出ロジック（onCanvasResponse, parseJobResult）[VERIFIED]
- `app/api/routes/canvas.py` — Canvas API（deployed フィルタ不在を確認）[VERIFIED]
- `app/api/routes/gems.py` — Gem API（GET /api/gems の WHERE 句確認）[VERIFIED]
- `app/jobs/handlers/langgraph_handler.py` — CANVAS-03 HTML 抽出ロジック（gem_type='canvas' 検出）[VERIFIED]
- `app/api/main.py` — lifespan（Canvas 専用 Gem 自動登録なし確認、gems テーブル UNIQUE 制約なし確認）[VERIFIED]
- `.planning/phases/16-canvas-app/16-CONTEXT.md` — ユーザー決定事項 [VERIFIED]
- `.planning/phases/16-canvas-app/16-UI-SPEC.md` — UI 設計コントラクト [VERIFIED]

### Secondary (MEDIUM confidence)

なし（このフェーズは全てコードベース内の情報で完結する）

---

## Metadata

**Confidence breakdown:**

- Standard Stack: HIGH — 既存スタックのみ、新規依存なし
- Architecture: HIGH — 実装ギャップをコード検証で特定済み
- Pitfalls: HIGH — コードと UI-SPEC の差分を直接確認

**Research date:** 2026-04-07
**Valid until:** 実装開始まで（コードベース変更がない限り）
