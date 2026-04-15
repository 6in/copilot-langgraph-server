# 0033. Canvas iframe RPC `ai()` モデル指定機能とエイリアスホワイトリスト

**Date:** 2026-04-15
**Status:** Accepted

## Context

Canvas アプリ（ユーザー定義 HTML を iframe でホストし、親フレームに postMessage JSON-RPC で AI/DB アクセスを要求する仕組み）の AI 呼び出しは Phase 18/19 で追加された `iframe_rpc_handler._handle_ai` を経由する。この経路にはいくつかの問題があった:

1. サーバー側 `_handle_ai` は `params.get("model", "claude-sonnet-4.5")` で既定モデルを読んでいたが、この ID (`claude-sonnet-4.5`) はリポジトリの他箇所 (`app/orchestrator/` 配下) で使用されている実在モデル (`claude-sonnet-4-6`) と食い違っており、実在しない可能性があった。実際 `tests/test_iframe_rpc_handler.py` もこの間違った ID をハードコードしていた。
2. クライアント側 `static/js/iframe-rpc.js` の `ai()` API にはモデル指定の口がなく、`ai(prompt, timeoutMs)` という旧シグネチャしかなかった。つまりプロトコル層は model を受けていたが誰も送れなかった。
3. Canvas アプリの性質はさまざま（挨拶 bot 〜 複雑な要約ツール）で、用途によって軽量/高性能モデルを使い分けてコスト・速度・精度のバランスを取りたい要求があった。既定が重いモデルだと全 Canvas アプリが無駄にコストを払う。
4. 無効なモデル名が渡された場合にどう扱うか未定義だった。

当初の Todo は `app/orchestrator/apps.py`（AppRegistry）と `app/jobs/handlers/langgraph_handler.py` の変更を想定していたが、これは誤った前提だった。Canvas iframe の AI 呼び出しは `iframe_rpc_handler` が本流であり、`apps.py` は別軸のシステムパッケージレジストリで、Canvas HTML アプリは `canvas_apps` DB テーブル管理だった。

## Decision

`iframe_rpc_handler._handle_ai` にサーバー側のモデル解決層を追加し、クライアント `ai()` API を拡張して呼び出し時にモデル指定できるようにする。

**サーバー側 (`app/jobs/handlers/iframe_rpc_handler.py`):**
- `MODEL_ALIASES` 定数でエイリアス→実モデル ID のホワイトリストを定義:
  - `haiku` → `claude-haiku-4-5-20251001`（既定）
  - `sonnet` → `claude-sonnet-4-6`
  - `gpt-4.1` → `gpt-4.1`
- `resolve_model(value)` ヘルパーでエイリアス解決と検証を一元化
- 既定モデルを Sonnet から **Haiku** に変更（軽量・高速・低コストが Canvas 用途の妥当な既定）
- 実モデル ID の直指定もホワイトリスト経由で許可
- 未知のモデル名は **silent fallback せず** `ValueError` → `{result: false, error: ...}` で明示拒否

**クライアント側 (`static/js/iframe-rpc.js`):**
- `ai(prompt, opts)` の `opts` を `{ model?: string, timeoutMs?: number }` オブジェクト形式に拡張
- 第 2 引数が `number` の場合は旧シグネチャ互換で `timeoutMs` として扱う（`typeof === 'number'` 分岐）
- 既存 Canvas アプリ (`ai('hi', 30000)` のような呼び出し) を壊さない

**ドキュメント/プロンプト:**
- `CANVAS_SYSTEM_PROMPT`（`app/api/main.py`、起動時に `_canvas_system_` Gem へ upsert される Canvas 生成用のシステムプロンプト）のベーステンプレート例とシグネチャ表を更新
- `docs/test-iframe-rpc-prompt.md` も同様に更新
- AI が新規 Canvas アプリを生成する際に `ai(prompt, { model: 'haiku' | 'sonnet' | 'gpt-4.1' })` の知識を持てるようにする

**テスト:** 新規 8 ケース + 既存 8 ケース（間違った `claude-sonnet-4.5` ID を `claude-sonnet-4-6` に修正）= 16 passed。

## Alternatives Considered

