---
phase: 19
slug: canvas-apps-app-id-iframe-phase-18-rpc
status: verified
threats_open: 0
asvs_level: 1
created: 2026-04-09
---

# Phase 19 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| 外部→GET /apps/{app_id} | 認証なし。app_id を知る任意ユーザーがアクセス可能 | Canvas アプリ HTML（公開コンテンツ） |
| iframe srcdoc→ブラウザ | Canvas アプリ HTML が sandboxed iframe で実行される | ユーザー生成 HTML |
| iframe→POST /api/iframe-rpc | JWT Cookie 認証あり（19-02で復活）。arq へ enqueue される | JSON-RPC リクエスト／結果 |
| parent-bridge.js→parent window | `e.source` で返信。targetOrigin '*' は srcdoc null origin への許容済みリスク | JSON-RPC レスポンス |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-19-01 | Information Disclosure | GET /apps/{app_id} 認証なし | accept | 社内ツール・200名規模。URL を知る者のみアクセス可能。将来フェーズで JWT チェック追加予定 | closed |
| T-19-02 | Tampering | srcdoc 属性注入（HTML エスケープ） | accept | srcdoc エスケープ実装済み（`"` → `&quot;`、`&` → `&amp;`）を SUMMARY.md で確認済み。コードレビューは現フェーズ対象外 | closed |
| T-19-03 | Elevation of Privilege | iframe sandbox 破壊 | accept | `sandbox="allow-scripts allow-forms"` のみ（`allow-same-origin` 除外）を UAT テスト3で確認済み。追加検証は将来フェーズ | closed |
| T-19-04 | Spoofing | POST /api/iframe-rpc JWT 削除後の不正利用 | mitigate | 19-02 でJWT Cookie 認証を復活。`auth_manager.load_token()` 方式を廃止し、呼び出し元ユーザーの JWT Cookie から github_token を取得 | closed |
| T-19-05 | Information Disclosure | DB app_id 列挙 | accept | UUIDv4（128bit）の app_id は予測不可能。列挙攻撃は現実的でない。レートリミットは将来フェーズ対象 | closed |
| T-19-06 | Denial of Service | 大量 GET /apps リクエスト | accept | 社内 200 名規模。レートリミットは現フェーズ対象外 | closed |
| T-19-07 | Spoofing | parent-bridge.js の postMessage 受信元偽装 | accept | origin 検証（`window.location.origin` または `'null'`）の実装を SUMMARY.md で確認済み。コード検証は将来フェーズ | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-19-01 | T-19-01 | GET /apps/{app_id} は認証不要。社内 200 名規模・URL 共有制御で十分と判断。将来フェーズで JWT 保護追加予定 | user | 2026-04-09 |
| AR-19-02 | T-19-02 | srcdoc エスケープは SUMMARY.md・UAT で動作確認済み。詳細コードレビューは現フェーズ対象外 | user | 2026-04-09 |
| AR-19-03 | T-19-03 | iframe sandbox 制限は UAT テスト3で確認済み（DevTools 目視）。自動検証は将来フェーズ | user | 2026-04-09 |
| AR-19-05 | T-19-05 | UUIDv4 app_id による列挙困難性で十分。レートリミットは将来フェーズで追加 | user | 2026-04-09 |
| AR-19-06 | T-19-06 | 社内ツール・200名規模のため DoS 対策は優先度低。将来スケールアップ時に対応 | user | 2026-04-09 |
| AR-19-07 | T-19-07 | postMessage origin 検証の実装は SUMMARY.md で確認済み。コード検証は将来フェーズ | user | 2026-04-09 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-04-09 | 7 | 7 | 0 | gsd-secure-phase (user accepted) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-04-09
