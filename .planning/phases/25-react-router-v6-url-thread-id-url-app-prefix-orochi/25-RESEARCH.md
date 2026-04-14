# Phase 25: React Router v6 URL ルーティング実装 - Research

**Researched:** 2026-04-14
**Domain:** React Router v7 (declarative mode) + Vite SPA + URL-based routing
**Confidence:** HIGH

---

## Summary

Phase 25 は、現在 `useState` ベースの画面切り替えで実装されている React SPA に React Router を導入し、`/{APP_PREFIX}/{app-type}/{thread_id}` 形式の URL 構造を確立するフェーズ。スレッド共有リンク、ブラウザの戻る/進む、URL ブックマークが動作するようになる。

**重要な発見:** React Router の「v6」という Phase 名は適切だが、npm の `latest` タグは v7.14.0 に移行している。v7 は declarative モード（BrowserRouter + Routes + Route）では v6 との後方互換を維持しており、`react-router-dom` から `react-router` への移行が主な変更点となる。`BrowserRouter` の `basename` プロップに `import.meta.env.BASE_URL`（Vite が `VITE_APP_BASE` を元に生成）を渡すことで `/orochi` プレフィックス対応が実現できる。

既存の `useThreads` フック、`ThreadSidebar`、各 ChatApp コンポーネントへの影響は限定的で、`activeThreadId` の状態管理を URL パラメータ経由に置き換える点が主な変更となる。

**Primary recommendation:** React Router v7（declarative モード）を `react-router` として導入し、`BrowserRouter basename={import.meta.env.BASE_URL}` + `Routes/Route` でアプリ画面とスレッドを URL にマッピングする。

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `react-router` | 7.14.0 | SPA ルーティング (BrowserRouter, Routes, Route, useParams, useNavigate, useLocation) | react-router-dom を統合した公式パッケージ。declarative モードは RR v6 API と後方互換 |

[VERIFIED: npm registry — `npm view react-router version` → 7.14.0 が latest]

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| （追加不要） | — | — | react-router 1パッケージで全機能をカバー |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `react-router` v7 | `react-router` v6 (npm tag: `version-6` = 6.30.3) | v6 でも動作するが、新規導入なら v7 が推奨。v7 は v6 と API 互換性あり |
| `BrowserRouter` | `HashRouter` | HashRouter は `#/chat/abc123` 形式。nginx strip が不要だが URL が醜い。本プロジェクトには不適合 |
| `BrowserRouter` | `createBrowserRouter` + `RouterProvider` (Data mode) | Data mode はサーバー側 loader/action 前提。この SPA には過剰 |

**Installation:**
```bash
cd frontend && bun add react-router
```

**Version verification:**
```bash
npm view react-router version
# → 7.14.0 (2026-04-14 時点) [VERIFIED]
```

---

## Architecture Patterns

### URL 構造設計

```
/{APP_PREFIX}/{app-type}/{thread_id}
```

| 画面 | URL パターン | 例 |
|------|------------|-----|
| メニュー | /{prefix}/ | /orochi/ |
| チャット（スレッドなし） | /{prefix}/chat | /orochi/chat |
| チャット（スレッド指定） | /{prefix}/chat/:threadId | /orochi/chat/abc-123 |
| SuperChat | /{prefix}/superchat/:appSlug/:threadId? | /orochi/superchat/my-app/abc-123 |
| Gems 一覧 | /{prefix}/gems | /orochi/gems |
| Gem チャット | /{prefix}/gemchat/:gemId/:threadId? | /orochi/gemchat/gem-xyz/abc-123 |
| Canvas 一覧 | /{prefix}/canvas | /orochi/canvas |
| Canvas チャット | /{prefix}/canvaschat/:threadId? | /orochi/canvaschat/abc-123 |
| DebateChat | /{prefix}/debate/:threadId? | /orochi/debate/abc-123 |

### APP_PREFIX (basename) の扱い

**VITE_APP_BASE と BrowserRouter basename の関係:**

