---
created: 2026-05-13T08:06:25Z
title: SuperChat の URL から冗長な default app slug を省く (/superchat/superchat → /superchat)
area: ui
files:
  - frontend/src/App.tsx:262-263
  - frontend/src/App.tsx:32-92
  - frontend/src/App.tsx:159
  - frontend/src/components/SuperChatApp.tsx:198
  - frontend/src/components/SuperChatApp.tsx:202
  - frontend/src/components/SuperChatApp.tsx:214
---

## Problem

SuperChat の URL が `http://localhost:5173/orochi/superchat/superchat` のように `superchat` が 2 回現れて冗長。希望は `http://localhost:5173/orochi/superchat`。

## Background

ルーティングは `App.tsx:262-263`:

```ts
<Route path="superchat/:appSlug" element={<SuperChatWrapper {...common} />} />
<Route path="superchat/:appSlug/:threadId" element={<SuperChatWrapper {...common} />} />
```

`SuperChatWrapper` (`App.tsx:35-92`) は `useParams` で `appSlug` を取得し、`/api/apps` から AppDefinition を解決してから `SuperChatApp` に渡す Phase 25 の設計 (multi-app 拡張のため)。デフォルトの SuperChat 自身が `applications` テーブル上に slug=`"superchat"` で登録されているため、URL の 2 段目に `superchat` が出てくる。

ナビゲーション側 (`App.tsx:159`, `SuperChatApp.tsx:198/202/214`) も `/superchat/${app.slug}` 形式で生成している。

## Solution

**Option A (推奨): default app shortcut を route 層で追加**

`App.tsx` に「appSlug なしの場合は `superchat` をデフォルトとして解決する」route を加える。

```ts
// 既存
<Route path="superchat/:appSlug" element={<SuperChatWrapper {...common} />} />
<Route path="superchat/:appSlug/:threadId" element={<SuperChatWrapper {...common} />} />

// 追加
<Route path="superchat" element={<SuperChatWrapper {...common} />} />
<Route path="superchat/:threadId" element={<SuperChatWrapper {...common} />} />  // ← /:threadId は appSlug より優先される必要あり (順序注意)
```

ただし React Router v6/v7 では `superchat/:threadId` と `superchat/:appSlug` は同じ shape のため衝突する。**threadId は UUID 形式なので識別可能** だが、Router は正規表現マッチしないので **どちらか一方しか route 定義できない**。

代替案: `SuperChatWrapper` 内で `appSlug` が `undefined` なら `"superchat"` を使う:

```ts
const { appSlug: rawSlug, threadId: rawThread } = useParams<{ appSlug?: string; threadId?: string }>();
// /superchat/<uuid> パターン → uuid なら threadId、それ以外なら appSlug
const looksLikeUuid = (s: string | undefined) => s && /^[0-9a-f]{8}-/.test(s);
const appSlug = looksLikeUuid(rawSlug) ? 'superchat' : (rawSlug ?? 'superchat');
const threadId = looksLikeUuid(rawSlug) ? rawSlug : rawThread;
```

これでルートは:
- `/superchat`             → default app, no thread
- `/superchat/<uuid>`      → default app, thread = uuid
- `/superchat/<slug>`      → 別 app, no thread
- `/superchat/<slug>/<uuid>` → 別 app, thread = uuid

ただし「slug が UUID 形式」だと衝突する。app slug は `applications` テーブル管理なので UUID 形式を禁止する制約を入れれば回避可能。

**Option B: ルート構造を変える**

- default SuperChat → `/superchat` 専用 route で別 wrapper を作る
- 別 app の SuperChat → `/apps/:appSlug` に分離 (ホスティング `/apps/{id}/` と混同しないよう注意)

メリット: 両方の URL が短くなる、衝突がない。デメリット: applications テーブル / `/api/apps` の意味が変わる可能性。

**Option C: 最小: redirect だけ**

- `/superchat` にアクセスしたら `/superchat/superchat` に redirect
- 表示 URL は変わらないが、ブックマーク・タイプ入力時は短く済む

```ts
<Route path="superchat" element={<Navigate to="/superchat/superchat" replace />} />
```

## Recommended

**Option A の改修版** (slug UUID 形式禁止 + Wrapper 内分岐) が筋が良い。実装は 30 行程度で済むはず。

実装時の変更点:
1. `App.tsx:262-263` に `superchat` / `superchat/:slugOrThreadId` ルート追加
2. `SuperChatWrapper` の useParams 処理を UUID 判定で分岐
3. `App.tsx:159` の `navigate('/superchat/${app.slug}')` を「app.slug が `superchat` ならスキップ」に変更
4. `SuperChatApp.tsx:198/202/214` も同様に default slug を省く navigate 関数に統一 (ヘルパー `buildSuperChatPath(appSlug, threadId)` を新設)
5. テスト: app `superchat`/別 app の組み合わせ × thread あり/なしの 4 ケース

## Out of Scope

- 他の URL (`/chat`, `/canvaschat`, `/gemchat`, `/debate`) の正規化 — それらは既に冗長性なし
- 既存ブックマーク `/superchat/superchat/<uuid>` の互換性維持 — `App.tsx:262-263` の旧ルートを残せば自動的に動く

## Related

- Phase 25 で導入された multi-app 構造の前提を踏襲
- 関連 ADR: `docs/adr/0051-multi-app-rollout-process-patterns.md` を確認すること (multi-app rollout)

---

## Resolved 2026-05-13 — Phase 40 Plan 03

- Implemented in: .planning/phases/40-ui-polish-round-2-frontend-only/40-03-PLAN.md / 40-03-SUMMARY.md
- ROADMAP Success Criteria: 5 (UI-SUPERCHAT-URL)
- Commits: 1a2f7e6, f65d2a2
