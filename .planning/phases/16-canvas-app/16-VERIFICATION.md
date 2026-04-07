---
phase: 16-canvas-app
verified: 2026-04-07T01:00:00Z
status: human_needed
score: 10/10 must-haves verified
re_verification: false
human_verification:
  - test: "MenuScreen に Canvas カードが表示されブラウザ上でクリック可能なことを確認する"
    expected: "🎨 Canvas カードが Gems カードの隣に表示され、クリックすると CanvasScreen に遷移する"
    why_human: "DOM レンダリング・クリックイベントの実際の動作はブラウザ実行なしには確認できない"
  - test: "CanvasChatApp の左右分割レイアウトと drag handle のリサイズ動作を確認する"
    expected: "右パネルにプレースホルダーが表示され、drag handle を操作するとパネルサイズが変わる"
    why_human: "インタラクティブな drag 動作はコードスキャンで検証できない"
  - test: "AI に HTML 生成を依頼し右パネルに CanvasPane が表示されることを確認する"
    expected: "チャットで HTML を要求すると右パネルのプレースホルダーが CanvasPane に置き換わる"
    why_human: "実際の AI 推論と SSE ストリーミングによる動的 UI 更新はブラウザ実行が必要"
---

# Phase 16: Canvas App 検証レポート

**Phase Goal:** MenuScreen から直接起動できる独立した Canvas アプリ体験を実装する。CanvasScreen（デプロイ済みアプリ一覧ハブ）と CanvasChatApp（左右分割チャット+Canvas エディタ）を新規作成し、Canvas 専用 Gem を自動登録して AI による HTML 生成・プレビュー・デプロイの完全フローを提供する。
**Verified:** 2026-04-07T01:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | MenuScreen に Canvas カードが表示される | ✓ VERIFIED | `MenuScreen.tsx` L123-130: `icon="🎨" title="Canvas"` の FeatureCard、`onOpenCanvas` prop が型安全に定義されている |
| 2 | Canvas カード → CanvasScreen の遷移が実装されている | ✓ VERIFIED | `App.tsx` L66,102,152-164: `handleOpenCanvas` ハンドラ、`onOpenCanvas={handleOpenCanvas}` prop 渡し、`currentScreen === 'canvas'` の CanvasScreen レンダリングブロック |
| 3 | App.tsx が 'canvas' と 'canvaschat' の Screen 状態を持つ | ✓ VERIFIED | `App.tsx` L22: `type Screen = 'menu' \| 'superchat' \| 'gems' \| 'gemchat' \| 'debate' \| 'canvas' \| 'canvaschat'` |
| 4 | CanvasScreen が deployed=true のアプリのみ取得する | ✓ VERIFIED | `CanvasScreen.tsx` L119: `listCanvasApps(true)` 呼び出し、バックエンド `canvas.py` L131-133: `deployed` フィルタ付き動的クエリ |
| 5 | CanvasChatApp が左右分割レイアウトで実装されている | ✓ VERIFIED | `CanvasChatApp.tsx` L185-281: ThreadSidebar + MessageArea + CanvasPane の 3 パネル構成、4px drag handle 2 本 |
| 6 | CanvasPane が canvasApp=null のときプレースホルダーを表示する | ✓ VERIFIED | `CanvasChatApp.tsx` L244-280: `{canvasApp ? <CanvasPane .../> : <div>アプリがここに表示されます</div>}` |
| 7 | drag handle でリサイズできる（D-03） | ✓ VERIFIED | `CanvasChatApp.tsx` L128-148: `handleCanvasDividerMouseDown`（delta 反転）、L206/233: `width: '4px'` 2 箇所 |
| 8 | GET /api/canvas/gem エンドポイントが存在する | ✓ VERIFIED | `canvas.py` L86-95: `@router.get("/gem", response_model=dict)` JWT 保護付き |
| 9 | Canvas 専用 Gem 自動登録が main.py lifespan に実装されている | ✓ VERIFIED | `main.py` L193-209: `SELECT → INSERT 冪等パターン` + `app.state.canvas_gem_id = canvas_gem_id` |
| 10 | canvasGemId が CanvasChatApp に正しく渡される | ✓ VERIFIED | `App.tsx` L74-76: `getCanvasGemId()` で取得・キャッシュ、L167/176: `canvasGemId &&` null safety + `canvasGemId={canvasGemId}` prop 渡し |

