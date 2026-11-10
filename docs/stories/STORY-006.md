# STORY-006 — Design AI-generated thumbnails

As an educator, I want AI to design thumbnails, so that my videos attract viewers.

**Release:** r1 · Advanced Content Creation and Distribution (weeks 2–3)
**Owner:** AI System
**Blocked by:** STORY-004

## The requirement this satisfies

- **REQ-005** (Functional, must) — The system must design thumbnails for videos using AI.

## How to build it

Implement AI model to generate video thumbnails based on content themes.

## Failure paths you must handle

- AI generates inappropriate thumbnails
- Thumbnails are not logged
- System fails to save thumbnails
- Generated thumbnails are not flagged for review
- AI generates irrelevant thumbnails

## Where this fits

**Workspace:** Content Production Dashboard · design thumbnails

## Acceptance — your stop condition

Tick each box as it genuinely passes. This file is yours — the platform reads
the same criteria out of `.colaberry/progress.json`, which Claude Code keeps in
step (see the managed block in CLAUDE.md). Ticking something you have not
actually met only misleads you.

- [ ] Given a video, when processed, then the system generates a thumbnail.
- [ ] Given an inappropriate thumbnail, when reviewed, then it is flagged for redesign.
- [ ] Trust: All thumbnails are logged for review.

When every box above is ticked, stop and show the demo.
