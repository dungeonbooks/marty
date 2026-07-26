---
applyTo: "**"
---

# Review instructions

## Review only this PR's own diff

Review the changes between this PR's head and **its own base branch**, not
against `main` and not against the cumulative state of a stack.

This repo uses stacked PRs (Graphite). A branch's base is usually another open
PR, so the surrounding files contain changes that belong to a different PR.
Those are not part of this diff and must not be commented on.

Before raising a point, confirm the code you are describing exists on this
branch. Do not infer it from a sibling branch, a later PR in the stack, or a
`.env.example` / docs file that a different PR edits. If the claim is about
something being removed, added, or renamed, check that this diff is what did it.

## Verify before claiming

Do not report a missing guard, missing exception type, or missing check without
reading the surrounding function first. Prefer quoting the line you are
objecting to.

If you are not confident the issue is real on this branch, say so explicitly
rather than stating it as fact.

## Scope

Worth raising:

- Logic errors, off-by-one, wrong operator, incorrect boundary
- Silent failure paths: swallowed exceptions, unreachable branches, results
  returned without the guarantee the function documents
- Tests that cannot fail, or that assert something other than what their name
  claims
- Resource growth without a bound, and cache keys that can collide
- Security issues in input handling or credential use

Not worth raising:

- Formatting, import order, quote style. `ruff` and `ruff format` gate these in
  CI and pre-commit.
- Requests for more test coverage on a PR that is not about tests, unless the
  change is untested and risky. Coverage gaps are tracked separately.
- Restating what the diff does without identifying a problem.
- Docstring or comment wording, unless it contradicts the code's behaviour.

## Conventions

- Python 3.13, `str | None` over `Optional[str]`, `pathlib.Path` over `os.path`
- `uv` for dependencies, `just` for commands
- Async for I/O
- `structlog` with keyword context for new log calls in `src/`. Note that not
  every module has been migrated; match the logger the module already binds.
- Comments explain why, not what. Self-documenting code is preferred over a
  comment restating the line.
