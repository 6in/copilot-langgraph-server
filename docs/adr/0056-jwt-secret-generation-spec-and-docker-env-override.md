# 0056. JWT_SECRET の生成規格と Docker 環境での env 明示指定

**Date:** 2026-05-13
**Status:** Accepted

## Context

JWT HS256 署名キーの取り扱いは Quick 260401-lkq で確立された「`JWT_SECRET` 環境変数 → file fallback (`~/.copilot_sdk/.jwt_secret`)」の二段構えになっている (`app/auth/jwt_utils.py` `_get_jwt_secret()`)。コード内部の生成器は `secrets.token_hex(32)` = 32 バイト (256 bit) の hex 文字列。

しかし以下の運用課題が表面化した:

1. **`.env.example` のプレースホルダ値が不適切:** commit `7bd52c1` で追加された値 `XJXJXJXJXJXXJXJXJXJXXJX` は 23 文字でランダム性ゼロ。HS256 推奨キー長 (RFC 7518: ハッシュ出力長 = 256 bit) を満たさず、開発者が誤ってこの値を本番に持ち出すリスクもある
2. **生成方法がどこにも文書化されていない:** README.md の環境変数表に `JWT_SECRET` の記載なし。`docs/adr/0014` (Phase 17 セキュリティ硬化) は blocklist の話で、シークレット生成手順には触れていない。コードを読まないと推奨フォーマットが分からない
3. **Docker 環境での file fallback は信頼できない:** `~/.copilot_sdk/.jwt_secret` はコンテナ内パスで、ボリュームに名前付きマウントしていないと **コンテナ再作成で消える**。消えると次回起動時に新規生成され、既存の JWT cookie がすべて無効化されてユーザーが強制ログアウトする

200 名規模の本番ロールアウトを控え、シークレット管理の運用ガイドラインを明示しないままだとリリース時に踏むことが目に見えていた。

## Decision

**生成規格:**

- `secrets.token_hex(32)` で生成する **32 バイト = hex 64 文字** の値を採用 (コード内部の挙動と同一)
- これは HS256 の推奨キー長 (256 bit) と一致し、SHA-256 出力長と同等のエントロピーを確保
- 生成コマンドは `python3 -c "import secrets; print(secrets.token_hex(32))"`

**運用ガイドライン:**

- **Docker 環境では `JWT_SECRET` 環境変数を明示指定する** (file fallback には依存しない)
- 理由: コンテナ再作成で `~/.copilot_sdk/.jwt_secret` が消えると全ユーザーが強制ログアウトされるため、env で固定値を渡すほうが安定
- 本番では `.env` をリポジトリに含めず、デプロイ環境 (docker compose / Kubernetes Secret 等) で注入する
- 既存値のローテーション時は全ユーザー強制ログアウトを伴う旨を運用側が認識する

**ドキュメンテーション:**

- `.env.example` 内に生成コマンドのコメントと proper な hex 64 文字のプレースホルダ値を記載
- `README.md` の環境変数表に `JWT_SECRET` 行を追加 (生成手順 + Docker での明示指定推奨理由を含む)

## Alternatives Considered

### A. ファイル fallback (`~/.copilot_sdk/.jwt_secret`) を Docker でも信頼する

`docker-compose.yml` でホストの `~/.copilot_sdk/` をコンテナにボリュームマウントし、自動生成された値をコンテナ間で共有する案。

**却下理由:**

- ホスト依存性が増す (ホスト側の `~/.copilot_sdk/` パーミッション・所有者と container 内 user の擦り合わせが必要)
- 開発者ごとにホスト環境が違うため、複数開発者で動かす場合 reproducible にならない
- 本番では Kubernetes Secret などの標準的なシークレット注入機構を使うので、env 経由のほうが本番との一貫性が高い
- file fallback は「ローカル単体実行 (uvicorn 直起動など)」のための保険として残しておくが、Docker 経由ではあえて使わない

### B. ランダム生成を `cryptography.fernet.Fernet.generate_key()` に統一

既存コード `_get_fernet()` が GitHub トークン暗号化に Fernet を使っているので、生成器を統一する案。

**却下理由:**

- Fernet キーは 32 バイトの base64url エンコード (URL-safe) で 44 文字。HS256 のキー素材としては問題ないが、コード本体は `secrets.token_hex(32)` を使っているので、生成器を変えると **既存の `_get_jwt_secret()` 実装と乖離する**
- ADR は「実装と運用ガイドの一致」を優先し、コードと同じ `secrets.token_hex(32)` を正規規格とする
- Fernet は GitHub トークン暗号化 (`COPILOT_ENC_KEY` 経路) と用途を分離

### C. キー長を 64 バイトに拡張

HS512 への切り替えや、より長いキーで余裕を持たせる案。

**却下理由:**

- HS256 にとって 32 バイトは仕様上の推奨下限ではなく上限 (ブロックサイズ) と一致する適正値
- 既存 JWT は HS256 で発行済みのため、アルゴリズム変更は破壊的変更
- 余剰エントロピーは攻撃面を実質的に改善しない (生成器が CSPRNG であれば 32 バイトで十分)

## Consequences

### Positive

- **`.env.example` がそのまま動く:** 開発者が初回 `cp .env.example .env` した直後から JWT 検証が動作する (旧プレースホルダは短すぎてエッジケースを踏む可能性があった)
- **生成手順が `README.md` と `.env.example` の両方に書かれている:** どちらを開いても再現可能
- **本番ローテーション運用の前提が明文化された:** 「Docker では env 明示指定」が ADR として残るので、将来の運用担当者が file fallback に頼って事故を起こすリスクを下げられる

### Negative / Gotchas

- **`.env.example` の値は「サンプル」だが、コピペして使われると共有秘密になる:** ADR と `.env.example` 内コメントで「本番では必ず新しい値に差し替えること」を強調するが、実運用での遵守は開発者の規律に依存する
- **シークレットローテーション = 全ユーザー強制ログアウト:** 既存 JWT がすべて無効になる仕様 (HS256 単一キー方式)。鍵 rotation 戦略 (旧鍵 grace period 等) は本 ADR のスコープ外
- **`.env.example` の値が git history に残る:** リポジトリは社内クローズドだが、もしホスティング先変更や OSS 化があった場合は注意。後続 ADR で「サンプル値もダミー固定値より placeholder text (例: `<your-32-byte-hex>`) のほうが望ましいか」を再検討する余地あり
- **file fallback は完全撤去していない:** ローカル単体実行 (Docker を使わない uvicorn 直起動など) では引き続き有効。判断軸は「Docker 経由なら env、それ以外は fallback」で運用する

### Related

- Quick 260401-lkq — `_get_jwt_secret()` 二段構えの最初の実装 (env → file fallback)
- ADR 0014 — Phase 17 セキュリティ硬化 (JWT blocklist の Redis 移行)
- `app/auth/jwt_utils.py:102` — 内部生成器 `secrets.token_hex(32)` の参照実装
