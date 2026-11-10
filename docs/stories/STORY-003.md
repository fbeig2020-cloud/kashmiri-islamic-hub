# STORY-003 — Flag content for human review

As an educator, I want the system to flag uncertain content for review, so that I can ensure accuracy.

**Release:** r0 · Initial Setup and Basic Content Creation (weeks 0–1)
**Owner:** AI System
**Blocked by:** nothing — you can start this now

## The requirement this satisfies

- **REQ-011** (Safety, must) — The system must flag content generation and analysis for human review when uncertain.

## How to build it

Implement flagging mechanism for uncertain content and log review actions.

## Failure paths you must handle

- System fails to flag uncertain content
- Flagged content is not logged
- Review actions are not recorded
- System crashes during flagging
- Flagged content is not visible to reviewers

## Where this fits

**Workspace:** Review Dashboard · review flagged content

## Acceptance — your stop condition

Tick each box as it genuinely passes. This file is yours — the platform reads
the same criteria out of `.colaberry/progress.json`, which Claude Code keeps in
step (see the managed block in CLAUDE.md). Ticking something you have not
actually met only misleads you.

- [ ] Given a generated script, when uncertain, then it is flagged for review.
- [ ] Given a flagged item, when reviewed, then it is either approved or rejected.
- [ ] Trust: All flagged items are logged with reviewer actions.

When every box above is ticked, stop and show the demo.
