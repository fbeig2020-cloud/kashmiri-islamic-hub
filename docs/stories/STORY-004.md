# STORY-004 — Produce Quran and Hadith educational content

As an educator, I want AI to produce educational content, so that I can teach effectively.

**Release:** r1 · Advanced Content Creation and Distribution (weeks 2–3)
**Owner:** AI System
**Blocked by:** STORY-002

## The requirement this satisfies

- **REQ-003** (Functional, must) — The system must produce Quran and Hadith educational content using AI.

## How to build it

Use AI to generate educational content based on scripts and Islamic texts.

## Failure paths you must handle

- AI produces incorrect content
- Content is not logged
- System fails to produce content
- Produced content is not flagged for review
- AI generates inappropriate content

## Where this fits

**Workspace:** Content Production Dashboard · produce content

## Acceptance — your stop condition

Tick each box as it genuinely passes. This file is yours — the platform reads
the same criteria out of `.colaberry/progress.json`, which Claude Code keeps in
step (see the managed block in CLAUDE.md). Ticking something you have not
actually met only misleads you.

- [ ] Given a script, when processed, then the system produces educational content.
- [ ] Given incorrect content, when reviewed, then it is flagged for correction.
- [ ] Trust: All produced content is logged for review.

When every box above is ticked, stop and show the demo.
