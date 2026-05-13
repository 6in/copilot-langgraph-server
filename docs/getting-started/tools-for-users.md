# Tools for Users — AI が裏で使えるツール

利用者視点で「AI に何を頼めば、裏でどのツールが動くか」を整理したガイド。技術仕様 (引数・戻り値・サンドボックスヘルパー) は自動生成の [../mcp-tools.md](../mcp-tools.md) を参照。

> **このページの位置づけ:** mcp-tools.md は **what** (引数・戻り値) を網羅する技術ドキュメント、本書は **why / when** (どんなときに何を頼むか) を整理する利用者ガイド。両者は分業関係。

---

## ツール一覧 — ユースケース別

| ツール | こういう時に使われる (利用者視点の頼み方) | アプリ別利用可否 |
|--------|----------------------------------------|---------------|
| `ping` | 「MCP サーバー、生きてる？」 (基本は開発者向け診断) | Chat / SuperChat / Gem / Canvas / Debate |
| `web_search` | 「Tavily で最新情報調べて」「2026 年の◯◯動向を教えて」 | Chat / SuperChat / Gem / Canvas |
| `db_query` | 「users テーブル、何件ある？」「過去 7 日のジョブ数を集計して」 | Chat / SuperChat / Gem / Canvas |
| `get_current_datetime` | 「今日の日付は？」「明日の日付で予定立てて」 | Chat / SuperChat / Gem / Canvas |
| `attachments_list` | (内部呼び出し) 添付ファイル一覧を確認するために AI が自動で呼ぶ | Chat / SuperChat / Gem |
| `attachments_extract` | 「`report.pdf` の内容を要約して」「`data.xlsx` から数字抜き出して」 | Chat / SuperChat / Gem |
| `execute_python` | 「数列の標準偏差計算して」「JSON 整形して」「グラフ画像作って」 | SuperChat (`codeact` agent 経由) / Canvas |
| `claude_code` | 「Claude Code に◯◯のファイル作らせて」 (高権限、限定運用) | 利用シナリオ限定 (privileged) |

> **アプリ別の可否は agents/<name>/AGENT.md の `tools:` 宣言と、SubAgent ルーティングで決まる。**
> 例えば `general-assistant` は `tools:` に `execute_python` を含まないため Chat / SuperChat の通常会話では Python 実行できない。`codeact` agent に振られたとき (SuperChat) または Canvas 内 (iframe RPC 経由) でのみ Python 実行が走る。

---

## ユーザー視点のツール詳細

### web_search — Web 検索 (Tavily)

**頼み方の例:**
- 「LangGraph 2026 年の新機能を Web で調べて要約して」
- 「Tavily で『◯◯ ベストプラクティス』を調べて 3 件まとめて」
- 「最近の Python リリースノートを見て」

**裏で起きること:** Tavily API に検索クエリを投げ、上位結果のタイトル / URL / 整形済み本文 (最大 15 行) を取得。AI がそれを読んで要約・回答する。

**制約:**
- `TAVILY_API_KEY` が未設定だとエラーになる (.env で設定する)
- 戻り値の `content` は前処理済み (ナビ・フッター除去) だが、全文ではない。詳細が必要なら URL を辿る必要あり

### db_query — DB クエリ (SELECT 限定)

**頼み方の例:**
- 「`users` テーブルの登録月別ヒストグラム作って」
- 「過去 7 日でアプリ別のスレッド作成数を集計して」
- 「`gems` テーブルから type=canvas の Gem 一覧見せて」

**裏で起きること:** SELECT (または WITH) 文だけが PostgreSQL に対して実行される。プール名は `config/db_pools.yaml` で定義 (デフォルト: `default`)。

**制約:**
- **SELECT 専用ガード:** INSERT / UPDATE / DELETE / DDL は実行されない (拒否)
- プール接続のタイムアウト・最大同時接続数は `db_pools.yaml` で制御
- 大量レコードを取ると LLM のコンテキストを食うため、AI 側は LIMIT を付けて取りに行くことが多い

### attachments_list / attachments_extract — 添付ファイル参照

**頼み方の例:**
- 「`report.pdf` の内容を要約して」 → AI が `attachments_extract("report.pdf")` を呼ぶ
- 「会議の議事録 (添付) で決まったこと教えて」
- 「`data.xlsx` の合計金額を計算して」 → `attachments_extract` で抽出 → `execute_python` で集計 (`codeact` agent)

**裏で起きること:**
- `attachments_list`: スレッドに紐づく添付 (`kind: "user_upload"`) と worker 生成 (`kind: "generated"`) のファイル一覧を返す
- `attachments_extract`: 指定ファイル (PDF / docx / xlsx / pptx) を MarkItDown でテキスト抽出 (最大 50,000 文字、60 秒タイムアウト)

