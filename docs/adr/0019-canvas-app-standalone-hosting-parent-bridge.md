# 0019. Canvas アプリのスタンドアロンホスティングと parent-bridge.js 共通化

**Date:** 2026-04-09  
**Status:** Accepted

## Context

Phase 18 で実装した iframe postMessage JSON-RPC ブリッジは CanvasPane.tsx（React 内のプレビューペイン）専用だった。  
しかし Canvas アプリを `/apps/{app_id}/` URL でスタンドアロン公開したいというニーズが生まれ、Phase 19 でホスティングシェルを実装することになった。

ここで問題が生じた：ホスティングシェルは静的 HTML（FastAPI が動的生成する `srcdoc` 文字列）であり、React コンポーネントではない。  
Phase 18 の postMessage リレーロジックは `useRef` / `useCallback` / `iframeRef` など React 固有の仕組みに依存していたため、Shell HTML にそのまま転用できなかった。

## Decision

postMessage リレーロジックを **`static/js/parent-bridge.js`** として独立したスクリプトに抽出し、両方の文脈（CanvasPane と Shell HTML）から `<script src>` で読み込む設計に変更した。

主な設計判断：

1. **`e.source` で返信先を特定**: React の `iframeRef` に依存せず、`e.source`（postMessage 送信元の window）に直接返信することで React 外でも動作する。
2. **`window.__parentBridgeInstalled` でべき等ガード**: 同じページに複数回 `<script>` が読み込まれても二重登録しない。
3. **`GET /apps/{app_id}` 動的シェル**: FastAPI の `hosted_apps.py` が DB から HTML を取得し、`srcdoc` に埋め込んだシェル HTML を返す。`<script src="/js/parent-bridge.js">` で親フレームにリレーを注入。
4. **FastAPI ルート登録順序**: `hosted_apps.router` を `/apps` StaticFiles マウントより**前**に登録することで、動的ルートが静的ファイルより先にマッチする。
5. **CanvasPane.tsx のリファクタ**: `useRef` / `handleIframeMessage` / `iframeRef` を削除し、`parent-bridge.js` を `document.head` にスクリプト注入する `useEffect` に置き換えた。

## Alternatives Considered

### CanvasPane のロジックをコピーして Shell HTML にも書く
最初の案はシェル HTML にインライン JavaScript としてリレーロジックを複製することだった。実装は容易だが、2箇所に同じロジックが存在すると片方だけ修正して不整合が起きるリスクがある。parent-bridge.js による共通化を選択した。

### React コンポーネントとしてのホスティングシェル
ホスティング画面を React アプリとして実装すれば、既存の `useRef` ベースのロジックをそのまま使えた。しかし `/apps/{app_id}/` は認証不要・React bundle 不要のシンプルなページであり、FastAPI が HTML を直接返す方が軽量で適切と判断した。

### `iframeRef` を使ったグローバル管理
window 上にグローバル変数として iframe 参照を持つ案もあったが、`e.source` が常に正確な返信先を指しているため不要だった。

## Consequences

**ポジティブ:**
- CanvasPane（React プレビュー）とホスティングシェル（静的 HTML）が同一のリレーロジックを共有し、バグ修正が1箇所で完結する
- `e.source` ベースの実装により、React に依存しない汎用的なブリッジスクリプトになった
- `GET /apps/{app_id}/` でデプロイ済み Canvas アプリをスタンドアロン URL で公開できるようになった

**ネガティブ / 注意点:**
- **FastAPI ルート順序が重要**: `hosted_apps.router` を `StaticFiles` より後に登録すると `/apps/{app_id}` が静的ファイルにマッチしてしまい 404 になる。`app/api/main.py` の登録順を変えるときは注意。
- **srcdoc のエスケープ必須**: `"` → `&quot;`、`&` → `&amp;` の変換が抜けると HTML 属性が壊れる（T-19-02）。`hosted_apps.py` の `html.escape(html, quote=True)` を削除しないこと。
- **sandbox 制限**: `allow-scripts allow-forms` のみ。`allow-same-origin` を追加すると XSS リスクが生じるため禁止（T-19-03）。
- **JWT 認証の変遷**: Phase 19 実装中に `/api/iframe-rpc` の認証を一時的に `auth_manager.load_token()`（サーバー共有トークン）に変更したが、UAT で問題が判明して JWT Cookie 認証に復活した。`parent-bridge.js` は `credentials: 'include'` でリクエストするためブラウザが Cookie を自動付与する。
- **`/apps/{app_id}/` は現時点で認証不要**: URL を知っていれば誰でもアクセスできる（T-19-01 accepted）。将来的に認証が必要になった場合は `hosted_apps.py` に JWT チェックを追加する。