**Score:** 10/10 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/api/routes/canvas.py` | deployed フィルタ + GET /api/canvas/gem | ✓ VERIFIED | L86-95: gem エンドポイント、L102/131-133: deployed フィルタ |
| `app/api/main.py` | Canvas Gem 自動登録 + canvas_gem_id | ✓ VERIFIED | L193-209: SELECT→INSERT 冪等 + app.state.canvas_gem_id |
| `frontend/src/components/CanvasChatApp.tsx` | 左右分割チャット+Canvas | ✓ VERIFIED | handleCanvasDividerMouseDown、useThreads(undefined, canvasGemId)、onCanvasResponse |
| `frontend/src/components/CanvasScreen.tsx` | Canvas App ハブ画面 | ✓ VERIFIED | listCanvasApps(true)、まだデプロイ済みアプリがありません、role="alert"、aria-busy="true" |
| `frontend/src/api/client.ts` | listCanvasApps + getCanvasGemId | ✓ VERIFIED | L178-187: 両関数 export 済み |
| `frontend/src/App.tsx` | canvas/canvaschat Screen + canvasGemId 取得 | ✓ VERIFIED | Screen 型、handleOpenCanvas/Chat ハンドラ、CanvasScreen/CanvasChatApp レンダリング |
| `frontend/src/components/MenuScreen.tsx` | Canvas FeatureCard + onOpenCanvas prop | ✓ VERIFIED | L14: prop 定義、L121-130: FeatureCard 追加 |
| `tests/test_canvas_gem.py` | Canvas Gem 登録テスト 4 件 | ✓ VERIFIED | test_canvas_gem_auto_register, test_canvas_gem_idempotent, test_get_canvas_gem_endpoint, test_get_canvas_gem_requires_auth |
| `tests/test_canvas_api.py` | deployed フィルタテスト 3 件 | ✓ VERIFIED | test_list_canvas_apps_deployed_filter, test_list_canvas_apps_no_filter, test_list_canvas_apps_requires_auth |
| `.planning/phases/16-canvas-app/16-UAT.md` | Phase 16 UAT チェックリスト | ✓ VERIFIED | 全 8 E2E 項目が auto-advance 承認済みとして記録 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| MenuScreen Canvas カード | App.tsx handleOpenCanvas | onOpenCanvas コールバック | ✓ WIRED | MenuScreen.tsx L130: `onClick={onOpenCanvas}`、App.tsx L102: `onOpenCanvas={handleOpenCanvas}` |
| App.tsx handleOpenCanvasChat | CanvasChatApp canvasGemId prop | getCanvasGemId() で取得した gem_id | ✓ WIRED | App.tsx L74-82: async 取得・キャッシュ、L176: `canvasGemId={canvasGemId}` |
| CanvasChatApp | useThreads(undefined, canvasGemId) | gem_id によるスレッド分離（D-17） | ✓ WIRED | CanvasChatApp.tsx L48: `useThreads(undefined, canvasGemId)` |
| CanvasChatApp | useChat({ gemId: canvasGemId, onCanvasResponse }) | Canvas HTML 抽出ロジック（D-14） | ✓ WIRED | CanvasChatApp.tsx L85-93: `gemId: canvasGemId, onCanvasResponse: setCanvasApp` |
| CanvasScreen | GET /api/canvas/apps?deployed=true | listCanvasApps(true) | ✓ WIRED | CanvasScreen.tsx L119: `listCanvasApps(true)`、client.ts L178-184: URLSearchParams 構築 |
| main.py lifespan | gems テーブル | SELECT → INSERT 冪等パターン | ✓ WIRED | main.py L193-209: `_canvas_system_` チェック→INSERT RETURNING |
| GET /api/canvas/gem | app.state.canvas_gem_id | request.app.state | ✓ WIRED | canvas.py L95: `return {"gem_id": str(request.app.state.canvas_gem_id)}` |

### Anti-Patterns Found

anti-pattern スキャン対象ファイル（Phase 16 で作成・修正されたもの）:

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| CanvasChatApp.tsx | `onClose={() => {}}` | ℹ️ Info | CanvasPane 常時表示のための意図的なダミー（D-02 実装として設計済み、Pitfall 4 対応） |

その他の TODO/FIXME/placeholder/return null パターンは検出されなかった。空の `onClose` は stub ではなく設計による意図的な実装（PLAN に記載あり）。

### Human Verification Required

#### 1. MenuScreen Canvas カード表示確認

**Test:** ブラウザで http://localhost:5173 または http://localhost:8000/app を開き、MenuScreen に「🎨 Canvas」カードが表示されることを確認する
**Expected:** Gems カードと隣接した位置に Canvas カードが表示され、クリックすると CanvasScreen に遷移する
**Why human:** DOM レンダリング・クリックイベントの実際の動作はコードスキャンでは確認できない

#### 2. CanvasChatApp レイアウト + drag handle 動作確認

**Test:** CanvasScreen から「+ 新しいチャットを開始」をクリックして CanvasChatApp を開き、左右パネルの drag handle をドラッグしてリサイズを確認する
**Expected:** 右パネルに「🎨 アプリがここに表示されます」プレースホルダーが表示され、drag handle 操作でパネルサイズが変化する
**Why human:** インタラクティブな drag 動作（mousemove/mouseup イベント）はブラウザ実行が必要

#### 3. AI HTML 生成フロー確認

**Test:** CanvasChatApp で「シンプルなカウンターアプリを作ってください」と送信し、右パネルの変化を確認する
**Expected:** AI が HTML を返すと右パネルのプレースホルダーが CanvasPane（Preview/Editor タブ付き）に置き換わる
**Why human:** 実際の AI 推論・SSE ストリーミング・onCanvasResponse コールバック起動の動作確認はブラウザ実行が必要

### Gaps Summary

ギャップなし。自動検証可能なすべての must-haves は VERIFIED。Human verification 3 項目（視覚・インタラクション・AI 連携動作）が残る。

---

_Verified: 2026-04-07T01:00:00Z_
_Verifier: Claude (gsd-verifier)_
