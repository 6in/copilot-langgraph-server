---
phase: 39-ui-polish
reviewed: 2026-05-13T15:00:00Z
depth: standard
files_reviewed: 31
files_reviewed_list:
  - app/jobs/job_store.py
  - docs/adr/0053-mermaid-source-default-rationale.md
  - docs/adr/INDEX.md
  - frontend/src/components/AttachmentButton.tsx
  - frontend/src/components/CanvasChatApp.tsx
  - frontend/src/components/ChatApp.tsx
  - frontend/src/components/DebateChatApp.tsx
  - frontend/src/components/GemChatApp.tsx
  - frontend/src/components/MermaidBlock.tsx
  - frontend/src/components/SuperChatApp.tsx
  - frontend/src/contexts/ThemeContext.ts
  - frontend/src/hooks/useThreads.ts
  - frontend/src/theme.css
  - scripts/generate_adr_index.py
  - tests/conftest.py
  - tests/test_api_auth.py
  - tests/test_api_chat.py
  - tests/test_api_me.py
  - tests/test_api_models_route.py
  - tests/test_apps_route.py
  - tests/test_canvas_api.py
  - tests/test_debate_handler.py
  - tests/test_generate_mcp_artifacts.py
  - tests/test_graph.py
  - tests/test_job_store.py
  - tests/test_jwt_auth.py
  - tests/test_mcp_server.py
  - tests/test_rpc_integration.py
  - tests/test_sse.py
  - tests/test_tool_catalog_js.py
  - tests/test_tool_enabled_subagent.py
  - tests/test_tool_registry.py
  - tests/test_worker.py
findings:
  critical: 0
  warning: 7
  info: 8
  total: 15
status: issues_found
---

# Phase 39: Code Review Report

**Reviewed:** 2026-05-13T15:00:00Z
**Depth:** standard
**Files Reviewed:** 31
**Status:** issues_found

## Summary

Phase 39 (UI polish) のスコープは UIFIX-01〜UIFIX-04 — Mermaid View デフォルトの恒久化、`theme.css` の incoming bubble width 担保、`JobStore` の dead in-memory queue 経路の整理、テスト fixture の JWT cookie bake-in と psycopg cursor mock の Pattern B 統一。アプリ側のロジック改変は最小限で、ほとんどが整理・ドキュメント化と test infra 整備。

レビューの結果 **BLOCKER は 0 件**。ただし以下の **WARNING 7 件** と **INFO 8 件** を検出した。主な懸念点は次の 3 つに集中している:

1. **CanvasChatApp の placeholder 表示・drag handle hover 色が dark mode に追従していない** — Phase 39 で `useCurrentTheme` を導入したのに hard-coded `#ffffff` / `#d1dbe3` / `#666666` がそのまま残っており、dark mode で目立つ白い領域が出る (WR-01)。GemChatApp / CanvasChatApp ヘッダーの `borderBottom: '1px solid #d1dbe3'` も同じ問題 (WR-02)。
2. **DebateConfigPanel の `isSubmitting` flag が一度 `true` に立った後 reset されない** — `onStart()` が同期的で、`handleStart` が `setConfig(c)` を呼ぶことで親が DebateChatPanel にアンマウントするためテストでは表面化しないが、`onStart` が失敗 / cancel する経路が将来追加された瞬間に永久 disable バグになる (WR-03)。
3. **`JobStore.push_turn` の関数内 `import json as _json` が dead** — module 先頭で既に `import json` 済みなのに、関数内で別名 import している。可読性低下のみだが Phase 39 で明示的に `notify()` を整理した文脈で見落とされた残骸 (IN-01)。

全体として「Phase 39 で意図した変更は SUMMARY と一致しており、観察ベース回避策の恒久化と test infra 整備という polish phase の趣旨に沿った」が、**`docs/adr/INDEX.md` の集計表記には致命的でない不整合がある**（WR-04）ことと、**theme.css の data-theme=dark 適用が `[data-theme="dark"]` selector に依存しているため inline style で書いた色は dark mode で override されない**ことに対する集合的なケアが弱い。

## Warnings

### WR-01: CanvasChatApp の "アプリがここに表示されます" placeholder が dark mode に追従しない

