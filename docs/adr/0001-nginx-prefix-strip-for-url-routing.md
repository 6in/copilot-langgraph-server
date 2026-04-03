# 0001. nginx prefix-strip approach for URL routing

**Date:** 2026-04-03  
**Status:** Accepted

## Context

アプリを `/orochi/` などのサブパスで運用するための URL プレフィックス設計が必要だった。
FastAPI バックエンド・React フロントエンド・nginx リバースプロキシが絡む構成で、
「どのレイヤーがプレフィックスを処理するか」を決める必要があった。

## Decision

nginx の `proxy_pass` に trailing slash を付けることで、プレフィックスをフォワード前に除去する（prefix strip）。
FastAPI のルートは `/api/...` のまま変更しない。`root_path=APP_PREFIX` のみ追加し、OpenAPI docs の URL 認識に使う。
フロントエンドは `VITE_APP_BASE` 環境変数でビルド時にプレフィックスを埋め込み、全 API パスを `` `${API_BASE}/api/...` `` の絶対パスで組み立てる。

```nginx
location /orochi/ {
    proxy_pass http://backend:8000/;  # trailing slash が /orochi を除去
    proxy_set_header X-Forwarded-Prefix /orochi;
}
```

## Alternatives Considered

- **FastAPI 側で prefix 付与**: `APIRouter(prefix=APP_PREFIX)` で FastAPI のルートを `/orochi/api/...` にする案。FastAPI の変更が必要でテストへの影響も大きいため不採用。
- **`VITE_BASE_URL` で絶対パス**: フロントエンドのみで対応する案（当初実装）。nginx なしでは動くが、nginx + prefix 構成では FastAPI 側も変更が必要になり中途半端だったため廃棄。
- **`./api/...` 相対パス**: fetch に相対パスを使いブラウザに解決させる案。React のマウント位置（`/react/`）によって `/react/api/...` に誤解決するため廃棄。

## Consequences

**ポジティブ:**
- FastAPI のルート定義・テストを一切変更しない
- nginx の標準的なパターンで実装できる
- `APP_PREFIX` / `VITE_APP_BASE` の2変数だけで prefix を制御できる

**ネガティブ:**
- prefix を使う場合は nginx が必須（直接 uvicorn 公開時は prefix なし運用）
- フロントエンドのビルド時に `VITE_APP_BASE` を設定し忘れると API パスが壊れる
- テンプレートリテラル（バッククォート）を使わないとビルド後も `${API_BASE}` が文字列として残るバグが起きる（実際に踏んだ）
