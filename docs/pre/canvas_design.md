# Canvas 機能設計

## 概要

チャットで指示を出すと AI がシングルファイル HTML を生成し、エディタでプレビュー・修正しながら、そのままシステムにデプロイできる機能。

Gemini の Canvas 機能に相当するもので、通常の Gem の一種として実装する。

アプリの登録方法は3種類あり、すべて同じエディタ・デプロイ基盤を使う。

> **スコープ**
> 初期実装はシンプルなシングルファイル HTML の生成・デプロイに絞る。
> データベースアクセス・AI プロンプト連携は拡張フェーズで対応する。

---

## アプリの登録方法

```
canvas_apps
  ├─ source: "canvas"   → このシステムの Canvas（AI生成）
  ├─ source: "upload"   → 外部 AI や他ツールで作ったものをアップロード
  └─ source: "builtin"  → 組み込みツール（全ユーザー共通）
```

どの方法で登録したアプリも、**同じエディタ・プレビュー・デプロイ**の仕組みを使う。

---

## 役割分離

```
Canvas（作業場）
  → チャットで指示・エディタで修正・プレビューする場所
  → デプロイ前の作業環境

デプロイ済みアプリ（成果物）
  → 純粋なシングルファイル HTML
  → Canvas の UI は含まない
  → /apps/{id}/ で誰でも使える
  → [修正する] から元の Canvas スレッドに戻れる
```

デプロイ = Canvas から切り離してアプリ単体として公開する。
Canvas はあくまで編集環境であり、デプロイ先には含まれない。

---

## UI

### Canvas（AI生成）

```
┌─────────────────┬──────────────────────────────┐
│   チャット       │   エディタ / プレビュー        │
│                 │                              │
│ 「ボタンを赤に」 │  [エディタ] [プレビュー]       │
│                 │  ┌────────────────────────┐  │
│ [生成中...]     │  │  HTML編集 or iframe     │  │
│                 │  │  アプリが表示される      │  │
│                 │  └────────────────────────┘  │
│                 │  [デプロイ]                   │
└─────────────────┴──────────────────────────────┘
```

チャットで指示 → エディタで確認・修正 → デプロイ

### サイドバー

```
├─ Gem 一覧
├─ アプリ
│    ├─ [+ 新規作成（Canvas）]
│    ├─ [↑ アップロード]
│    ├─ ── 組み込みツール ──
│    │    ├─ MD ⇔ グリッド変換
│    │    └─ ...
│    └─ ── マイアプリ ──
│         ├─ 売上ダッシュボード（canvas）
│         └─ 勤怠集計ツール（upload）
```

---

## Gem との関係

Canvas は Gem の一種として扱う。`gems` テーブルの `type` で区別するだけ。

| type | 挙動 |
|---|---|
| `default` | テキスト回答 |
| `canvas` | HTML コード生成 + エディタ + デプロイ |

```sql
ALTER TABLE gems ADD COLUMN type VARCHAR NOT NULL DEFAULT 'default';
-- type: 'default' | 'canvas'
```

---

## データモデル

```sql
CREATE TABLE canvas_apps (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id   UUID REFERENCES threads(id),  -- upload/builtin は NULL
    user_id     VARCHAR   NOT NULL,
    name        VARCHAR   NOT NULL,
    html        TEXT      NOT NULL,            -- シングルファイル HTML
    source      VARCHAR   NOT NULL DEFAULT 'canvas',
                                               -- 'canvas' | 'upload' | 'builtin'
    deployed    BOOLEAN   NOT NULL DEFAULT FALSE,
    deployed_at TIMESTAMP,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);
```

スレッド毎に最新の生成 HTML を保持する。反復修正のたびに上書き更新する。
`upload` / `builtin` は `thread_id` が NULL になる。

---

## API

```
# Canvas（AI生成）
POST   /chat                        # コード生成（通常チャットと同じ口）

# アップロード登録
POST   /canvas/apps/upload          # HTML ファイルをアップロードして登録

# 共通操作
GET    /canvas/apps/{id}            # アプリ取得（エディタへの受け渡し）
GET    /canvas/apps?thread_id={id}  # スレッドの最新アプリ取得
PATCH  /canvas/apps/{id}            # HTML 編集・保存（エディタから）
POST   /canvas/apps/{id}/deploy     # デプロイ実行
GET    /apps/{app_id}/              # デプロイ済みアプリの表示（純粋な HTML のみ）
GET    /canvas/apps/{id}/source     # デプロイ済みアプリから元の Canvas スレッドに戻る
```

エディタは既存のものをそのまま使う。
`GET /canvas/apps/{id}` で HTML を受け取り、編集後は `PATCH /canvas/apps/{id}` で保存する。

---

## アップロード登録

```python
@app.post("/canvas/apps/upload")
async def upload_app(
    name:    str,
    file:    UploadFile,   # index.html
    user_id: str,
):
    html = (await file.read()).decode("utf-8")
    app  = await db.canvas_apps.insert({
        "user_id": user_id,
        "name":    name,
        "html":    html,
        "source":  "upload",
    })
    return {"app_id": app["id"]}
```

---

## Canvas Gem のシステムプロンプト