**対応形式:**
| 形式 | 扱い |
|------|------|
| 画像 (PNG / JPG / GIF) | LLM の multimodal で直接読まれる (Phase 36) |
| テキスト / コード (.txt / .py / .ts / .md) | 自動で会話コンテキストに展開 (Phase 36) |
| PDF / docx / xlsx / pptx | `attachments_extract` で抽出 (Phase 37) |
| その他バイナリ | `attachments_list` で名前だけ見える、`execute_python` / `claude_code` から bytes として読める (Phase 37) |

**エラーパターン (`error.code`):**
- `password` — PDF にパスワード保護がかかっている
- `corrupt` — ファイルが破損して開けない
- `size_over` — 抽出後のテキストが 50,000 文字を超える
- `unsupported` — 拡張子が対応外
- `extract_timeout` — 60 秒以内に抽出が終わらない

### execute_python — Python サンドボックス実行

**頼み方の例 (`codeact` agent 経由 / Canvas 内):**
- 「数列 [3, 7, 2, 8, 5] の平均と標準偏差を計算して」
- 「以下の JSON を整形して、`status=active` の項目だけ取り出して」
- 「フィボナッチ数列の最初の 20 項を出して」
- 「numpy で正弦波のサンプル値を 100 点生成して Markdown テーブルで」

**裏で起きること:** AST allowlist + 512MB + 60 秒タイムアウトでサンドボックス Python を実行、stdout / stderr / exit_code を返す。

**使用可能:** math / statistics / datetime / json / re / collections / itertools / functools / numpy / yaml / pydantic / mcp_helper / urllib
**使用不可:** os / subprocess / sys / shutil

> **Privileged ツール:** `tools:` への明示宣言が必要 (`codeact` agent と Canvas 内のみ)。Chat / 通常 SuperChat ルーティングでは呼ばれない。

### claude_code — Claude Code CLI 起動

**用途:** 限定的な運用 — AI に対し外部 Claude Code CLI をサブプロセスで起動させ、ファイル生成・コード実行を頼む。env サニタイズ + 60 秒タイムアウト + 4000 文字切り詰めの安全策付き。

**制約 (要注意):**
- **Privileged ツール** で広範な権限を持つため、`tools:` に宣言した SubAgent には WARNING が出る
- 現状、`spirit-room` 方式の認証バインドとセキュリティ改善が pending (todo `2026-04-16-improve-claude-code-mcp-tool-with-spirit-room-auth-binding.md`)

### get_current_datetime — JST 現在日時

**頼み方の例:**
- 「今日の日付教えて」 (Copilot SDK は時系列に弱いので明示的にこのツールが必要)
- 「明日の日付で予定組んで」 → AI が現在日時取得 → +1 日 → 表記

**戻り値:** `{"date": "2026-05-13", "time": "13:50:00", "weekday": "水曜日", "formatted": "..."}`

### ping — MCP サーバー疎通確認

主に開発者の診断用。利用者が直接呼ぶシーンは少ないが、`general-assistant` に「MCP 生きてる？」と聞くと裏で `ping` が走る。

---

## ツールが呼ばれる経路 — 3 つ

技術的にツールが実行される経路は 3 つあり、利用者の体感はだいたい同じだが裏側のグラフ構造が異なる:

1. **ReAct ループ (ToolEnabledSubAgent):** `general-assistant` など `tools:` を宣言した SubAgent が、思考 → ツール呼び出し → 観察 を交互に繰り返す。SuperChat / Chat の通常会話で発火する経路
2. **CodeAct (Plan → Execute → Observe):** `codeact` agent が `execute_python` を直接実行する経路 (Phase 28)。Plan コメント必須、1 ターンに 1 実行
3. **iframe RPC (Canvas):** Canvas 内の iframe アプリから postMessage 経由で MCP ツールを呼ぶ経路 (`iframe-rpc.js` ライブラリ)。Canvas アプリが独立したフロントエンドからツールを使う用

3 経路すべて **observability 基盤** (Phase 31) が trace を `agent_traces` テーブルに記録する。開発者は [../trace-query-recipes.md](../trace-query-recipes.md) のクエリでツール利用状況を集計できる。

---

## ツール追加・運用について (開発者)

ツール一覧は `config/mcp_tools.yaml` を **single source of truth** として管理する (Phase 30)。新規追加は:

```bash
/add-mcp-tool <name>
```

詳細は [../mcp-tool-add-manual.md](../mcp-tool-add-manual.md) を参照。

`config/mcp_tools.yaml` から以下が自動生成される:

- `mcp_server/tools/mcp_helper.py` (sandbox Python ラッパー)
- `static/js/tool-catalog-generated.js` (iframe RPC 用 JS カタログ)
- `docs/mcp-tools.md` (技術ドキュメント)

これらを手動編集すると pre-commit hook で drift が検知され commit がブロックされる。修正は YAML 編集 → `python3 scripts/generate_mcp_artifacts.py --target all` で再生成。