- `.env` では `VITE_APP_BASE=/orochi` と設定（トレイリングスラッシュなし）
- Vite の `base` 設定は `vite.config.ts` で `process.env.VITE_APP_BASE ?? '/'` → `/orochi`
- Vite は `import.meta.env.BASE_URL` を `{base}` の値として公開する（末尾スラッシュ付き → `/orochi/`）
- BrowserRouter の `basename` は末尾スラッシュなしを期待する → `.replace(/\/$/, '')` で除去

```typescript
// main.tsx または App.tsx
import { BrowserRouter } from "react-router";

const basename = (import.meta.env.BASE_URL ?? '/').replace(/\/$/, '');
// VITE_APP_BASE=/orochi → BASE_URL="/orochi/" → basename="/orochi"
// VITE_APP_BASE=未設定  → BASE_URL="/"      → basename=""

<BrowserRouter basename={basename}>
  <App />
</BrowserRouter>
```

[CITED: Vite docs — import.meta.env.BASE_URL は vite.config の base 値と一致する]
[VERIFIED: npm registry + WebFetch reactrouter.com/start/library/installation]

### Route 定義パターン

```typescript
// App.tsx の Routes 構造
import { Routes, Route, Navigate } from "react-router";

<Routes>
  {/* メニュー */}
  <Route index element={<MenuScreen ... />} />

  {/* チャット */}
  <Route path="chat" element={<ChatApp selectedModel={selectedModel} />} />
  <Route path="chat/:threadId" element={<ChatApp selectedModel={selectedModel} />} />

  {/* SuperChat — appSlug はアプリ定義から取得 */}
  <Route path="superchat/:appSlug" element={<SuperChatWrapper selectedModel={selectedModel} />} />
  <Route path="superchat/:appSlug/:threadId" element={<SuperChatWrapper selectedModel={selectedModel} />} />

  {/* Gems */}
  <Route path="gems" element={<GemsScreen ... />} />
  <Route path="gemchat/:gemId" element={<GemChatWrapper ... />} />
  <Route path="gemchat/:gemId/:threadId" element={<GemChatWrapper ... />} />

  {/* Canvas */}
  <Route path="canvas" element={<CanvasScreen ... />} />
  <Route path="canvaschat" element={<CanvasChatWrapper ... />} />
  <Route path="canvaschat/:threadId" element={<CanvasChatWrapper ... />} />

  {/* Debate */}
  <Route path="debate" element={<DebateChatApp selectedModel={selectedModel} />} />
  <Route path="debate/:threadId" element={<DebateChatApp selectedModel={selectedModel} />} />
</Routes>
```

### useParams + useNavigate によるスレッド同期

**現在の状態管理（`useState` ベース）:**
```typescript
// useThreads.ts
const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
```

**移行後（URL パラメータベース）:**
```typescript
// ChatApp.tsx または useThreads 内
import { useParams, useNavigate } from "react-router";

const { threadId } = useParams<{ threadId?: string }>();
const navigate = useNavigate();

// スレッド切り替え時に URL を更新
const handleSelectThread = (tid: string) => {
  navigate(`../chat/${tid}`, { replace: false });
};

// 新規スレッド作成後に URL へ反映
const handleNewChat = async () => {
  const tid = await createNewThread();
  navigate(`../chat/${tid}`, { replace: true }); // replace でブラウザ履歴を汚染しない
};
```

### Link コンポーネントによる共有リンク生成

```typescript
import { Link } from "react-router";

// スレッド共有リンク — basename 込みで自動生成される
<Link to={`/chat/${thread.thread_id}`}>
  スレッドを開く
</Link>

// ブラウザアドレスバーの URL をコピー
const shareUrl = window.location.href; // /orochi/chat/abc-123
```

### 推奨プロジェクト構造（変更ファイル）

