---
status: resolved
trigger: "討論チャットを実行してもチャット履歴（スレッド）に保存されない"
created: 2026-04-06T00:00:00Z
updated: 2026-04-06T04:00:00Z
---

## Current Focus

hypothesis: CONFIRMED — applications テーブルに 'debate' レコードが存在しないため、threads テーブルへの INSERT が FK 制約違反で失敗している
test: app/api/main.py のシードロジックを確認 → 'chat' と 'superchat' のみシード、'debate' なし
expecting: main.py の applications シードに 'debate' を追加すれば修正できる
next_action: コンテナ再起動後に討論チャットを実行してスレッドが保存されるか確認

## Symptoms

expected: 討論ターンがスレッド履歴に残る（スレッド切り替え後も各ターンのメッセージが表示される）
actual: |
  - 履歴が空のまま
  - ターン表示はされるが保存されない（リアルタイム表示はOK）
  - サイドバーにスレッドが出ない
errors: エラーなし（ブラウザコンソール・サーバーログとも）
reproduction: /app から討論チャットを開き、テーマを入力して討論を実行する
started: Phase 17 実装後（前セッションで3バグ修正済み）

## Eliminated

- hypothesis: DebateHandler.run() がスレッドを作成・保存していない
  evidence: |
    debate_handler.py は直接 threads テーブルに書き込まない。
    threads への upsert は POST /api/chat エンドポイント (chat.py) が担う。
    chat.py の upsert コードは正しく app_id='debate' で INSERT を試みている。
  timestamp: 2026-04-06T00:01:00Z

- hypothesis: フロントエンドから thread_id が渡されていない
  evidence: |
    DebateChatApp.tsx の handleSend で createNewThread() を呼んで thread_id を生成し、
    sendMessage(text, threadId) に明示的に渡している。postChat の body にも正しく含まれる。
  timestamp: 2026-04-06T00:01:00Z

- hypothesis: app_id='debate' が POST /api/chat のボディに含まれていない
  evidence: |
    useChat に appId='debate' が渡され、postChat のボディに app_id: 'debate' として含まれる。
    chat.py の app_id ロジック: body.app_id が truthy なら使用 → 'debate' が使われる。
  timestamp: 2026-04-06T00:01:00Z

## Evidence

- timestamp: 2026-04-06T00:00:30Z
  checked: app/api/main.py — applications テーブルのシードロジック (68-74行)
  found: |
    INSERT INTO applications VALUES ('chat', 'Chat', ...), ('superchat', 'SuperChat', ...)
    ON CONFLICT DO NOTHING
    → 'debate' はシードされていない
  implication: applications テーブルに 'debate' レコードが存在しない

- timestamp: 2026-04-06T00:00:35Z
  checked: app/api/main.py — threads テーブルスキーマ (93-101行)
  found: |
    app_id TEXT NOT NULL REFERENCES applications(app_id)
    → threads.app_id は applications テーブルへの外部キー制約付き
  implication: |
    'debate' が applications に存在しない状態で threads に INSERT すると
    FK 制約違反 (psycopg.errors.ForeignKeyViolation) が発生する

- timestamp: 2026-04-06T00:00:40Z
  checked: app/api/routes/chat.py — threads upsert のエラー処理 (120-133行)
  found: |
    try:
        async with ... psycopg.AsyncConnection.connect(db_uri) as conn:
            await conn.execute(INSERT INTO threads ...)
            await conn.commit()
    except Exception:
        pass  # Non-fatal
  implication: |
    FK 制約違反例外が except Exception: pass で握り潰されるため、
    サーバーログにもエラーが出ず「エラーなし」という症状と一致する

- timestamp: 2026-04-06T00:00:45Z
  checked: apps/ ディレクトリ — APP.md の動的シード
  found: apps/chat/APP.md と apps/superchat/APP.md のみ存在。apps/debate/ は存在しない
  implication: 動的シードでも 'debate' は登録されない

## Resolution

root_cause: |
  applications テーブルに 'debate' レコードが登録されていないため、
  threads テーブルへの INSERT が app_id の外部キー制約違反で失敗する。
  エラーは except Exception: pass で握り潰されるため症状がサイレントになる。
fix: |
  app/api/main.py の applications シード INSERT に ('debate', 'Debate Chat', true, now()) を追加。
  ON CONFLICT DO NOTHING によりべき等。コンテナ再起動時に自動適用される。
verification: ユーザーによる手動検証で確認済み（討論チャット実行後にスレッドが保存されることを確認）
files_changed:
  - app/api/main.py
