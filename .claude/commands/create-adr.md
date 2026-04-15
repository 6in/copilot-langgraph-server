Create an Architecture Decision Record (ADR) in `docs/adr/` by autonomously inferring the topic and writing the retrospective. Zero input required — Claude reads context and writes it all.

## Steps

**1. Determine the next ADR number**

```bash
ls docs/adr/*.md 2>/dev/null | grep -oP '^\d+' | sort -n | tail -1
```

Next number = last + 1, zero-padded to 4 digits. Start at `0001` if none exist.

**2. Infer the topic**

If `$ARGUMENTS` is non-empty, use it as the title hint.

Otherwise, infer from context — in priority order:

```bash
git branch --show-current          # branch name often describes the work
git log --oneline -10              # recent commits
cat .planning/todos/done/*.md 2>/dev/null | tail -40   # recently completed todos
```

Pick the most specific, meaningful topic. Prefer: recently completed todo title > branch name > last commit subject.

**3. Research autonomously**

Read as needed to reconstruct the *why*:

- `git log --oneline -20` — scope of recent work
- `git show` or `git diff` on relevant commits — what actually changed
- Relevant source files touched
- `docs/` for any design notes written alongside the work
- `.planning/quick/*/SUMMARY.md` or `PLAN.md` for recent quick tasks

Goal: answer "what problem existed, what was tried, what was chosen, and what would trip someone up later?"

**4. Write the ADR**

Filename: `docs/adr/NNNN-<slugified-title>.md`

```markdown
# NNNN. <Title>

**Date:** YYYY-MM-DD  
**Status:** Accepted

## Context

<What situation or problem prompted this decision. Be specific.>

## Decision

<The chosen approach, concisely stated.>

## Alternatives Considered

<Other approaches tried or evaluated, and why each was discarded. "None documented" if nothing was tried.>

## Consequences

<Positive and negative outcomes. Include gotchas and anything that would trip up a future reader.>
```

**5. Commit**

```bash
git add docs/adr/NNNN-<slug>.md
git commit -m "docs(adr): NNNN - <title>"
```

Report: `Created docs/adr/NNNN-<slug>.md`

## 6. patterns.md 更新リマインダ

ADR 作成・コミット後、パターンとして記録すべき設計判断が含まれていれば `.planning/patterns.md` にも手動で追記すること（D-15 / CLAUDE.md 参照）。

**追記ルール:**

- patterns.md は手動更新（自動生成しない）
- 1 パターンあたり 5-10 行: パターン名見出し + 要約 2-4 行 + 関連 ADR 相対リンク
- カテゴリは 7 種: `Auth` / `LangGraph・Graph` / `MCP・Tools` / `Worker・Jobs` / `Frontend・UI` / `Infra・Deploy` / `Data・Persistence`
- ADR にないパターンは追加しない（ADR が唯一の真実源 — D-08）
- ADR 番号を `.planning/adr-categories.yaml` にも追記する（primary + secondary カテゴリ）

**記載例:**

```markdown
### パターン名
設計判断の要約 2-4 行。具体的な挙動・採用理由・回避したい代替案を簡潔に記す。
関連 ADR: [NNNN](../docs/adr/NNNN-slug.md)
```

pre-commit hook が有効な環境では、次回コミット時に `docs/adr/INDEX.md` が自動で再生成される（`scripts/install-hooks.sh` でインストール済みの場合）。
