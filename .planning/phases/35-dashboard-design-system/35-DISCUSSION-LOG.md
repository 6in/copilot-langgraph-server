# Phase 35: ダッシュボード化 + レスポンシブ/デザイン統一 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-23
**Phase:** 35-dashboard-design-system
**Areas discussed:** Design token 統一方針, MenuScreen ダッシュボード化, モバイル幅対応の深さ, MessageArea のリファクタ範囲

---

## Design Token 統一方針 (Area 1)

### 実装方式

| Option | Description | Selected |
|--------|-------------|----------|
| CSS custom properties | `:root` と `[data-theme="dark"]` に `--color-*` 等を定義、コンポーネント側は `var(--color-*)` 参照。`isDark` 三項を排除。chatscope override も統一可能 | ✓ |
| Tailwind 導入 | `tailwind.config` で color / breakpoint / spacing 一元管理。規約・生態系的だが全コンポーネント書き換え、chatscope と交差が複雑 | |
| 現状維持 + 新規のみ変数化 | 既存 inline style + theme.css overrides を維持、新規追加のみ変数化。スコープ最小だが二重構造 | |

**User's choice:** CSS custom properties（推奨）
**Notes:** chatscope との共存・既存コードへの影響最小・isDark 三項排除の全てを満たす方式として採用。

### 移行戦略

| Option | Description | Selected |
|--------|-------------|----------|
| Base layer + 主要 4 コンポーネント移行 | Phase 35 で theme.css に root 変数定義 + Menu/MessageArea/ThreadSidebar/Header の 4 コンポーネント移行、残りは gradual | ✓ |
| Base layer のみ追加 | 変数だけ定義し既存 inline style はそのまま。Phase 36 以降の新規実装でのみ使用。DRY 改善なし | |
| 全面移行 | Phase 35 内に全 .tsx をリファクタ。重いがゼロ手戻り | |

**User's choice:** Base layer + 主要 4 コンポーネント移行（推奨）
**Notes:** Phase 36 の InputBar 追加は MessageArea 移行と統合できる。残りコンポーネントは必要になった時点で gradual に移行する運用。

---

## MenuScreen ダッシュボード化の方向性 (Area 2)

### ダッシュボード形式

| Option | Description | Selected |
|--------|-------------|----------|
| セクション型ダッシュボード | 「アプリケーション」「最近のスレッド」「その他」等の縦セクション。カード以外の情報も配置できる | ✓ |
| リッチカード維持 + 文言強化 | カード grid を維持、icon / description / 近況を追加。小さく終わるが UX-03 達成が微妙 | |
| Widget 型（Gmail/Notion 風） | 各アプリの最終スレッド / 作成中 Gem / デプロイライブ Canvas を widget として配置。リッチだが情報整理コスト高 | |

**User's choice:** セクション型ダッシュボード（推奨）
**Notes:** 社内 200 名規模・初見ユーザー導線を重視。widget 型はオーバー、リッチカードのみでは UX-03 達成が微妙と判断。

### 添付ファイル情報を出すか

| Option | Description | Selected |
|--------|-------------|----------|
| 出さない | Phase 35 ではスレッド一覧・アプリカードに限定。添付ファイルは各スレッドに階層化される情報なので MenuScreen で見せないが自然 | ✓ |
| セクションだけ先行して Phase 36 で埋める | 「最近の添付ファイル」セクションを空で用意、Phase 36 で中身実装。Phase 38 ダウンロード履歴とも共用可能 | |
| Phase 35 で空の placeholder も作らない | Phase 36 時点では添付は MessageArea でのみ見せ、MenuScreen 無関心 | |

**User's choice:** 出さない（推奨）
**Notes:** Phase 36 / Phase 38 で要求が出たら再設計する。Phase 35 では placeholder すら作らない最小方針。

---

## モバイル幅対応の深さ (Area 3)

### 対応深度