- **`canvas_apps` テーブルに `default_model` カラム追加:** アプリ単位のデフォルトモデルを DB 永続化する案。正攻法だが DB マイグレーションと canvas CRUD API 更新が必要で Quick タスクの粒度を超える。**Deferred**: 別 Todo として `MODEL_ALIASES` の config.yaml 化、モデル別メトリクス記録とセットで再検討する。
- **`langgraph_handler.py` 側で吸収:** 当初 Todo の想定。Canvas iframe AI は `iframe_rpc_handler` を通るため本経路とは無関係。langgraph_handler にも `claude-sonnet-4.5` ハードコードが残っている可能性があるが、影響範囲が広く本 Quick のスコープから除外 (Deferred)。
- **環境変数で既定モデルを指定:** シンプルだが、Canvas アプリごとに使い分けたい要件に合わず却下。
- **opus エイリアスを含める:** 当初 Todo は haiku/sonnet/opus を挙げていたが、`opus` に対応する実モデル ID がリポジトリ内で使用実績なし。未検証のモデル ID をホワイトリストに入れるとランタイムエラーの温床になるため除外。
- **Silent fallback（未知モデル → 既定へフォールバック）:** エラーを出さずに続行する案。Canvas アプリ開発者がタイプミスに気づけず、想定と違うモデルが裏で使われる事故が起きるため不採用。明示的なエラーで拒否する方針に統一。

## Consequences

### Positive
- Canvas アプリ開発者がアプリの性質に応じて `haiku`/`sonnet`/`gpt-4.1` を選択できるようになり、コスト・速度・精度のトレードオフを取れる。
- 既定が Haiku になったことで、従来の全 Canvas アプリ共通コストを削減。
- `MODEL_ALIASES` 方式により、将来実モデル ID が変わってもホワイトリスト 1 箇所の更新で済む。
- 未知モデル指定は明示的エラーになるため、Canvas アプリ側のデバッグが容易。
- CANVAS_SYSTEM_PROMPT 更新により、AI が新規 Canvas アプリを生成する際にモデル指定を自然に使えるようになる（次回 FastAPI 起動時に `_canvas_system_` Gem が自動上書きされる）。
- クライアント `ai()` の後方互換を維持したため、既存 Canvas アプリは改修なしで動作し続ける。

### Gotchas / 注意点
- **`MODEL_ALIASES` はコード定数:** 新しいエイリアスを追加するには `iframe_rpc_handler.py` を編集してデプロイする必要がある。config.yaml 化は Deferred。
- **既定モデルの挙動変更:** 今までモデル指定なしで `ai()` を呼んでいた既存 Canvas アプリは、マージ後は Sonnet 相当から **Haiku に既定が変わる**。複雑な推論を前提にしていたアプリは明示的に `{ model: 'sonnet' }` を指定する必要がある。Canvas アプリ数が少ないうちに切り替えるのが前提。
- **`langgraph_handler.py` 側のハードコード未是正:** 本 Quick では `iframe_rpc_handler` 経路のみ修正した。`langgraph_handler.py` などに類似のハードコードがある場合、そちらは別タスクで対応が必要 (Deferred)。
- **CANVAS_SYSTEM_PROMPT の upsert タイミング:** `app/api/main.py` の lifespan で起動のたびに Canvas 専用 Gem を最新化する実装。本 ADR の更新はデプロイ（FastAPI 再起動）後に反映される。既に作成済みの Canvas アプリのシステムプロンプトは個別に更新されない点に注意。
- **モデル ID 直指定の互換性:** 現在ホワイトリスト化された `claude-haiku-4-5-20251001` / `claude-sonnet-4-6` / `gpt-4.1` の ID が Copilot SDK のモデル ID 変更などで将来失効した場合、エイリアスと実 ID 両方が壊れる。ホワイトリストを 1 箇所に集約してあるので対応は容易。
- **`canvas_apps.default_model` が未実装:** アプリ単位のデフォルトモデル永続化は Deferred。当面はアプリの JavaScript 内で `ai(prompt, { model: 'sonnet' })` を毎回指定するか、アプリ冒頭で `const DEFAULT_MODEL = 'sonnet'` として使い回す運用になる。
