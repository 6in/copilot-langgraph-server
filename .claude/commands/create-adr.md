Create an Architecture Decision Record (ADR) in `docs/adr/` by autonomously analyzing the codebase and git history. No interactive Q&A — Claude researches and writes the ADR itself.

## Steps

**1. Determine the next ADR number**

```bash
ls docs/adr/*.md 2>/dev/null | grep -oP '^\d+' | sort -n | tail -1
```

Next number = last + 1, zero-padded to 4 digits. Start at `0001` if none exist.

**2. Get the topic**

Use `$ARGUMENTS` as the decision topic/title. If empty, infer from recent git activity:

```bash
git log --oneline -10
```

**3. Research autonomously**

Gather context without asking the user. Read as needed:

- `git log --oneline -20` — recent work and scope
- `git show <hash>` or `git diff <base>..HEAD` — what actually changed
- Relevant source files touched in recent commits
- Existing docs (e.g. `docs/nginx.md`, `CLAUDE.md`) for design intent
- Any `.planning/quick/*/` SUMMARY.md or PLAN.md related to the topic

Goal: reconstruct the *why* — what problem existed, what was tried, what was discarded, what was chosen.

**4. Write the ADR**

Filename: `docs/adr/NNNN-<slugified-title>.md`

```markdown
# NNNN. <Title>

**Date:** YYYY-MM-DD  
**Status:** Accepted

## Context

<What situation or problem prompted this decision. Be specific — what broke, what was missing, what constraint existed.>

## Decision

<What was decided. The chosen approach, concisely stated.>

## Alternatives Considered

<Other approaches that were tried or evaluated, and why each was discarded. If nothing was considered, write "None documented".>

## Consequences

<Positive and negative outcomes. Include gotchas, constraints, and anything that would trip up someone reading this later.>
```

Write with a future reader in mind — someone who sees a piece of code and wonders "why is it done this way?"

**5. Commit**

```bash
git add docs/adr/NNNN-<slug>.md
git commit -m "docs(adr): NNNN - <title>"
```

Report: `Created docs/adr/NNNN-<slug>.md`
