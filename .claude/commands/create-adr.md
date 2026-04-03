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