**File:** `frontend/src/components/CanvasChatApp.tsx:346-368`
**Issue:**
`useCurrentTheme()` を取得して `cardBg` / `textColor` を分岐させているにも関わらず、CanvasPane プレースホルダの最外 `<div>` で `background: '#ffffff'` / `borderLeft: '1px solid #d1dbe3'` / `color: '#666666'` を直接書いている。`canvasApp === null` 時にこの白い領域が dark mode の `#1e1e2e` 背景の上に乗るため、ダークテーマで右側が真っ白な矩形になる。Phase 39 のスコープに「dark mode polish」が含まれるかは明示されていないが、`cardBg` / `textColor` を既に取得済みである以上、placeholder にも適用すべき分岐漏れ。
**Fix:**
```tsx
<div
  style={{
    minWidth: `${CANVAS_PANE_MIN}px`,
    width: `${canvasPaneWidth}px`,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'column',
    gap: '8px',
    background: cardBg,                             // was '#ffffff'
    borderLeft: `1px solid ${isDark ? '#3a3a52' : '#d1dbe3'}`,  // was hardcoded
    color: isDark ? '#9090a8' : '#666666',          // was '#666666'
    textAlign: 'center',
    padding: '24px',
    flexShrink: 0,
  }}
>
  <div style={{ fontSize: '2rem' }}>🎨</div>
  <div style={{ fontSize: '1rem', fontWeight: 600 }}>アプリがここに表示されます</div>
  <div style={{ fontSize: '0.875rem', color: isDark ? '#9090a8' : '#666666', lineHeight: 1.5 }}>
    チャットで HTML アプリを生成してください
  </div>
</div>
```

### WR-02: GemChatApp / CanvasChatApp ヘッダーの `borderBottom` が dark mode 非対応

**File:** `frontend/src/components/CanvasChatApp.tsx:243`, `frontend/src/components/GemChatApp.tsx:132`
**Issue:**
両コンポーネントとも `useCurrentTheme()` を呼んで `cardBg` / `textColor` を分岐させているが、ヘッダー row の `borderBottom: '1px solid #d1dbe3'` は直書きされており、dark mode で `#2a2a3e` (cardBg) の下に明るいライトグレーの境界線が出てしまう。`isDark ? '#3a3a52' : '#d1dbe3'` で揃えるべき。
**Fix:**
```tsx
// CanvasChatApp.tsx:243 / GemChatApp.tsx:132
borderBottom: `1px solid ${isDark ? '#3a3a52' : '#d1dbe3'}`,
```

### WR-03: DebateConfigPanel.handleStart の `isSubmitting` が永続的に true になり得る

**File:** `frontend/src/components/DebateChatApp.tsx:376, 391-403`
**Issue:**
`handleStart()` は `setIsSubmitting(true)` を呼んだあと **`onStart(config)` を同期的に呼ぶだけ** で reset を行わない。現在の `DebateChatApp.handleStart` は `setConfig(c)` を呼ぶため親再レンダリングで `DebateConfigPanel` が unmount されるため副作用が表面化しないが、これは強い結合に依存している。将来 `onStart` を非同期化したり、検証エラーで cancel する経路が追加された瞬間に「開始ボタンが永久 disabled」というデグレが入る。さらに「開始中...」ラベルとボタン色が変わるのみで実際には子コンポーネントに dispatch 完了済みのため、UI を見たユーザーが二重クリックを防げるのは「親 unmount に依存」という暗黙仕様。
**Fix:**
`onStart` の責務（成功時親へ通知 / 失敗時残留）を明示的に契約化し、`finally` で reset するか、もしくは `isSubmitting` をローカルではなく親の `config !== null` で判定する設計に変更する。
```tsx
const handleStart = async () => {
  if (selectedIds.length < 2) {
    setValidationError('参加者を2名以上選択してください');
    return;
  }
  setIsSubmitting(true);
  try {
    // ... existing logic ...
    onStart({ pattern, participants, gemIds, gemNames, maxTurns });
  } finally {
    setIsSubmitting(false);  // 親 unmount に依存しない
  }
};
```

### WR-04: docs/adr/INDEX.md の "Total" 集計が ADR 実数と矛盾

