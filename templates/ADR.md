# ADR-NNNN: <decision in one line>

- **Status:** proposed | accepted | superseded by ADR-NNNN
- **Date:** <YYYY-MM-DD>
- **Author:** <id>
- **Affects:** <projects / agents / paths>

## Context

What forced a decision. Include the constraint that made the obvious option
unacceptable (a budget, a failure, a hard dependency, a measured incident — see
`postmortems.md`). A reader who skips everything else should be able to stop here
and still know why.

## Decision

> The thing we decided, in the active voice: "We will …"

State what is decided, not what was considered. Alternatives belong below.

## Consequences

**Accepted costs** — what this makes harder or more expensive:

- <cost we knowingly took on>

**Gains** — what it buys:

- <capability or safety we did not have>

**Reversibility** — how to back this out if it turns out wrong:

- <the concrete undo>

## Alternatives considered

| Option | Why rejected |
|---|---|
| <option> | <one line> |

## Revisit-trigger  ← mandatory

A decision without a stated condition for reversal is a debt that accrues
interest silently. Fill this in before the ADR is accepted.

> Re-open this decision when **<observable condition>** — e.g. "the vendor's
> maintenance goes 6 months without a commit", "the migration cost is measured at
> > 2 days", "usage crosses N agents".

<!--
Why mandatory: a team that cannot say what would change its mind tends to keep
re-litigating the decision instead of acting on new evidence.
-->