| Option | Description | Selected |
|--------|-------------|----------|
| タブレットまで対応（768-1024px） | タブレット幅で破綻ゼロ、スマホ幅 (375-767px) はレイアウト確保のみ。社内 200 名の PC 主体用途に即する | ✓ |
| 破綻回避のみ（>=375px） | 機能は PC 前提、スマホで見た時にボタン重なり/横スクロールだけ回避。UX-04 最低満たす | |
| 全機能スマホ対応（375-768px） | 添付含め全てタッチフレンドリー。コスト高・PROJECT.md Out of Scope と矛盾 | |

**User's choice:** タブレットまで対応（推奨）
**Notes:** Phase 36 の添付操作もタブレット幅で実用レベル。スマホは破綻回避のみで UX 劣化を許容する方針。

### breakpoint と responsive 戦略

| Option | Description | Selected |
|--------|-------------|----------|
| desktop-first 2 breakpoint | `@media (max-width: 1024px)` で tablet、`(max-width: 767px)` で mobile。既存 inline style が desktop 想定なので相性良い | ✓ |
| mobile-first 3 breakpoint | スマホベースで tablet/desktop/wide に拡張。モダンだが既存 inline style を base から見直す必要あり | |
| 1 breakpoint のみ | `<=768px` を「コンパクト mode」として 1 本の media query で切替。最低コストだが粒度粗い | |

**User's choice:** desktop-first 2 breakpoint（推奨）
**Notes:** 既存コード (desktop 想定) との整合性、タブレット / スマホで異なる挙動（ThreadSidebar drawer 化等）が必要な点を考慮。

---

## MessageArea のリファクタ範囲 (Area 4)

### リファクタ深度

| Option | Description | Selected |
|--------|-------------|----------|
| InputBar 分離 + デザイントークン適用 | MessageArea から `InputBar` 分離、toolbar / preview スロット予約、CSS 変数適用 | ✓ |
| スロット（空構造）のみ確保、分離なし | inline style 内に toolbar / preview スペースを確保、コンポーネント分離はしない。Phase 36 実装時に中身混在しがち | |
| 全面書き直し | InputBar / MessageList / MessageBubble 全て分離。Phase 35 最大スコープ、Phase 36 手戻りゼロ | |
| リファクタしない | Phase 35 は design token + CSS のみ、構造は Phase 36 側に委ねる | |

**User's choice:** InputBar 分離 + デザイントークン適用（推奨）
**Notes:** Phase 36 での手戻り回避とスコープ肥大のバランスを取る。MessageList / MessageBubble は既存維持で Phase 35 に留まらせない。

### 添付ボタンの配置位置

| Option | Description | Selected |
|--------|-------------|----------|
| textarea 左の toolbar 行 | ChatGPT / Claude スタイル。icon button 群を textarea の左に横並び。デスクトップ・タブレット両対応 | ✓ |
| textarea 上の toolbar 行 | 横幅いっぱいの toolbar を textarea 上に配置。警告バナーも統合可能だが縦スペースを食う | |
| textarea 内 floating icon | textarea 下側に浮かせる（Slack 風）。コンパクトだが chatscope の幅制御と相性悪い | |

**User's choice:** textarea 左の toolbar 行（推奨）
**Notes:** メンタルモデルの一致（ChatGPT / Claude）、タブレット幅でも操作しやすい、chatscope との競合が少ない、の 3 点で採用。

---

## Claude's Discretion

以下は researcher / planner が決定する:
- CSS 変数の具体的な命名規則（`--color-accent` 等の prefix / 階層）
- トークン階層（primitive + semantic の 2 層 vs 1 層）
- chatscope override の置換粒度
- ダッシュボードセクションの具体的構成（セクション数・順序・カード内密度）
- ThreadSidebar の mobile drawer 化方式
- Header の mobile stacking 方式
- InputBar の props signature 詳細
- タブレット幅での chatscope バルーン width 調整値

## Deferred Ideas

- Phase 36: 添付機能本体（FIN-01 / FIN-02 / multimodal 警告）
- Phase 38: 「最近生成したファイル」を MenuScreen に追加
- Phase 39: chatscope バルーン幅 / Mermaid hang / test_sse hang（UIFIX-01〜03）
- v6.1+: 残り 9 コンポーネントの design token 移行、スマホ幅全機能対応、ネイティブアプリ