**File:** `docs/adr/INDEX.md:3`, `scripts/generate_adr_index.py:69-71`
**Issue:**
`INDEX.md:3` は「**Total:** 50 件（欠番 3 件: 0015, 0016, 0017）」と書いているが、ADR 番号 0001-0053 のうち欠番 3 件を除くと **50 件で正しい**（0001-0053 = 53 個、-3 欠番 = 50）。しかし `scripts/generate_adr_index.py:71` の集計は `len(parsed)` を使っており、**`docs/adr/` 配下の実 ADR ファイル数** を数えている。`parse_adr` で TITLE_RE にマッチしないファイルは silently skip されるため、もし将来 ADR ファイルのタイトル書式が崩れた場合 (`# ADR 0054: ...` ではなく `# 0054 - ...` 等) `Total` が静かにずれる。欠番リスト `.planning/adr-categories.yaml` の `missing` 配列は手動メンテで、ADR 実数とは独立しているため整合性検査も無し。

加えて TITLE_RE (`scripts/generate_adr_index.py:26`) は `^# (?:ADR )?(\d+)[.:]\s+(.+?)\s*$` を要求するが、`0053-mermaid-source-default-rationale.md:1` のタイトルは `# 0053. Mermaid View デフォルトを Source 固定とする (UIFIX-01)` なので OK、`0020-fastmcp-docker-service-infrastructure.md` の `# ADR 0020: ...` 形式も OK と確認済み。**現状は問題なく動いている** が drift 検知が無いリスクは残る。
**Fix:**
generator に最低限のサニティチェックを足す。
```python
def build_index(adr_dir: Path, categories_data: dict) -> str:
    parsed: dict[str, tuple[str, str, str, str]] = {}
    skipped: list[str] = []
    for md in sorted(adr_dir.glob("[0-9][0-9][0-9][0-9]-*.md")):
        r = parse_adr(md)
        if r:
            parsed[r[0]] = (*r, md.name)
        else:
            skipped.append(md.name)

    if skipped:
        # fail loud — 1 つでも parse 失敗があれば drift 検知で気づける
        raise RuntimeError(f"Failed to parse ADR title in: {skipped}")
    # ... rest unchanged
```

### WR-05: MermaidBlock の `lastTheme` がモジュールレベルで共有され、テスト分離を壊す

**File:** `frontend/src/components/MermaidBlock.tsx:18-30`
**Issue:**
`let mermaidId = 0` と `let lastTheme: string | null = null` がモジュールトップレベルで定義されており、`mermaid.initialize()` が theme 変化を観察したときのみ呼ばれる設計。グローバル mutable state を使うパターン自体は性能上の妥当性があるが:

1. テスト時に複数の `MermaidBlock` を異なる theme で render するとキャッシュが汚染される（テスト間で `lastTheme` を reset する経路がない）。
2. `mermaidId` が単調増加なので、長時間 SPA を使い続けると ID 値が大きくなり続ける（実害は無いが mermaid SVG の DOM id が予測可能になりセキュリティ上の懸念は微小）。
3. `initMermaid` は `theme === 'dark' ? 'dark' : 'default'` と判定するが、`Theme` 型は `'light' | 'dark'` の 2 値のため `'default'` 分岐は安全 — ただし将来 `Theme` に `'auto'` 等を追加した瞬間に未テストの dark default に倒れる。

**Fix:**
最低限、`initMermaid` の theme 判定を defensive にしておく。
```ts
function initMermaid(theme: Theme) {
  const t: 'dark' | 'default' = theme === 'dark' ? 'dark' : 'default';
  if (lastTheme === t) return;
  lastTheme = t;
  mermaid.initialize({ startOnLoad: false, theme: t, securityLevel: 'strict' });
}
```
`Theme` が今後 union を拡張したらコンパイル時に明示的に判定を追加すべき。

### WR-06: tests/test_canvas_api.py の `not_deployed_row` が未使用 (deployed=true テスト)

