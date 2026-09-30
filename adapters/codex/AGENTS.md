# AGENTS.md rules block — for any harness that reads `AGENTS.md`

> This file is the `AGENTS.md` variant of `adapters/claude-code/SKILL.md`.
> `AGENTS.md` is a de-facto convention read by several coding agents
> (Codex among them; Claude Code also honours it, depending on version —
> **verify for yours**). Keep the block short: it is loaded every session, so
> every line costs context forever.
>
> Usage: copy the block below into the project root `AGENTS.md`, or paste it
> into the constitution you already keep.

---

## Agent Covenant (non-negotiable)

**Division of labour.** The agent that writes code never approves it. If you
authored a change, you are not its reviewer — say so instead of quietly
self-certifying.

**Definition of done.** A task is done when:

1. `verdicts/<id>.verdict.json` exists, and
2. `python tools/gate.py --verdict-dir verdicts --require <id>` exits `0`.

Exit `1` means a real violation. Exit `2` means the command was misconfigured —
that is *not* a pass, and *not* something to paper over.

**Task cards.** Before non-trivial work, write a card from
`templates/TASK.md`, renamed to `<NS>-YYYYMMDD-NNN.md` (`<NS>` = your namespace
token, 2–6 uppercase letters). Bare `TASK-N` filenames are non-conformant: two
agents can legitimately hold the same bare number, and the resulting collision
produces a confident review of the wrong artifact. See `postmortems.md` §PM-1.

**Acceptance criteria must be executable.** "Works well" is inadmissible. Write
"pytest exits 0", "gate exits 0", "row count == 21", "no TODO in the diff". Each
criterion becomes an evidence string in your verdict.

**Handover.** When you pass work to another agent, hand over the **absolute
path** of the card and say "read this first". A bare task id is ambiguous across
agents and is the single most expensive mistake in this protocol.

**Failure honesty.**

- An input you cannot read is a *finding*, not a skip. A verifier that crashes on
  hostile input is not a verifier (`postmortems.md` §PM-6).
- If you cannot finish, emit a blocking question or a FAIL verdict. Absent output
  is never success.
- Never write a verdict you did not actually check, and never let a missing
  verdict default to "approved".

**Cleanup.** Cards reach `GATED`, then get archived or deleted within a working
day. Only conclusions persist: decisions go to an ADR (with a revisit-trigger),
durable lessons go to your knowledge surface, process chatter is deleted.

**Conformance honesty.** State your level: L0 unstructured, L1 carded, L2 gated
with the gate in CI. If a human clicks "approve" in the loop, you are at L1 —
say L1. Overstating the level is the failure mode this whole project exists to
prevent.

---

*Protocol: `PROTOCOL.md` · Rationale: `postmortems.md` · Checker: `tools/gate.py`,
`tools/lint_cards.py`*
