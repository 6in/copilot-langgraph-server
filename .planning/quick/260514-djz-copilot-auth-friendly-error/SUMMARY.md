---
quick_id: 260514-djz
slug: copilot-auth-friendly-error
date: 2026-05-14
branch: quick/260514-djz-copilot-auth-friendly-error
status: complete
---

# Summary

## What changed

`app/providers/copilot.py` のみ変更:

1. **`CopilotAuthExpired` 例外** + ヘルパー `_is_auth_expired(exc) -> bool` を追加
   - SDK エラー文字列 `"Session was not created with authentication info"` をサブストリング判定
   - `__cause__` / `__context__` 連鎖もたどる (自己参照ループ防御あり)
   - 既定メッセージ: 「Copilot の認証セッションが無効になりました。一度ログアウトして再ログインしてください。」

2. **`_agenerate` / `_astream` の except** で auth-expired を検知し `CopilotAuthExpired` に raise 差し替え
   - 既存の `self._client.stop()` + `self._client = None` リセットはそのまま継続
   - 非 auth エラーは従来通り素通し

3. **`_astream` の `SESSION_IDLE` フォールバック** を拡張
   - 旧: `has_deltas=False` かつ `fallback_content=None` の時、queue に None だけ入れて完了 → `generate_from_stream` が `ValueError("No generations found in stream.")` を投げる
   - 新: 上記ケースで友好メッセージを 1 chunk yield してから None を入れる → UI には「Copilot から応答が得られませんでした。一度ログアウトして再ログインしてください。」が見える

## Verification

| 項目 | 結果 |
|------|------|
| 新規テスト `tests/test_copilot_auth_expired.py` | 9/9 passed |
| Copilot 関連既存テスト (`test_copilot_bind_tools.py`, `test_copilot_attachments.py`, `test_provider.py`) | 41/41 passed (regression なし) |
| 全テスト | 457 passed / 13 skipped / 2 xpassed / 4 errors (errors はすべて `test_install_hooks.py` の host 環境依存テストで本変更とは無関係) |

## Out of scope (未実施)

- UI への自動 logout 誘導 (`useChat.ts` などの frontend 変更)
- handler 側で `CopilotAuthExpired` を特別扱いして job status を `auth_expired` 等にする変更
- Copilot SDK の health probe を worker startup に追加

これらは UI 連携を伴う独立 phase として別途切り出す候補。

## Notes

- 真因 (OAuth `ghu_` 失効) は GitHub 側でしか再現できないため、本番動作確認は次回失効発生時を待つ
- Device Flow には refresh token が無いので、自動更新は原理的に不可能 — 検知＆再ログイン誘導が現実解
- 参考: `.planning/notes/2026-05-13-no-generation-chunks-recovery-needs-full-restart.md`
