---
created: 2026-05-13T07:02:42Z
title: Debate Chat の各エージェント会話バルーンが重なって表示される
area: ui
files:
  - frontend/src/components/DebateChatApp.tsx
---

## Problem

Debate Chat 画面 (`/orochi/debatechat`) で各エージェントの会話バルーン (発言メッセージ枠) が **互いに重なって表示** されてしまい、誰がどの発言をしているか視認しづらい。複数エージェントが順番に発言するレイアウト上、バルーン間の余白・z-index・幅制限のいずれかが効いていない可能性が高い。

## Solution

TBD。調査・修正の入口:

1. **再現確認**: Debate Chat で 2-3 エージェント (例: agent-a / agent-b / gem) を選択し、1 ターン回して重なりの位置をスクリーンショットで取る
2. **DOM 検査**: Chrome DevTools で重なっているバルーン要素を選択し、computed style で `position` / `margin` / `transform` / `flex-shrink` のどれが問題かを切り分け
3. **DebateChatApp.tsx の構造確認**: 832 行の長めコンポーネント。message 描画部 (おそらく `messages.map(...)` の `style={{...}}`) で、`alignItems: 'flex-start'` + `flex-direction: column` + `gap` の値、もしくは agent カラムごとの `width` 設定を確認
4. **共通 MessageArea / MarkdownMessage との差分**: Chat/SuperChat は `@chatscope/chat-ui-kit-react` の `MessageList` を使っている (`MessageArea.tsx`) が、Debate Chat は独自実装。共通化されていないので独自レイアウト崩れの可能性
5. **修正方針候補**:
   - エージェントごとに固定の column を割り当てる timeline 型レイアウト → 各 column 内で縦並びにすれば重ならない
   - 単一カラムで `marginBottom` を agent 別に明示する
   - 全エージェント共通の bubble コンポーネントを抽出して Chat 系と統一する (Phase 35 dashboard design system の延長線)

関連: 同日キャプチャの "AttachmentButton を SuperChat/Gem/Canvas/Debate にも展開" todo と一緒に Debate Chat 側を整理すると効率的。Phase 35 で確立した dashboard design system のトークン (色・spacing) を Debate Chat にも適用する流れに乗せやすい。

---

## 2026-05-13 追加調査 (実画面確認結果)

Chrome DevTools で実 thread (`/orochi/debate/9412d903-4f15-4619-9c12-2fb4d5da4a45`, 6in 所有, 10 checkpoints, agents: general-assistant / 慎重さんGEM / aggregator) を確認した結果、**バルーン同士の重なり**ではなく **chatscope デフォルトバブルと独自カラーバブルの 2 層重ね問題** だった:

- DOM 階層 (DebateChatApp は `MessageArea` 経由で `@chatscope/chat-ui-kit-react` の `<Message>` を使用):
  ```
  SECTION.cs-message.cs-message--incoming           (透明)
    DIV.cs-message__content-wrapper                  (透明)
      DIV.cs-message__content                        (★ bgColor=rgb(198, 227, 250) — chatscope のデフォルト薄青)
        DIV.cs-message__custom-content               (透明)
          DIV                                        (★ bgColor=rgb(255, 248, 238) — Phase 35 のエージェント別カラー)
            DIV (label container)
              SPAN "慎重さんGEM" (badge)
            ... message body ...
  ```
- 外側 `cs-message__content` の **薄青背景が、内側 wrapper のオレンジ/緑背景の上下から数 px はみ出して**、二重縁取りのように見える。スクリーンショット (`/tmp/debate-actual.png`) で上下に薄青の帯が確認できる。
- 各 agent label (badge) 自体は static position で wrapper 内に格納されており、座標としては問題なし。視覚的に "label がバブル境界線に乗っている" ように見えるのは、外側 chatscope bubble の上端が label の真下に来ているため。

### 修正方針

**Option A (最小): chatscope の `cs-message__content` を透明化**

DebateChatApp 内の `MessageArea` 利用箇所、もしくは MessageArea コンポーネント自体に CSS override を追加:

```css
.cs-message__content {
  background: transparent !important;
  padding: 0 !important;
}
```

これだけで外側の薄青がなくなり、wrapper のエージェント別色のみが表示される。Chat / SuperChat / Gem 側で同じバブル構造が使われているなら、副作用 (色付きバブルが見えなくなる) のレビューが必要。

**Option B (筋が良い): Phase 35 design system のトークンを `cs-message__content` 側に流し込む**

Phase 35 でエージェント色トークン (例: `--agent-color-general-assistant`, `--agent-color-jugicho`) を定義しているはず。外側 chatscope bubble の `background` を直接そのトークンで上書きし、内側 wrapper の二重定義を削除。これでバブル背景を 1 層にまとめられる。

**Option C (大改修): Debate Chat だけ chatscope `<Message>` を使うのをやめる**

Chat/SuperChat は chatscope 使用、Debate Chat は独自レイアウト (timeline 型) に切り替える。スコープ大きいので最後の手段。

### 補助発見 (別 TODO 候補)

DebateChatApp は **`/orochi/debate/{threadId}` で URL に thread ID があっても、ローカル React state `config === null` の間は必ず設定画面に戻る** 構造 (`DebateChatApp.tsx:821-829`)。リロード時や直接 URL アクセス時に既存スレッドの履歴が表示されず、毎回参加者を選び直して "討論を開始" を押さないと過去ログが見えない。本 todo とは別の issue だが要 capture。

---

## Resolved 2026-05-13 — Phase 40 Plan 02

- Implemented in: .planning/phases/40-ui-polish-round-2-frontend-only/40-02-PLAN.md / 40-02-SUMMARY.md
- ROADMAP Success Criteria: 3 (UI-BALLOON)
- Commits: 9029c77