```
frontend/src/
├── main.tsx           ← BrowserRouter でラップ（要変更）
├── App.tsx            ← useState routing → Routes/Route に置換（大幅変更）
├── components/
│   ├── ChatApp.tsx           ← useParams で threadId 取得（変更）
│   ├── SuperChatApp.tsx      ← useParams で appSlug + threadId（変更）
│   ├── GemChatApp.tsx        ← useParams で gemId + threadId（変更）
│   ├── CanvasChatApp.tsx     ← useParams で threadId（変更）
│   ├── DebateChatApp.tsx     ← useParams で threadId（変更）
│   └── ThreadSidebar.tsx     ← onSelectThread が navigate を呼ぶ（軽微）
└── hooks/
    └── useThreads.ts         ← activeThreadId を URL から初期化（変更）
```

### Anti-Patterns to Avoid

- **`HashRouter` の使用:** nginx がプレフィックス strip する構成と相性が悪く、`#` 記号が URL に残る
- **`basename` に末尾スラッシュを含める:** `BrowserRouter basename="/orochi/"` は二重スラッシュ問題を起こす。`.replace(/\/$/, '')` で必ず除去
- **`navigate(-1)` を Back ボタンの代替として無条件使用:** history stack が空の場合にアプリ外に脱出する。`navigate('/menu', { replace: true })` 等の安全な代替を用意
- **thread_id を URL と state の両方で管理:** 二重管理は競合の原因。URL が single source of truth

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| URL → コンポーネントのマッピング | 独自 `if currentScreen === 'chat'` 条件分岐 | `Routes/Route` | history API のエッジケース（ポップステート等）を包括対応 |
| URL パラメータの取得 | `location.pathname.split('/')` で手動パース | `useParams` | エンコーディング、Optional パラメータ、ネスト対応 |
| プログラム遷移 | `window.history.pushState()` 直接呼び出し | `useNavigate` | React state との同期保証 |
| basename を手動で全 URL に付加 | `${APP_PREFIX}/chat/${threadId}` を全箇所に書く | BrowserRouter `basename` + 相対 `to` | basename 変更時の全箇所修正不要 |

**Key insight:** ブラウザ History API の popstate イベント処理、ScrollRestoration、basename の自動付加は手書きでは確実に漏れが生じる。React Router に委譲すること。

---

## Runtime State Inventory

> このフェーズはリファクタリングだが、URL スキーマ変更によるランタイム影響を確認する

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | ブックマーク/共有リンク（既存ユーザーが保存した URL）は `?screen=chat` 等の形式ではなく現在は存在しない（URL ルーティングなし） | なし — 既存リンクは `/orochi/` にフォールバックするだけ |
| Live service config | nginx は現在 `/orochi/` をプロキシ転送。SPA の HTML5 History URL（例: `/orochi/chat/abc`）を nginx が 404 返却する可能性がある | nginx に `try_files` または `fallback` 設定が必要（後述） |
| OS-registered state | なし | なし |
| Secrets/env vars | `VITE_APP_BASE=/orochi` — コード変更のみ、env var は変更不要 | なし |
| Build artifacts | `frontend/dist/` の再ビルドが必要 | `bun run build` で自動解決 |

**nginx fallback の必要性:**
SPA で HTML5 History API を使う場合、`/orochi/chat/abc-123` への直接アクセスや再読み込み時に nginx が静的ファイルを探して 404 を返す。対策:
```nginx
location /orochi/ {
  try_files $uri $uri/ /orochi/index.html;
}
```
ただし開発環境（Vite dev server）は自動的に SPA フォールバックを提供するため、この問題は production nginx のみ該当する。

---

## Common Pitfalls

### Pitfall 1: `import.meta.env.BASE_URL` の末尾スラッシュ
**What goes wrong:** Vite は `BASE_URL` を末尾スラッシュ付きで提供する（例: `/orochi/`）。これを BrowserRouter の `basename` にそのまま渡すと二重スラッシュ URL（`/orochi//chat`）が生成される。
**Why it happens:** BrowserRouter は basename を path segments に付加する際にスラッシュを自動挿入する。
**How to avoid:** `basename={(import.meta.env.BASE_URL ?? '/').replace(/\/$/, '')}`
**Warning signs:** URL バーに `/orochi//chat` が現れる

