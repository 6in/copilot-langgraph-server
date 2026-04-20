# 0046. Phase 31 Integration Check retrospective — unit-test green でも surface しなかった silent failure 3 件

**Date:** 2026-04-20
**Status:** Accepted
**Related:** ADR-0045 (Phase 31 observability 基盤)

## Context

Phase 31 (agent-mcp-observability) の Plan 01–07 は unit test 60/60 green で完了した。しかし Plan 08 Wave 6 の docker compose 実環境での 4 経路 integration check を実施したところ、**unit test では一切 surface していなかった silent failure が 3 件**見つかった。いずれも observability 基盤そのものを無言で破壊する類のバグで、production に merge していたら「trace が出ない」「Canvas が timeout する」という後続調査で初めて気付く高コスト事象だった。

3 件の内訳:

1. **Python `logging` root level が WARNING default**: `logging.getLogger("trace")` に handler / level が未設定だったため `logger.info(json.dumps(...))` が silently drop。pytest の `caplog` fixture が内部で `set_level(INFO, logger="trace")` していたため test 側では INFO 出力が有効化され、実 env との差分を隠していた。
2. **LangGraph checkpointer state 復元 + `_keep_first` reducer**: `AsyncPostgresSaver` が thread_id 単位で state を checkpoint/復元。`context` フィールドに `_keep_first` reducer を使っていたため、同 thread で 2 回目のリクエストを投げると checkpointer が復元した**前回の RPCContext**を優先し、handler が渡す新 `correlation_id` が ignore された。結果、child span が前リクエストの trace_id を引き継ぎ trace isolation が壊れる。unit test は checkpointer なしで StateGraph を単発実行していたため再現しなかった。
3. **Route → arq enqueue → worker dispatch のシグネチャ不整合**: Plan 05 で iframe_rpc route が `correlation_id` kwarg を追加したが、arq job function `process_chat()` の signature 更新を忘れ、`TypeError: process_chat() got an unexpected keyword argument 'correlation_id'` で every job が即死。SSE で応答が返らず 30s client-side timeout。handler 直接呼びの unit test は通っていた。

Phase 31 Wave 6 の範囲で 3 件すべて発見・修正済み (`1ade308`, `f1a41f0`, `d9e0519`)。ただし **「なぜ unit test でこれらが surface しなかったか」** は構造的な問題であり、同じ失敗パターンが今後の phase でも再発する可能性が高い。整理と対策を ADR として記録する。

## Decision

以下 4 点を今後の全 phase に適用する規範として採択する:

### 1. **Integration check gate を全 phase で必須化**

`/gsd-execute-phase` の Wave 6 相当に「docker compose / 実環境 / 実 user 操作で end-to-end 1 経路を手動または自動で確認する」step を必ず含める。unit test の green を以って close しない。

- phase plan の最後の plan は `type: execute` + `autonomous: false` + `checkpoint: human-verify` とし、実操作と観察結果を SUMMARY.md に貼付
- 可能なら `chrome-devtools` MCP 経由で自動化するが、少なくとも 1 経路は人間が UI 操作してログを拾う
- 観察結果は `docs/phase-XX-integration-check.md` として必ず残す (他 phase からも参照可能)

### 2. **基盤系モジュール (logger / checkpoint / enqueue) は self-bootstrap で実環境動作を保証**

「`main.py` の lifespan で設定するはずだった」というタイプの silent failure を防ぐため、**module import 時に自己設定する self-bootstrap パターン** を採用:

```python
# app/observability/trace.py
logger = logging.getLogger("trace")

def _configure_trace_logger() -> None:
    if any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

_configure_trace_logger()
```

Idempotent かつ scope が限定 (root / uvicorn / arq logger は無変更) なので副作用リスク最小。arq worker / pytest / ad-hoc script のどこから import しても動く。

### 3. **契約テスト (contract test) を route → queue → worker → handler 経路に必ず追加**