**File:** `tests/test_canvas_api.py:48`
**Issue:**
`test_list_canvas_apps_deployed_filter` で `not_deployed_row` を作っているが、これを `mock_cur.fetchall` の返り値に含めていない (`return_value=[deployed_row]` のみ)。つまり「サーバー側がフィルタしている」のではなく「mock がフィルタした結果だけを返している」状態で、実質的にフィルタロジック (SQL の `WHERE deployed=true` 句や route のクエリ組み立て) を検証していない。route が `?deployed=true` を受けて何か filter を実装したかは確認されず、deployed=False を **silently 通過させる** デグレを検知できない。
**Fix:**
mock cursor に「全行返す」設定をした上で、route 層が `?deployed=true` パラメータをサーバー側 SQL の WHERE 句に組み込んでいることを `executed_sqls` で確認するか、もしくは route 内 Python filter で `[a for a in apps if a.deployed]` が掛かっているか cover する。
```python
# mock_cur.fetchall = AsyncMock(return_value=[deployed_row])
mock_cur.fetchall = AsyncMock(return_value=[deployed_row, not_deployed_row])
# その上で executed_sqls をキャプチャして WHERE deployed=true が含まれることを assert
```
未使用変数は IDE で警告が出るが、未使用なまま放置すると本質的なテスト失敗を見落とす。

### WR-07: `useThreads.bulkRemoveThreads` が Promise.all で失敗した個別エラーを silently 飲み込む

**File:** `frontend/src/hooks/useThreads.ts:77-85`
**Issue:**
`Promise.all(threadIds.map((id) => apiDeleteThread(id)))` は **1 件でも reject されると全体が reject** し、`bulkRemoveThreads` の caller には 1 つの例外として伝播。しかしハンドラの try/catch が caller 側にないため (`ThreadSidebar` 側コードは未読だが、削除後の `setThreads` filter は **`bulkRemoveThreads` 内の `await` 後に必ず実行される**ことを前提) `await` が throw した瞬間、`setThreads`・`setActiveThreadId(null)` は呼ばれず UI 状態が DB と乖離する（削除成功した thread もリストに残る）。
**Fix:**
`Promise.allSettled` を使い、成功した ID だけを `idSet` に入れる。
```ts
const bulkRemoveThreads = useCallback(async (threadIds: string[]) => {
  const results = await Promise.allSettled(
    threadIds.map((id) => apiDeleteThread(id))
  );
  const deletedIds = threadIds.filter(
    (_, i) => results[i].status === 'fulfilled'
  );
  const idSet = new Set(deletedIds);
  setThreads((prev) => prev.filter((t) => !idSet.has(t.thread_id)));
  if (activeThreadId && idSet.has(activeThreadId)) {
    setActiveThreadId(null);
    setMessages([]);
  }
  // failed ones は再表示・エラー通知を caller に渡す経路を検討
}, [activeThreadId]);
```

## Info

### IN-01: JobStore.push_turn 内の `import json as _json` が dead

**File:** `app/jobs/job_store.py:37-38`
**Issue:**
module 先頭 (`app/jobs/job_store.py:1`) で `import json` 済みなのに、`push_turn` 内で再度 `import json as _json` している。元々 in-memory queue 経路を削除した残骸で、Phase 39 UIFIX-03 D-06 でリファクタした際に消し忘れたと思われる。
**Fix:**
```python
async def push_turn(self, job_id: str, name: str, content: str) -> None:
    """Append a debate turn to a Redis list (cross-process safe, polled by SSE)."""
    await self.redis.rpush(f"job:{job_id}:turns", json.dumps({"name": name, "content": content}))
    await self.redis.expire(f"job:{job_id}:turns", 3600)
```

### IN-02: tests/test_jwt_auth.py の `InvalidToken` import が未使用

**File:** `tests/test_jwt_auth.py:6`
**Issue:**
`from cryptography.fernet import InvalidToken` を import しているが、テスト本体は `with pytest.raises(Exception):` を使っており `InvalidToken` 型自体を参照していない。コメントだけで残しているなら削除して `pytest.raises(InvalidToken)` を使うほうが意図が明確。
**Fix:**
```python
# unused import 削除 or
with pytest.raises(InvalidToken):
    decrypt_github_token("notvalidbase64ciphertext")
```

### IN-03: tests/test_debate_handler.py の `call` import が未使用

**File:** `tests/test_debate_handler.py:11`
**Issue:**
`from unittest.mock import AsyncMock, MagicMock, patch, call` の `call` がテスト本体で参照されていない。
**Fix:**
import から `call` を削除。

### IN-04: tests/test_mcp_server.py の `_load_allowlist` import が未使用