### Pitfall 2: nginx が SPA の deep URL を 404 返却
**What goes wrong:** `/orochi/chat/abc-123` に直接アクセスすると nginx が `index.html` を返さずに 404 を返す。
**Why it happens:** nginx はデフォルトでファイルシステムのパスを探す。`/orochi/chat/abc-123` というファイルは存在しない。
**How to avoid:** nginx に `try_files $uri $uri/ /orochi/index.html;` を追加する（`docs/nginx.md` の更新が必要）
**Warning signs:** ブラウザリフレッシュや共有リンクのアクセスで 404 になる（開発環境は問題なし）

### Pitfall 3: 認証前の URL アクセス
**What goes wrong:** 未ログイン状態で `/orochi/chat/abc-123` にアクセスすると、ログイン後のリダイレクト先が失われる。
**Why it happens:** 現在の `App.tsx` は `isAuthenticated` チェックで `AuthPanel` を表示するが、URL のコンテキストを保持していない。
**How to avoid:** ログイン後に元の URL（`useLocation` で取得）にリダイレクトする。`location.state.from` パターンを活用。
**Warning signs:** ログイン後に常にメニュー画面に飛ぶ

### Pitfall 4: SuperChat の appSlug と AppDefinition の解決
**What goes wrong:** `/orochi/superchat/my-app` にアクセスしたとき、`appSlug` は URL から取れるが `AppDefinition`（name、agents[]）は API から取得が必要。
**Why it happens:** `SuperChatApp` は `appId`、`appName`、`appAgents` を props として受け取る設計になっている。
**How to avoid:** SuperChat ルートに Wrapper コンポーネントを作成し、`useParams` で `appSlug` を取得後に `getApps()` で AppDefinition を解決してから `SuperChatApp` に渡す。
**Warning signs:** SuperChat 画面で agents が空になる、appName が表示されない

### Pitfall 5: useThreads の `activeThreadId` と URL の競合
**What goes wrong:** `useThreads` が内部で `useState` で `activeThreadId` を管理しており、URL の `:threadId` パラメータと二つの source of truth が存在する。
**Why it happens:** フックが URL を知らない。
**How to avoid:** `useThreads` に `initialThreadId?: string` を渡すか、呼び出し側（各 ChatApp）で `useParams` の値を使って `switchThread` を呼ぶ `useEffect` を追加する。URL が single source of truth。
**Warning signs:** URLと実際に表示されるスレッドが異なる

---

## Code Examples

### main.tsx — BrowserRouter でラップ

```typescript
// Source: reactrouter.com/start/library/installation [CITED]
import { BrowserRouter } from "react-router";

const basename = (import.meta.env.BASE_URL ?? '/').replace(/\/$/, '');

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter basename={basename}>
      <App />
    </BrowserRouter>
  </StrictMode>
);
```

### App.tsx — Routes + Route でスクリーンをマッピング

```typescript
// Source: reactrouter.com/start/library/routing [CITED]
import { Routes, Route } from "react-router";

// 既存の useState-based routing を置換
<Routes>
  <Route index element={
    <MenuScreen onNavigate={...} onOpenGems={...} onOpenDebate={...} onOpenCanvas={...} />
  } />
  <Route path="chat" element={<ChatApp selectedModel={selectedModel} />} />
  <Route path="chat/:threadId" element={<ChatApp selectedModel={selectedModel} />} />
  <Route path="gems" element={<GemsScreen onSelectGem={...} onBack={...} />} />
  {/* ... etc */}
</Routes>
```

### ChatApp.tsx — useParams で threadId を取得

```typescript
// Source: reactrouter.com/api/hooks/useParams [CITED]
import { useParams, useNavigate } from "react-router";

export function ChatApp({ selectedModel }: ChatAppProps) {
  const { threadId: urlThreadId } = useParams<{ threadId?: string }>();
  const navigate = useNavigate();

  const { threads, activeThreadId, messages, switchThread, createNewThread, ... } = useThreads('chat');

  // URL の threadId が変わったら useThreads と同期
  useEffect(() => {
    if (urlThreadId && urlThreadId !== activeThreadId) {
      switchThread(urlThreadId);
    }
  }, [urlThreadId]);

  const handleSelectThread = (tid: string) => {
    navigate(`/chat/${tid}`); // basename が自動付加される
  };

  const handleNewChat = async () => {
    const tid = await createNewThread();
    navigate(`/chat/${tid}`, { replace: true });
  };
  // ...
}
```

