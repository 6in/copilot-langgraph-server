---
quick_id: 260514-djz
slug: copilot-auth-friendly-error
date: 2026-05-14
branch: quick/260514-djz-copilot-auth-friendly-error
---

# Quick: Copilot OAuth トークン失効を friendly に検知

## Trigger

PROD で SuperChat 利用中に `Error: No generations found in stream.` が表示された。
worker ログを追うと真因は Copilot SDK の `Exception: Session error: Execution failed: Error: Session was not created with authentication info or custom provider` で、これは GitHub OAuth `ghu_` トークンが GitHub 側で無効化された状態だった (Device Flow は refresh token なし)。
ログオフ → 再ログインで復旧したが、ユーザーには原因不明のスタックトレース由来エラーが見えるだけだった。

参考: `.planning/notes/2026-05-13-no-generation-chunks-recovery-needs-full-restart.md` の「将来の改善案」セクション。

## Scope

`app/providers/copilot.py` 内のみ。frontend / handler / auth manager は触らない。

### Change 1 — `CopilotAuthExpired` 例外

- 新規例外クラス `CopilotAuthExpired(RuntimeError)` を追加 (モジュールトップレベル)
- 既定メッセージ: 「Copilot の認証セッションが無効になりました。一度ログアウトして再ログインしてください。」
- ヘルパー `_is_auth_expired(exc) -> bool` を追加 (SDK エラー文字列 `"Session was not created with authentication info"` をサブストリング判定)

### Change 2 — `_agenerate` / `_astream` の except で検知

両メソッドの `except Exception:` ブロックで:
1. 既存の `self._client.stop()` + `self._client = None` リセットはそのまま継続
2. `_is_auth_expired(exc)` が True なら `raise CopilotAuthExpired(cause=exc) from exc` に差し替え
3. それ以外は今まで通り `raise`

→ Handler 側の catch は変更しない。スタックトレース上の `Exception` が `CopilotAuthExpired` に変わるだけで、UI には「Copilot の認証セッションが無効になりました...」のメッセージが見える。

### Change 3 — `_astream` で SESSION_IDLE chunks=0 fallback

`on_event` 内の `SESSION_IDLE` 分岐 (現状 line 270-274):

```python
elif event_type == SessionEventType.SESSION_IDLE:
    if not has_deltas[0] and fallback_content[0]:
        loop.call_soon_threadsafe(queue.put_nowait, fallback_content[0])
    loop.call_soon_threadsafe(queue.put_nowait, None)
```

を以下に変更:

```python
elif event_type == SessionEventType.SESSION_IDLE:
    if not has_deltas[0]:
        if fallback_content[0]:
            loop.call_soon_threadsafe(queue.put_nowait, fallback_content[0])
        else:
            # 0-chunk fallback: Copilot SDK が ASSISTANT_MESSAGE_DELTA も
            # ASSISTANT_MESSAGE も emit せず SESSION_IDLE で終了するパターン
            # (典型例: OAuth token 失効で SDK subprocess が auth 拒否)。
            # generate_from_stream が ValueError を投げないよう friendly な
            # メッセージを 1 chunk yield してから完了させる。
            loop.call_soon_threadsafe(
                queue.put_nowait,
                "Copilot から応答が得られませんでした。"
                "一度ログアウトして再ログインしてください。",
            )
    loop.call_soon_threadsafe(queue.put_nowait, None)
```

### Out of scope

- UI への自動 logout 誘導 (frontend 変更なし)
- handler 側で `CopilotAuthExpired` を特別扱いして job status を `auth_expired` 等にする変更
- Copilot SDK の health probe を worker startup に追加
- `.planning/notes/2026-05-13-...` の TODO セクションのうち、上記以外の項目

## Tasks

| ID | Task | File |
|----|------|------|
| T1 | `CopilotAuthExpired` 例外 + `_is_auth_expired` ヘルパー追加 | `app/providers/copilot.py` |
| T2 | `_agenerate` の except で auth-expired を検知して raise 差し替え | `app/providers/copilot.py` |
| T3 | `_astream` の except で auth-expired を検知して raise 差し替え | `app/providers/copilot.py` |
| T4 | `_astream` の `SESSION_IDLE` で chunks=0 fallback を追加 | `app/providers/copilot.py` |
| T5 | `_is_auth_expired` の単体テスト (auth-expired と他のエラーの判定) | `tests/test_copilot_auth_expired.py` |

## Verification

- `pytest tests/test_copilot_auth_expired.py -q` が pass
- 全 unit test (`pytest tests/ -q`) が既存通り pass (regression なし)
- 手動: PROD 想定で `docker compose -f docker-compose.prod.yml restart worker` 後、次の auth エラーで友好メッセージが出ることを SuperChat で確認 (※ 復旧後のため自然な再現は難しい — token 失効は ad-hoc 再現できないので unit test に頼る)

## Commit Plan

1 コミットで完結:

```
feat(quick-260514-djz): Copilot OAuth トークン失効を friendly に検知

- CopilotAuthExpired 例外を追加し、SDK の "Session was not created with
  authentication info" を検知して raise を差し替え
- _astream で SESSION_IDLE 時 chunks=0 の場合に ValueError ではなく
  「再ログインしてください」メッセージを yield する fallback を追加
- _is_auth_expired の単体テスト追加

PROD で SuperChat 利用中に発生した No generations found in stream エラーの
ユーザー向け表示を改善する。真因は OAuth token 失効 (Device Flow は refresh
なし) で、検知後にログオフ→再ログインで復旧していた経緯がある。

Refs: .planning/notes/2026-05-13-no-generation-chunks-recovery-needs-full-restart.md
```