複数層をまたぐ contract (kwarg 名 / task_type / job dict shape) は**単一の unit test が守れない**。以下を追加:

- `tests/test_worker_contracts.py` — route の enqueue 呼び出しと `process_chat()` signature の整合性を**import-time** に検証する。例えば `inspect.signature(process_chat).parameters` と route 側で使う kwarg set の subset 関係をアサート
- iframe_rpc / langgraph / orchestrator / debate の各 route ごとに contract テストを書き、kwarg 追加忘れを CI で検知

### 4. **LangGraph checkpointer 復元を想定した state reducer 設計ガイド**

`context` のような **request-scoped で fresh であるべき**フィールドを checkpointer に載せる場合、reducer は明示的に last-wins (新値優先) にする。first-wins 系の reducer は `messages` (accumulate) のような本当に加算が意図されるフィールドにのみ使う。

判断フロー:
- フィールドが request 単位で fresh であるべき → `lambda a, b: b if b is not None else a` (last-wins + None guard)
- フィールドが会話履歴のように累積する → `operator.add` または同等の reducer
- フィールドが (一度確定したら) immutable である → `lambda a, b: a` (first-wins) は許容、ただし unit test に**再 invoke シナリオ**を含める

本 ADR の採択をもって `app/orchestrator/state.py` の `AgentState.context` は **last-wins** に変更 (`f1a41f0`)。

## Consequences

### Positive

- Phase 32 以降、unit test が green でも integration check を通すまで phase を close しない規律が定着する
- silent failure (特に logger / checkpoint / enqueue 等の基盤層) が最終段で検出されて本番影響を防げる
- contract test により route の kwarg 変更時に worker 側の signature 更新忘れが CI で止まる
- self-bootstrap pattern により新しい module を追加した際も「logger 設定を main.py のどこに書くか」の議論を回避できる
- Phase 31 Wave 6 の retrospective が将来の planner / executor への教訓として形式知化される

### Negative

- phase 毎に integration check の operator cost (人間操作または chrome-devtools 自動化) が増える (経験的に 5–15 分/phase)
- contract test の追加で既存 route 変更のコストがわずかに上がる (新規 kwarg 追加時にテスト更新必須)
- reducer semantic の判断を要する feature 追加時に若干の認知負荷

### Neutral

- self-bootstrap pattern は Python ecosystem では一般的でないため、慣れていないレビュアーに「なぜ module level で handler 追加？」と聞かれる可能性 (docstring で理由を明記)
- LangGraph checkpointer の state 復元挙動は未だ公式ドキュメントに散在しており、reducer 選択基準がライブラリ側で明示されるまでは ad-hoc 判断が残る

## Alternatives Considered

- **Integration check を phase 外の CI に委ねる**: 手戻りコストが大きい。phase 内で close するのが合理的。
- **self-bootstrap せず main.py lifespan で logger 設定**: arq worker (別プロセス) や pytest や ad-hoc script から import したケースで設定が漏れる。self-bootstrap の方が頑健。
- **LangGraph の `context` を checkpoint から除外 (ephemeral field)**: 対応 API が LangGraph 側で提供されていないため現実的でない。reducer flip で対応。
- **契約テスト不要、route/worker は手動で同期**: Phase 18 以来 5 回類似ミスが発生 (過去 SUMMARY から grep)。手動同期は reliable でない。

## Links

- Phase 31 Integration Check report: `docs/phase-31-integration-check.md`
- Plan 31-08 SUMMARY: `.planning/phases/31-agent-mcp-observability/31-08-SUMMARY.md`
- Bug 1 fix commit: `1ade308` (`fix(31): configure trace logger stdout handler at import time`)
- Bug 2 fix commit: `f1a41f0` (`fix(31): flip _keep_first reducer to prefer fresh request context`)
- Bug 3 fix commit: `d9e0519` (`fix(31): thread correlation_id through process_chat to iframe_rpc_handler`)
- 関連 ADR: ADR-0045 (Phase 31 observability 基盤)