### ThreadSidebar — onSelectThread を URL ナビゲーションに接続

```typescript
// ThreadSidebar への変更は最小限 — props の onSelectThread を navigate に繋げるだけ
// ThreadSidebar 自体は変更不要（onSelectThread: (threadId: string) => void のまま）
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `react-router-dom` (v5) | `react-router` (v7,統合パッケージ) | v7.0.0 (2024年11月) | import パスの変更のみ |
| `useHistory` | `useNavigate` | v6.0.0 (2021年) | 既に v6 API で解決済み |
| `json()` / `defer()` | raw object return | v7.0.0 | Data mode のみ関係。Declarative mode には影響なし |
| `<Switch>` | `<Routes>` | v6.0.0 | 既に v6 で解決済み |

**Deprecated/outdated:**
- `react-router-dom` パッケージ: 引き続き動作するが、v7 では `react-router` に統合。新規インストールは `react-router` のみ

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | nginx の production 設定に `try_files` が追加可能（プロジェクトがnginx設定を管理している） | Runtime State Inventory | nginx を管理していない場合、SPA deep link が本番環境で動作しない。ただし開発環境は問題なし |
| A2 | `canvasGemId` は URL パラメータではなく API から取得するため、CanvasChatApp ルートには gemId は不要 | Architecture Patterns | 将来 canvasGemId を URL に含める設計変更が必要になる可能性あり |
| A3 | DebateChatApp は `selectedModel` のみ受け取り、`activeApp` 概念を持たないため `/debate/:threadId?` で十分 | URL 構造設計 | DebateChat に複数の「アプリ」が加わった場合は URL 構造の見直しが必要 |

---

## Open Questions

1. **CanvasChatApp の canvasGemId**
   - What we know: `canvasGemId` は API `GET /api/canvas/gem` から取得し、`App.tsx` の state に保持している
   - What's unclear: CanvasChatApp への直接 URL アクセス時（`/orochi/canvaschat/abc-123`）に canvasGemId をどのタイミングで取得するか
   - Recommendation: CanvasChatApp 内部で mount 時に API を呼び出すよう移動する。現在の App.tsx での管理をやめる

2. **SuperChat の appSlug 解決**
   - What we know: `AppDefinition` は `GET /api/apps` で取得できる。`appSlug` は `AppDefinition.slug` に対応
   - What's unclear: アプリ一覧を Router レベルで事前ロードするか、各コンポーネントで個別ロードするか
   - Recommendation: `SuperChatWrapper` コンポーネントを追加し、`useParams` の `appSlug` から `getApps()` を呼んで解決する（過剰なグローバル化を避ける）

3. **ログイン後リダイレクト**
   - What we know: 現在は認証後に常にメニュー表示
   - What's unclear: Phase スコープに含めるか
   - Recommendation: ログイン前の URL を `location.state.from` に保存し、認証後にリダイレクトするパターンを実装する（スレッド共有リンクの UX のため重要）

---

## Environment Availability

Step 2.6: SKIPPED（このフェーズはフロントエンドコード変更のみ。外部ツール依存なし。bun/npm は既に Docker 環境に存在）

---

## Validation Architecture

> nyquist_validation: 設定ファイルで確認できないため enabled として扱う

### Test Framework

| Property | Value |
|----------|-------|
| Framework | なし（フロントエンドに jest/vitest なし。TypeScript ビルドチェックのみ） |
| Config file | なし |
| Quick run command | `cd frontend && bun run build` (TypeScript 型チェック + ビルド) |
| Full suite command | `docker compose up --build frontend` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| URL-01 | `BrowserRouter` が `/orochi` を basename として認識する | manual + build | `bun run build` (型チェック) | ❌ Wave 0 |
| URL-02 | `/orochi/chat/abc-123` にアクセスするとスレッド `abc-123` が表示される | manual (browser) | ブラウザで URL 直接入力 | — |
| URL-03 | スレッドを選択すると URL バーが更新される | manual (browser) | ブラウザで動作確認 | — |
| URL-04 | ブラウザの戻る/進む ボタンで画面・スレッドが切り替わる | manual (browser) | ブラウザで動作確認 | — |
| URL-05 | `/orochi/chat` → `/orochi/chat/abc-123` の URL をコピーして別タブで開ける | manual (browser) | ブラウザで動作確認 | — |

**注:** フロントエンドに自動テストスイートが存在しない。主な検証は TypeScript ビルド成功 + ブラウザ手動確認。

### Sampling Rate

- **Per task commit:** `cd frontend && bun run build`
- **Per wave merge:** `docker compose up --build` → ブラウザ手動確認
- **Phase gate:** 全 URL パターン手動確認 + TypeScript エラーなし

### Wave 0 Gaps

- [ ] `frontend/src/components/__tests__/` — フォルダが存在しない（このフェーズのスコープ外）
- TypeScript ビルドが通ることを各変更後に確認する

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | 既存 JWT 認証を維持 |
| V3 Session Management | no | 変更なし |
| V4 Access Control | no | 変更なし |
| V5 Input Validation | yes | URL パラメータ（threadId）はバックエンドで検証済み。フロントは encodeURIComponent を使用 |
| V6 Cryptography | no | 変更なし |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| URL パラメータ不正値（非存在 thread_id）| Tampering | API エラーを catch して空メッセージ表示にフォールバック（既存 useThreads の try-catch 継続） |
| 他ユーザーの thread_id を URL で直接指定 | Elevation of Privilege | バックエンドの JWT ユーザーフィルタが防止（既存の `WHERE github_login = $user` ガード） |

---

## Project Constraints (from CLAUDE.md)

- **応答言語:** すべての応答・コメント・ドキュメントは日本語
- **Tech Stack:** React 19 + TypeScript + Vite + Bun（フロントエンド）
- **Primary startup:** `docker compose up` — 直接 `bun run dev` は使わない
- **開発時アクセス URL:** `http://localhost:5173/orochi/`（VITE_APP_BASE=/orochi）
- **nginx strip パターン:** nginx が `/orochi` を strip してから FastAPI に転送。FastAPI のルートは `/api/...` のまま
- **API パス:** `client.ts` の `API_BASE` は `import.meta.env.VITE_APP_BASE` を使用済み。React Router 導入後も変更不要
- **GSD Workflow:** 編集前に `/gsd:execute-phase` または `/gsd:quick` で開始すること

