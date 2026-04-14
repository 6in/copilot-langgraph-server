# 0028. React Router v7 による URL ベースルーティングの導入

**Date:** 2026-04-14  
**Status:** Accepted

## Context

それまでの SPA は `useState<Screen>` でアクティブ画面を管理していた。この方式には以下の問題があった:

- ブラウザの「戻る/進む」が機能しない
- チャットスレッド URL を直接共有できない（チャット状態が URL に現れない）
- リロードすると常にメニュー画面に戻る
- `/orochi/` というアプリプレフィックス（`VITE_APP_BASE`）を basename として扱う必要があり、標準的なルーティングライブラリを使わないと設定が煩雑になる

加えて、React Router v7 では `react-router-dom` が `react-router` に統合されており、インストールするパッケージが1つで済む。

## Decision

`react-router` ^7.14.0 を導入し、`BrowserRouter` + `Routes/Route` で SPA を URL ベースルーティングに移行した。

主な変更点:

| ファイル | 変更内容 |
|---------|---------|
| `frontend/package.json` | `react-router ^7.14.0` を追加（`react-router-dom` は不要） |
| `frontend/src/main.tsx` | `<BrowserRouter basename={import.meta.env.BASE_URL.replace(/\/$/, '')}>` でラップ |
| `frontend/src/App.tsx` | `useState<Screen>` を廃止し `<Routes>/<Route>` に置換。各アプリを `/chat/:threadId`・`/superchat/:appSlug/:threadId` 等の URL パスにマッピング |
| 各 ChatApp | `useParams` でスレッド ID を取得、`useNavigate` でスレッド切り替え時に URL を更新 |
| `docs/nginx.md` | React Router の deep URL を直接開いたときの 404 対策として `try_files` SPA フォールバック設定を追記 |

URL 設計:

```
/orochi/                        → MenuScreen
/orochi/chat/:threadId?         → ChatApp
/orochi/superchat/:appSlug/:threadId?  → SuperChatApp
/orochi/gemchat/:gemId/:threadId?      → GemChatApp
/orochi/gems                    → GemsScreen
/orochi/canvas                  → CanvasScreen
/orochi/canvaschat/:threadId?   → CanvasChatApp
/orochi/debate/:threadId?       → DebateChatApp
```

## Alternatives Considered

- **`useState<Screen>` 継続（現状維持）**: URL 共有・ブラウザ履歴が使えないまま。ユーザー体験上の問題が増えると判断し却下。
- **`react-router-dom` を使用**: v7 では `react-router` に統合されており、別途インストールが不要。`react-router` のみで完結させた。
- **`wouter`（軽量代替）**: バンドルサイズは小さいが、`basename` サポートが限定的で `/orochi/` プレフィックスの扱いが煩雑になるため却下。

## Consequences

**ポジティブ:**
- チャットスレッド URL を直接共有・ブックマーク可能になった
- ブラウザの戻る/進むが正しく動作する
- `VITE_APP_BASE`（`/orochi/`）を `basename` に設定することで、nginx のプレフィックス strip と一致した URL 管理が実現
- TypeScript 型エラー（`CanvasResult.name`・`CanvasAppInfo.thread_label` 欠落）が本対応で発覚・修正された

**注意点 / 落とし穴:**
- nginx で React Router の deep URL に直接アクセスすると 404 になる。`try_files $uri $uri/ /orochi/index.html` の SPA フォールバック設定が必須（`docs/nginx.md` 参照）
- `react-router` v7 では `import { BrowserRouter } from 'react-router'`（`react-router-dom` ではない）。誤った import は型エラーではなく実行時エラーになるため注意
- `basename` は末尾スラッシュなしで設定する（`import.meta.env.BASE_URL` は末尾 `/` を含むため `.replace(/\/$/, '')` が必要）
- `threadId` が URL にない初期状態（`/chat/` のみ）でも動作するよう、`:threadId?` のオプショナルパラメータとして定義している
