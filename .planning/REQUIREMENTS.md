# Requirements: Copilot LangGraph Chat

**Defined:** 2026-03-31
**Core Value:** Copilot の JSON-RPC ベース SDK を LangChain 互換プロバイダーとして動かし、スレッド維持付きのチャット UI から使えること。

## v1 Requirements

### Auth

- [ ] **AUTH-01**: Device Flow で GitHub OAuth 認証を行い、Copilot トークン（`ghu_` prefix）を取得できる
- [ ] **AUTH-02**: 取得したトークンを Fernet で暗号化し、ローカルに保存・再起動後も再利用できる
- [ ] **AUTH-03**: トークン期限切れ時に UI 上で Re-authenticate ボタンを表示し、再認証フローを起動できる

### Provider

- [ ] **PROV-01**: `ChatCopilot`（`BaseChatModel` 継承）が LangGraph ノード内で `ChatOpenAI` と差し替え可能な形で動作する
- [ ] **PROV-02**: UI またはコンフィグで Copilot 提供モデル（gpt-4.1 等）を選択できる
- [ ] **PROV-03**: `CopilotClient` の start/stop ライフサイクルをアプリ起動・終了時に正しく管理する

### Graph

- [ ] **GRPH-01**: `MessagesState` + `add_messages` リデューサーで複数ターンの会話履歴を LangGraph 内で維持する
- [ ] **GRPH-02**: `thread_id` でセッションを分離し、新規チャット・履歴クリアに対応する
- [ ] **GRPH-03**: 将来のツール呼び出し・マルチノード拡張を見越した `StateGraph` 構成にする

### Chat UI

- [ ] **CHAT-01**: ユーザー・AI の発言を時系列で表示するメッセージ一覧を持つ
- [ ] **CHAT-02**: テキスト入力・送信ボタン・ローディング表示を含む送受信フローが動作する
- [ ] **CHAT-03**: AI 回答の Markdown およびコードブロックを整形レンダリングする
- [ ] **CHAT-04**: 新規チャットボタンで会話スレッドをリセットできる

## v2 Requirements

### Session Persistence

- **SESS-01**: チャット履歴を SQLite に永続化し、再起動後も閲覧できる
- **SESS-02**: サイドバーに過去のチャットセッション一覧を表示できる
- **SESS-03**: チャットセッションに名前を付けられる

### Provider Extensions

- **PROV-EXT-01**: ツール呼び出し（bind_tools / function calling）に対応する
- **PROV-EXT-02**: ストリーミング応答に対応する（SDK が対応次第）

## Out of Scope

| Feature | Reason |
|---------|--------|
| マルチユーザー対応 | 個人ツール。Redis トークンストアは不要 |
| ストリーミング応答（v1） | Copilot SDK Technical Preview では未サポート |
| ツール呼び出し（v1） | 拡張性考慮の設計はするが実装は v2 以降 |
| OAuth 以外の認証 | Device Flow で十分。PAT 直接指定は v1 対象外 |
| モバイル対応 | Web ブラウザ（PC）のみ対象 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-01 | Phase 1 | Pending |
| AUTH-02 | Phase 1 | Pending |
| AUTH-03 | Phase 3 | Pending |
| PROV-01 | Phase 1 | Pending |
| PROV-02 | Phase 3 | Pending |
| PROV-03 | Phase 2 | Pending |
| GRPH-01 | Phase 2 | Pending |
| GRPH-02 | Phase 2 | Pending |
| GRPH-03 | Phase 2 | Pending |
| CHAT-01 | Phase 3 | Pending |
| CHAT-02 | Phase 3 | Pending |
| CHAT-03 | Phase 3 | Pending |
| CHAT-04 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 13 total
- Mapped to phases: 13
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-31*
*Last updated: 2026-03-31 after initial definition*
