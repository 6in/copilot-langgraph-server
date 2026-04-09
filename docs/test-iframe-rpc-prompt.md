# Canvas アプリ開発ガイド — iframe RPC API

Canvas アプリ（HTML）は、`window.RPC` ライブラリを通じて AI・DB などのバックエンド API を呼び出せます。
このライブラリは Canvas プレビュー時に自動注入されるため、**HTML 側でのスクリプト読み込みは不要**です。

---

## HTML テンプレート

新しい Canvas アプリを作る際の出発点として使えます。

```html
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Canvas App</title>
  <!-- $URL_PREFIX は Canvas プレビュー時に APP_PREFIX（例: /orochi）へ自動置換される -->
  <script src="$URL_PREFIX/iframe-rpc.js"></script>
  <style>
    /* ここにスタイルを記述 */
    body { font-family: sans-serif; margin: 0; padding: 16px; }
  </style>
</head>
<body>

  <!-- ここにコンテンツを記述 -->

  <script>
    // window.RPC はライブラリ読み込み後に利用可能（Canvas プレビュー時は自動注入でも補完される）

    // AI 呼び出し例
    async function askAI() {
      try {
        const res = await RPC.ai('こんにちは！一言で挨拶してください。');
        console.log(res.responseText);
      } catch (e) {
        console.error(e.message);
      }
    }

    // DB クエリ例（db_pools.yaml で設定済みのプール名を指定）
    async function queryDB() {
      try {
        const res = await RPC.query('default', 'SELECT current_timestamp AS now');
        console.log(res.rows);
      } catch (e) {
        console.error(e.message);
      }
    }
  </script>
</body>
</html>
```

### RPC API リファレンス

| メソッド | シグネチャ | 戻り値 |
|---------|-----------|--------|
| `RPC.ai` | `(prompt: string, timeoutMs?: number)` | `{ responseText: string }` |
| `RPC.query` | `(poolName: string, sql: string, timeoutMs?: number)` | `{ rows: object[] }` |
| `RPC.call` | `(method: string, params: object, timeoutMs?: number)` | `object` |

- エラー時は `Promise.reject(new Error(...))` — `try/catch` で処理する
- `RPC.ai` のデフォルトタイムアウト: 60秒、`RPC.query`: 30秒
- `RPC.query` は SELECT 文のみ有効（INSERT/UPDATE/DELETE は拒否される）

---

## 動作確認用テストアプリ生成プロンプト

以下をそのまま Canvas チャットに貼り付けると、RPC ブリッジの動作確認ツールを生成できます。

```
下記の HTML テンプレートをベースに、iframe RPC テストツールを作成してください。

window.RPC は自動注入済みなので import・fetch 不要です。
postMessage を直接扱う必要はなく、RPC.ai() / RPC.query() を呼ぶだけでOKです。

---

## ベーステンプレート

<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>iframe RPC テストツール</title>
  <style>
    body { font-family: sans-serif; margin: 0; padding: 16px; background: #f5f5f5; }
  </style>
</head>
<body>
  <script>
    // window.RPC は自動注入済み
  </script>
</body>
</html>

---

## 追加する機能

1. **AI テストパネル**（カード形式）
   - テキストエリア（デフォルト: "日本語で「テスト成功」と一言だけ答えてください"）
   - 「AIを呼び出す」ボタン — `RPC.ai(prompt)` を呼ぶ
   - 結果表示エリア（responseText を表示）
   - 実行中はボタン無効化 + ローディング表示

2. **QUERY テストパネル**（カード形式）
   - pool_name 入力（デフォルト: "default"）
   - SQL テキストエリア（デフォルト: "SELECT current_timestamp AS now, version() AS pg_version"）
   - 「クエリ実行」ボタン — `RPC.query(poolName, sql)` を呼ぶ
   - rows を JSON で整形表示

3. **ガードテスト**（カード形式）
   - 「INSERT を試みる（拒否されるはず）」ボタン
   - `RPC.query('default', 'INSERT INTO test_dummy VALUES (1)')` を呼ぶ
   - catch でエラーを受け取り "✅ 正しく拒否されました: {message}" と表示

4. **ログエリア**
   - 全 API 呼び出しのリクエスト/レスポンスをタイムスタンプ付きで記録
   - 「ログをクリア」ボタン

## デザイン要件
- 成功結果は緑背景、エラーは赤背景でハイライト
- 各パネルはカード（白背景 + 角丸 + 影）で区切る
- 外部ライブラリ不使用（vanilla JS + CSS のみ）
```

---

## 使い方

1. Canvas チャット（CanvasChatApp）を開く
2. 上記プロンプトをコピーして送信
3. 生成された HTML をプレビューで確認
4. 各パネルのボタンを押して RPC ブリッジの動作を検証
