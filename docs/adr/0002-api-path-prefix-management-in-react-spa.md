# 0002. API Path Prefix Management in React SPA

**Date:** 2026-04-03  
**Status:** Accepted

## Context

nginx リバースプロキシ経由で `/orochi/` などのサブパスにアプリを配置したい。
React SPA から FastAPI への API 呼び出しパス（`/api/auth/start` など）が、
デプロイ先のパス構成に関係なく正しく解決される必要があった。

具体的な制約:
- FastAPI のルートは `/api/...` のまま変更したくない（nginx が prefix を除去する）
- React アプリは `/orochi/react/` のようなサブパスにマウントされうる
- 開発時は Vite dev server（`:5173`）、本番は nginx 経由、どちらでも動く必要がある

## Decision

`VITE_APP_BASE` 環境変数でビルド時に prefix を埋め込み、`client.ts` 内の全パスを
テンプレートリテラルで組み立てる方式を採用。

```ts
const API_BASE = (import.meta.env.VITE_APP_BASE ?? '').replace(/\/$/, '');

export const startAuthFlow = () =>
  apiFetch<AuthStartResponse>(`${API_BASE}/api/auth/start`, { method: 'POST' });
```

- prefix なし（デフォルト）: `API_BASE = ''` → `/api/auth/start`（従来通り）
- prefix あり: `API_BASE = '/orochi'` → `/orochi/api/auth/start`（nginx が除去して FastAPI へ）

Vite dev server のプロキシキーも同じ変数で統一:

```ts
proxy: {
  [`${process.env.VITE_APP_BASE ?? ''}/api`]: {
    target: 'http://api:8000',
    rewrite: (path) => path.replace(new RegExp('^' + (process.env.VITE_APP_BASE ?? '')), ''),
  }
}
```

## Alternatives Considered

**① `VITE_BASE_URL` で絶対パスに prefix を付与（最初の実装）**  
`const BASE_URL = import.meta.env.VITE_BASE_URL ?? ''` を追加し全パスに結合する案。
動作はするが `VITE_BASE_URL` と `VITE_APP_BASE`（Vite の `base` 設定用）の2変数が乱立するため廃棄。

**② `./api/...` 相対パス（2番目の実装）**  
`fetch('./api/auth/start')` のように相対パスにして、ブラウザの URL 解決に任せる案。
React が `/orochi/react/` にマウントされると `./api/...` が `/orochi/react/api/...` に解決されてしまい誤動作するため廃棄。
相対パスが正しく解決されるのはアプリが prefix の直下ルート（`/orochi/`）に置かれている場合のみ。

**③ `<base href>` タグをサーバー側で注入**  
HTML の `<base>` タグで全相対 URL の基準パスを設定する案。
サーバー（FastAPI または nginx）が動的に HTML を書き換える必要があり複雑度が上がるため不採用。

## Consequences

**ポジティブ:**
- `VITE_APP_BASE` 1つで Vite の `base`（アセット URL）・プロキシキー・`API_BASE` が統一される
- prefix なし時はデフォルト空文字列のため既存動作を完全に維持
- React アプリのマウント位置に依存しない（`/react/` でも `/app/` でも動く）

**ネガティブ / 注意点:**
- ビルド時に値が確定するため、ビルド後に prefix を変えるには再ビルドが必要
- **テンプレートリテラルのクォート罠**: `replace_all` などで文字列を一括置換すると、シングルクォート文字列 `'/api/...'` が `'${API_BASE}/api/...'` になり `${}` がそのままの文字列として残るバグが起きる。必ずバッククォート `` `${API_BASE}/api/...` `` を使うこと
- エラーが起きても `startFlow` などに try/catch がないと画面上は何も起きず原因特定が困難になる（エラーハンドリングを忘れずに追加する）
