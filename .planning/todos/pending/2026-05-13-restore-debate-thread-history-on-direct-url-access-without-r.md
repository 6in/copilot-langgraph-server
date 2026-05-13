---
created: 2026-05-13T07:17:55Z
title: Debate Chat で URL 直接アクセス時に過去スレッドの履歴を復元する
area: ui
files:
  - frontend/src/components/DebateChatApp.tsx:818-832
  - frontend/src/components/DebateChatApp.tsx:534-555
---

## Problem

`/orochi/debate/{threadId}` に URL 直接アクセス (リロード含む) しても、必ず **「討論チャットを設定」画面** に戻ってしまい、既存スレッドの履歴が表示されない。

原因は `DebateChatApp.tsx:818-832` の root コンポーネント:

```ts
export function DebateChatApp({ selectedModel }: DebateChatAppProps) {
  const [config, setConfig] = useState<DebateConfig | null>(null);
  // ...
  if (config === null) {
    return <DebateConfigPanel onStart={handleStart} isDark={isDark} />;  // ← 必ず設定画面
  }
  return <DebateChatPanel config={config} selectedModel={selectedModel} />;
}
```

`config` はローカル React state で、URL/thread から復元する経路がない。`DebateChatPanel` 側 (`L534-555`) は URL の `threadId` から `switchThread` を呼ぶが、そもそも `DebateChatPanel` が render されるのは「討論を開始」ボタンを押した後だけなので、リロード時には必ず設定画面に戻る。

実際の挙動: 直近の thread `9412d903-4f15-4619-9c12-2fb4d5da4a45` (6in 所有, 10 checkpoints) に直接アクセスしても設定画面が出る。参加者を 2 名以上選んで「討論を開始」を押すと、初めて DebateChatPanel が描画され、useEffect → switchThread → 履歴が API から取得される。

Chat / SuperChat / Gem / Canvas は URL の thread ID から即座に履歴を復元する設計なので、Debate Chat だけ UX が一貫していない。

## Solution

`DebateChatApp` で URL に thread ID があれば config を自動復元する。

### Option A (推奨): 既存スレッドの config をサーバ側で永続化して復元

1. **schema**: `threads` テーブルに `debate_config JSONB` カラムを追加 (Debate Chat のときだけ使用、それ以外 NULL)
2. **send 時**: `useChat` 経由で送信した最初のメッセージ (もしくは「討論を開始」直後) の段階で、`POST /api/threads/{id}/debate-config` で `participants` / `pattern` / `gemIds` / `gemNames` / `maxTurns` を保存
3. **load 時**: `DebateChatApp` の `useEffect` で urlThreadId がある & `config === null` のとき `GET /api/threads/{id}/debate-config` を呼び、結果を `setConfig(...)` する。404 (新規スレッド) なら従来通り setup 画面
4. UX: 既存スレッドの URL を踏んだら自動で履歴復元 + 元の設定で延長可能

### Option B (最小): localStorage に config を保存

1. `setConfig` 直後に `localStorage.setItem('debate:config:' + threadId, JSON.stringify(c))` で保存
2. mount 時に `localStorage.getItem` で復元
3. 課題: 別端末・別ブラウザでアクセスすると復元できない。ユーザーが 200 名規模で同じ thread を共有するワークフローがなければ実用上問題ない

### Option C (最小×2): URL クエリパラメータに config を載せる

1. `setConfig` 後 `navigate('/debate/${tid}?p=...&pattern=...')` のように config を URL に encode
2. mount 時に `useSearchParams` で読み込み復元
3. 課題: 共有 URL が長くなる。Gem 名や participants は文字数次第で URL 制限に当たる

## Recommended

Option A。サーバ側の single source of truth に合わせる方針 (Canvas の `canvas_apps.html`, gems の DB 永続化と同じパターン)。schema migration が要るが、Canvas Editor diff todo と同じ「`threads` 拡張」系の変更なので、Phase の単位を揃えて一緒に取り組めば効率的。

## Out of Scope

- 既存 thread の `debate_config` をマイグレーションで埋める (NULL のままで初回アクセス時に「設定画面に戻ります」と warning 表示する fallback で十分)
- Debate config の編集 UI (現状は一度開始したら変えられない設計)
- 過去 thread の「設定だけコピーして新スレッド開始」機能 — UX 強化として別 todo

## Related

- 同日キャプチャ: `2026-05-13-fix-overlapping-agent-message-balloons-in-debate-chat.md` (バルーン重なりの調査中に発見した副次 issue)
- 同日キャプチャ: `2026-05-13-canvas-editor-diff-between-current-html-and-deployed-html.md` — `canvas_apps` の schema 拡張系として並べて検討する余地