```python
CANVAS_SYSTEM_PROMPT = """
あなたはシンプルな Web アプリを生成するアシスタントです。
以下のルールに従って出力してください。

- 必ずシングルファイルの HTML で出力する
- 出力は ```html から始まるコードブロックのみとする（説明文は不要）
- 外部 CDN は利用可能（Tailwind CSS・Chart.js・Alpine.js 等）
- スタイルは HTML 内の <style> タグに記述する
- スクリプトは HTML 内の <script> タグに記述する
"""
```

---

## Worker 側の処理

通常チャットと同じフローに、HTML 抽出と `canvas_apps` への保存を追加する。

```python
# worker.py

async def process(job: dict):
    notifier  = build_notifier(job["reply_to"])
    llm       = await create_llm_for_user(job["user_id"])
    thread    = await db.threads.get(job["thread_id"])
    gem       = await db.gems.get(thread["gem_id"]) if thread["gem_id"] else None

    system_prompt = build_system_prompt(gem) if gem else None
    messages      = await build_messages(job, system_prompt)

    await notifier.progress("thinking")

    async for event in graph.astream({"messages": messages}):
        node_name = list(event.keys())[0]
        await notifier.progress(f"running:{node_name}")

    # Canvas Gem の場合は HTML を抽出して保存
    if gem and gem["type"] == "canvas":
        html = extract_html(final_result)
        app  = await db.canvas_apps.upsert({
            "thread_id": job["thread_id"],
            "user_id":   job["user_id"],
            "name":      gem["name"],
            "html":      html,
            "source":    "canvas",
        })
        result_payload = {"type": "canvas", "app_id": app["id"], "html": html}
    else:
        result_payload = {"type": "text", "content": final_result}

    # メッセージ保存 → JobStore 保存 → 完了通知
    await db.messages.insert(job["thread_id"], "user",      job["prompt"])
    await db.messages.insert(job["thread_id"], "assistant", final_result)
    await job_store.save_result(job["job_id"], result_payload)
    await notifier.done()


def extract_html(text: str) -> str:
    import re
    m = re.search(r"```html\n(.*?)```", text, re.DOTALL)
    return m.group(1).strip() if m else text
```

---

## デプロイ

登録方法（canvas / upload / builtin）に関わらず同じ処理。
**デプロイされるのは純粋な HTML のみ**。Canvas の UI は含まない。

```python
@app.post("/canvas/apps/{app_id}/deploy")
async def deploy_app(app_id: str):
    app = await db.canvas_apps.get(app_id)

    # 純粋な HTML のみを書き出す（Canvas UI は含まない）
    deploy_path = Path(f"./static/apps/{app_id}/index.html")
    deploy_path.parent.mkdir(parents=True, exist_ok=True)
    deploy_path.write_text(app["html"])

    await db.canvas_apps.update(app_id, {
        "deployed":    True,
        "deployed_at": datetime.now(),
    })

    return {"url": f"/apps/{app_id}/"}


@app.get("/canvas/apps/{app_id}/source")
async def get_source_thread(app_id: str):
    """デプロイ済みアプリから元の Canvas スレッドに戻る"""
    app = await db.canvas_apps.get(app_id)
    return {"thread_id": app["thread_id"]}  # NULL の場合は upload / builtin
```

nginx で `/apps/` を `./static/apps/` にマッピングするだけで配信できる。

```nginx
location /apps/ {
    alias /path/to/static/apps/;
    try_files $uri $uri/index.html =404;
}
```

---

## データフロー

```
【Canvas（AI生成）】
ユーザー指示 → POST /chat → キュー → Worker
  → HTML抽出 → canvas_apps保存（source: canvas）
  → notifier.done()
  → フロント：エディタに HTML を受け渡し
  → [デプロイ] → 純粋な HTML のみ /apps/{id}/ に公開
  → デプロイ済みアプリの [修正する] → 元の Canvas スレッドに戻る

【アップロード】
HTML ファイル → POST /canvas/apps/upload
  → canvas_apps 保存（source: upload）
  → エディタで確認・修正
  → [デプロイ] → 純粋な HTML のみ /apps/{id}/ に公開

【共通】
Canvas（作業場） ←→ GET / PATCH /canvas/apps/{id}  # エディタとの接続
デプロイ済み（成果物） → GET /apps/{app_id}/         # 純粋な HTML アプリ
修正したい場合  → GET /canvas/apps/{id}/source      # 元スレッドに戻る
```

---

## 拡張フェーズ（初期実装のスコープ外）

| 拡張 | 概要 |
|---|---|
| DB アクセス | 生成アプリから社内 DB を参照できる API を提供 |
| AI プロンプト連携 | 生成アプリ内から AI にプロンプトを投げられる API エンドポイントを提供 |
| バージョン管理 | 生成履歴を保持してロールバック可能にする |
| アプリ一覧管理 | デプロイ済みアプリを管理・公開設定できる画面 |

---

## ファイル構成

```
├── db/
│   └── canvas_apps.py     # canvas_apps の CRUD
├── worker.py              # Canvas 判定・HTML 抽出・保存
├── main.py                # アップロード・デプロイ API
└── static/
    └── apps/
        └── {app_id}/
            └── index.html # デプロイ済みアプリ
```
