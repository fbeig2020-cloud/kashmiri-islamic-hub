# STORY-013 — Establish content approval and audit trail

As a content manager, I want to ensure all content goes through an approval process and is logged, so that we maintain quality and accountability.

**Release:** r0 · Initial Setup and Basic Content Creation (weeks 0–1)
**Owner:** content_manager
**Blocked by:** nothing — you can start this now

## The requirement this satisfies

- **REQ-011** (Safety, must) — The system must flag content generation and analysis for human review when uncertain.

## How to build it

Implement an approval workflow for video scripts with logging to the audit trail. Ensure all actions are recorded in the audit log table.

## Failure paths you must handle

- Approval request not logged
- Audit trail entry missing
- Approval status not updated

## Where this fits

**Workspace:** Content Approval Dashboard · approve

## Acceptance — your stop condition

Tick each box as it genuinely passes. This file is yours — the platform reads
the same criteria out of `.colaberry/progress.json`, which Claude Code keeps in
step (see the managed block in CLAUDE.md). Ticking something you have not
actually met only misleads you.

- [ ] Given a new video script is generated, When it is flagged for review, Then it must be approved by a content manager before publication.
- [ ] Given a video script is approved, When it is published, Then an entry is created in the audit log with the approval details.
- [ ] Trust: Given a video script is flagged, When it is approved or rejected, Then the action is recorded in the audit trail.

When every box above is ticked, stop and show the demo.