**File:** `tests/test_mcp_server.py:442`
**Issue:**
`test_execute_python_returns_stdout` 内で `from tools.execute_python import execute_python, _load_allowlist` と import しているが、`_load_allowlist` は呼ばれず `_cached_allowlist` を直接書き換えているのみ。
**Fix:**
```python
from tools.execute_python import execute_python
```

### IN-05: tests/test_canvas_api.py の `import json` が未使用

**File:** `tests/test_canvas_api.py:8`
**Issue:**
ファイル冒頭で `import json` しているが、ファイル中で `json.dumps` / `json.loads` は呼ばれない (mock cursor が dict をそのまま返すパターン)。
**Fix:**
import 削除。

### IN-06: tests/test_api_chat.py, test_api_auth.py, test_api_models_route.py の `import pytest` が形式的

**File:** `tests/test_api_chat.py:8`, `tests/test_api_auth.py:6`, `tests/test_api_models_route.py:10`
**Issue:**
これらは `pytest.mark.asyncio` を使う test もあれば、`@pytest.fixture` / `pytest.raises` も使うため必須だが、`test_api_chat.py` の async test 群は asyncio_mode auto を前提に `@pytest.mark.asyncio` を省略している (一貫性なし)。
**Fix:**
プロジェクト設定 (`pyproject.toml` の `asyncio_mode`) を確認し、すべての async test に `@pytest.mark.asyncio` を付けるか、auto モードで統一する。Phase 39 のスコープではないが将来 pytest-asyncio のバージョンアップで挙動が変わるリスクがある。

### IN-07: MermaidBlock の `renderDiagram` callback の依存配列に `svgHtml`, `error` を含めている

**File:** `frontend/src/components/MermaidBlock.tsx:107-150`
**Issue:**
`renderDiagram` の `useCallback` 依存に `svgHtml, error` を入れているため、render が成功・失敗するたびに新しい関数 instance が生成される。`handleView` がこれに依存しているため、`handleView` も毎レンダ再生成される。`memo()` で囲っているコンポーネントだが props がオブジェクトでなければ問題なし。実害なし、ただし intent unclear。
**Fix:**
state を ref に逃すか、`renderDiagram` 内で関数開始時に最新値を読み直す pattern に変える。Phase 39 polish のスコープ外なので info 扱い。

### IN-08: tests/test_api_me.py の `MOCK_GITHUB_USER` への path 解決が file 内で散らばっている

**File:** `tests/test_api_me.py:8-13`, `tests/test_api_me.py:48`
**Issue:**
`MOCK_GITHUB_USER` を module-level で定義しているが、`patch("app.api.routes.me.httpx.AsyncClient", ...)` の patch path は test ごとに直書きで、route module path がリファクタされた瞬間に全テストが silently mock しなくなる。`api_client.cookies.clear()` パターン (test_get_me_no_cookie) は OK だが、テスト間の前提条件 (前テストが残した state) が conftest fixture の scope 設計によって意図せず漏れる可能性がある。**ただし current code は問題なし** — `api_client` fixture が function scope なので毎回新規 cookies。
**Fix:**
patch path を module-level 定数化して中央集権化。
```python
ME_HTTPX_PATCH = "app.api.routes.me.httpx.AsyncClient"
# ... 各テストで patch(ME_HTTPX_PATCH, ...)
```

---

## ボーナス観察 (Out-of-Scope だが言及)

- **`AttachmentButton.tsx:14-19`** の `DEFAULT_ACCEPT` 配列に `text/*` を MIME wildcard で混ぜているが、ブラウザの `<input accept>` 属性は MIME と拡張子の mix が一部ブラウザ (Safari の古い版) で挙動差がある。社内 200 名向けで Chromium 想定なら問題なし。
- **`SuperChatApp.tsx:151`** の `filteredAgents` が毎レンダ新規配列を作るので、`useAgents()` の selectedAgents 変化で `<AgentSelector>` が必ず再レンダ。`useMemo` で memo 化する余地あり (性能の話なので v1 review スコープ外)。
- **`ChatApp.tsx:174` `onCanvasResponse` クロージャ** が `setCanvasApp` 依存無しに `setCanvasApp(app)` を呼ぶ — `useCanvas` から取得しているため `useChat` の依存配列に追加されていないと stale closure が発生し得る (`useChat` の実装を未読のためこれは推測)。

---

_Reviewed: 2026-05-13T15:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