---

## Sources

### Primary (HIGH confidence)
- [reactrouter.com/start/library/installation](https://reactrouter.com/start/library/installation) — BrowserRouter declarative mode インストール手順
- [reactrouter.com/start/library/routing](https://reactrouter.com/start/library/routing) — Routes/Route/useParams/useNavigate API
- [reactrouter.com/api/hooks/useNavigate](https://reactrouter.com/api/hooks/useNavigate) — useNavigate オプション（replace, state など）
- [reactrouter.com/upgrading/v6](https://reactrouter.com/upgrading/v6) — v6→v7 マイグレーション（後方互換性確認）
- npm registry — `react-router@7.14.0` latest 確認

### Secondary (MEDIUM confidence)
- [WebSearch] React Router v7 BrowserRouter basename import.meta.env.BASE_URL パターン
- [WebSearch] nginx try_files SPA フォールバック設定

### Tertiary (LOW confidence)
- なし

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — npm registry で v7.14.0 を直接確認、公式ドキュメントで API を検証
- Architecture: HIGH — 既存コードの全ファイルを読み込み、影響箇所を特定済み
- Pitfalls: MEDIUM — Vite BASE_URL トレイリングスラッシュ問題は WebSearch で複数ソース確認。nginx fallback は一般的な SPA 知識

**Research date:** 2026-04-14
**Valid until:** 2026-05-14（React Router v7 は活発開発中だが declarative mode API は安定）
