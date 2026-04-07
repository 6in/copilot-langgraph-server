---
phase: 17-debate-chat
fixed_at: 2026-04-07T16:02:20Z
review_path: .planning/phases/17-debate-chat/17-REVIEW.md
iteration: 1
findings_in_scope: 12
fixed: 11
skipped: 1
status: partial
---

# Phase 17: Code Review Fix Report

**Fixed at:** 2026-04-07T16:02:20Z
**Source review:** .planning/phases/17-debate-chat/17-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 12 (CR-01〜CR-04, WR-01〜WR-08)
- Fixed: 11
- Skipped: 1

## Fixed Issues

### CR-01: SSE ストリームエンドポイントに認証がない

**Files modified:** `app/api/routes/chat.py`
**Commit:** 2e67476
**Applied fix:** `stream_job` 関数のシグネチャに `payload: dict = Depends(get_jwt_payload)` を追加。JWT 未認証リクエストは 401 で拒否される。

---

### CR-02: ジョブステータスポーリングエンドポイントに認証がない

**Files modified:** `app/api/routes/jobs.py`
**Commit:** f18954d
**Applied fix:** `get_job` 関数に `payload: dict = Depends(get_jwt_payload)` を追加。`chat.py` から `get_jwt_payload` をインポート。不要な `HTTPException` インポートは追加せず。

---

### CR-03: `delete_thread` の ownership チェックが DB エラー時に無視される

**Files modified:** `app/api/routes/chat.py`
**Commit:** 2700442
**Applied fix:** `except Exception: pass` を `except Exception as e: raise HTTPException(status_code=503, detail="Service temporarily unavailable") from e` に変更。DB エラー時は ownership 確認なしに削除を継続しなくなった。

---

### CR-04: JWT blocklist がインメモリのみ — サーバー再起動でログアウト済みトークンが復活する

**Files modified:** `app/auth/jwt_utils.py`, `app/api/routes/chat.py`, `app/api/routes/auth.py`
**Commit:** 0fd5322
**Applied fix:**
- `jwt_utils.py` に `async_add_to_blocklist` と `async_is_blocked` を追加。Redis に TTL 付き（24h）でキーを保存し、Redis 障害時はインメモリ blocklist へフォールバック。
- `chat.py` の `get_jwt_payload` が `async_is_blocked` で Redis を確認するよう変更（`request.app.state.redis_client` を利用）。
- `auth.py` の logout が `async_add_to_blocklist` で Redis へ revoke するよう変更。既存の同期パス (`add_to_blocklist`) はフォールバックとして維持。

**Note:** ロジック変更を含むため `requires human verification` — Redis 接続エラー時のフォールバック動作を手動確認推奨。

---

### WR-01: CORS `allow_origins` が Vite dev server のみ — 本番で API が使えなくなる

**Files modified:** `app/api/main.py`
**Commit:** 2c3af22
**Applied fix:** `CORS_ORIGINS` 環境変数が設定されていれば JSON 配列としてパースして使用。未設定時は従来の開発用オリジンをデフォルト値として使用。

---

### WR-02: `rename_thread` が ownership チェックなしで任意スレッドを更新できる

**Files modified:** `app/api/routes/chat.py`
**Commit:** 6478184
**Applied fix:** UPDATE 文に `AND github_login = %s` を追加。`rowcount == 0` の場合は 404 を返す。JWT の `github_login` が一致しないスレッドは更新不可。

---

### WR-03: `DebateChatApp` の延長処理で `handleSend` がスタックした `currentTurn` を使うリスク

**Files modified:** `frontend/src/components/DebateChatApp.tsx`
**Commit:** db34828
**Applied fix:** `handleExtend` の先頭に `if (!activeThreadId) return;` ガードを追加。`activeThreadId` が null の場合は早期リターンして新スレッド作成を防ぐ。

---

### WR-04: `useChat` の polling fallback タイマーがクリアされない (memory leak)

**Files modified:** `frontend/src/hooks/useChat.ts`
**Commit:** 4558a70
**Applied fix:**
- `useRef<ReturnType<typeof setInterval> | null>(null)` で `fallbackTimerRef` を追加。
- `es.onerror` で `setInterval` の戻り値を `fallbackTimerRef.current` に格納。完了時に `clearInterval(fallbackTimerRef.current!)` で確実にクリア。
- `useEffect` の cleanup 関数でアンマウント時にタイマーをクリア。

---

### WR-05: `CanvasChatApp` の `initialThreadId` 処理で `setTimeout` を使ったレンダリング外の副作用

**Files modified:** `frontend/src/components/CanvasChatApp.tsx`
**Commit:** 466e280
**Applied fix:** render 本体の `if (initialThreadId && !initialSwitchDone.current)` ブロックを `useEffect(() => { if (initialThreadId) { switchThread(initialThreadId); } }, [])` に置き換え。`initialSwitchDone` ref も不要になったため削除。

---

### WR-07: `_load_code_agent` が `spec.loader` が `None` の場合に `AttributeError` が発生

**Files modified:** `app/orchestrator/agent.py`
**Commit:** 6743285
**Applied fix:** `spec_from_file_location` の直後に `if spec is None or spec.loader is None: raise ImportError(...)` チェックを追加。エラーメッセージが明確になり、`_INIT_FAILURE_TYPES` の `AttributeError` に紛れない。

---

### WR-08: `DebateHandler` で gem_ids の SQL プレースホルダーが手動構築されている

**Files modified:** `app/jobs/handlers/debate_handler.py`
**Commit:** f0501b7
**Applied fix:** 動的プレースホルダー構築 (`", ".join(["%s"] * len(gem_ids))`) を `WHERE gem_id = ANY(%s::uuid[])` に置き換え。`OrchestratorHandler` と同パターンに統一。`gem_id::text` キャストも追加。

---

## Skipped Issues

### WR-06: `app/api/main.py` の startup で DB マイグレーションと DDL が本番 `autocommit=False` 接続で走る

**File:** `app/api/main.py:53-208`
**Reason:** 本質的な解決策は Alembic への移行であり、コードの部分修正では対応できない。現在の実装は単一トランザクション内で DDL を実行し、最後に `await conn.commit()` を呼ぶため、エラー時はトランザクションがロールバックされてサーバー起動が失敗する（サイレント継続はない）。`CREATE INDEX CONCURRENTLY` は使用していないため現時点では実害なし。将来 Alembic 移行時に解決することを推奨。
**Original issue:** DDL をトランザクション内で実行しており、ロールバック処理がない。将来 `CREATE INDEX CONCURRENTLY` を使う場合に壊れる。

---

_Fixed: 2026-04-07T16:02:20Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
