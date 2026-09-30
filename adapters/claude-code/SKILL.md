# Adapter: Claude Code

> Scope of this adapter: how to make Claude Code *follow* Agent Covenant when it
> is an **author** or a **reviewer** in your setup. This is documentation, not a
> runtime shim (PROTOCOL.md §10.4).

## 1. Capability facts

| Fact | Status |
|---|---|
| Reads a project-level `AGENTS.md` / `CLAUDE.md` at session start | widely documented; **verify against your version** |
| Has subagents (separate context, delegated tasks) | documented; names/flags change between versions — verify |
| Can read/write files in the project | yes |
| Ships a skill format with `name` + `description` frontmatter | yes in current versions; **field set is version-sensitive — verify before relying on extra keys** |

We deliberately do not assert exact CLI flags or plugin APIs here. They move
faster than this document. Check `claude --help` and the official docs for your
version and treat anything above marked "verify" accordingly.

## 2. Install

**Author role** — make the protocol part of the session's standing instructions:

1. Copy `adapters/claude-code/AGENTS.md` (this repo's `adapters/codex/AGENTS.md`
   is the same text; either works) to your project root as `AGENTS.md`, or
   append its "Rules" block to your existing `CLAUDE.md`.
2. Keep it short. A constitution nobody reads is a constitution that isn't applied.

**Reviewer role** — turn the protocol into a skill so it is only loaded when
reviewing:

```
.claude/
  skills/
    covenant-review/
      SKILL.md        ← copy templates/REVIEW.md structure into this
```

`SKILL.md` frontmatter (verify the required fields for your version):

```markdown
---
name: covenant-review
description: Produce an Agent Covenant verdict (REVIEW card + .verdict.json) for a
  task card. Use when asked to review, gate, or sign off on another agent's work.
  Do NOT use when authoring your own changes — independence rule R1.
---
```

The `description` is what the model sees when deciding to load the skill; write
it as an instruction with an explicit negative boundary, not as a label.

## 3. Operating procedure

**When Claude Code is the author:**

1. It writes the task card first: `templates/TASK.md` → rename to
   `<NS>-YYYYMMDD-NNN.md`.
2. Acceptance criteria must be commands/exit codes, not adjectives (§5).
3. It hands over the **absolute path** of the card. Never a bare id (N2).
4. It must not write its own review.

**When Claude Code is the reviewer:**

1. Trigger (human or upstream agent): *"Read `<abs-path>/<id>.md` in full, then
   write `REVIEW-<id>.md` and `verdicts/<id>.verdict.json`."*
2. The reviewer edits **no** author files.
3. The reviewer runs the acceptance commands and records the real exit codes.
4. Then `python tools/gate.py --verdict-dir verdicts --require <id>`.

## 4. Known limitations for this harness

- **The reviewer is a sibling subagent, not an independent party.** If the same
  session authored the change, the independence field is `false` and the gate
  blocks unless you pass `--allow-nonindependent`. Say so in the verdict rather
  than quietly marking `true`.
- **Self-review pressure is real** — a reviewer in the same conversation tends to
  grade generously. Put the review in a fresh session.
- **No automatic wake-up**: if your author and reviewer are separate sessions,
  something (human or script) must relay the path. See PROTOCOL.md §10.1.
- Subagent availability and naming differ by version; the *procedure* above holds
  regardless of how you spawn the review.

## 5. Minimal snippet

```markdown
## Agent Covenant (non-negotiable)

- Never approve your own work. Independence is a protocol field, not a feeling.
- A task is done when `verdicts/<id>.verdict.json` exists AND
  `python tools/gate.py --verdict-dir verdicts --require <id>` exits 0.
- Card ids are namespaced: `<NS>-YYYYMMDD-NNN.md`. Bare `TASK-N` names are invalid.
- When told to review, read the card by absolute path, produce the verdict pair
  (REVIEW card + verdict json), and do not touch the author's files.
- Unreadable input is a finding, never a silent pass.
```
