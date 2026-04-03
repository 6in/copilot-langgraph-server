Create an Architecture Decision Record (ADR) in `docs/adr/`.

## Steps

**1. Determine the next ADR number**

```bash
ls docs/adr/*.md 2>/dev/null | grep -oP '\d+' | sort -n | tail -1
```

Next number = last number + 1 (zero-padded to 4 digits, e.g. `0001`). If no files exist, start at `0001`.

**2. Get the title**

If `$ARGUMENTS` is non-empty, use it as the title.
Otherwise ask: "What is the decision title? (e.g. 'Use nginx prefix-strip for URL routing')"

**3. Ask for context interactively**

Use AskUserQuestion for each section. Keep it conversational — one question at a time:

- **Context**: "What problem or situation prompted this decision?"
- **Decision**: "What was decided? (the chosen approach)"
- **Alternatives considered**: "What other options were considered? (or skip)"
- **Consequences**: "What are the key consequences — positive and negative?"
- **Status**: offer options — Accepted / Proposed / Deprecated

If the user provides enough context in $ARGUMENTS or naturally answers multiple sections at once, skip redundant questions.

**4. Write the file**

Filename: `docs/adr/NNNN-<slugified-title>.md`

Template:
```markdown
# NNNN. <Title>

**Date:** YYYY-MM-DD  
**Status:** <Status>

## Context

<context>

## Decision

<decision>

## Alternatives Considered

<alternatives or "None documented">

## Consequences

<consequences>
```

**5. Commit**

```bash
git add docs/adr/NNNN-<slug>.md
git commit -m "docs(adr): NNNN - <title>"
```

Report: `Created docs/adr/NNNN-<slug>.md`
