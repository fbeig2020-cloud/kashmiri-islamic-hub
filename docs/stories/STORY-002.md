# STORY-002 — Create AI-generated video scripts

As an educator, I want AI to create video scripts, so that I can produce content efficiently.

**Release:** r0 · Initial Setup and Basic Content Creation (weeks 0–1)
**Owner:** AI System
**Blocked by:** nothing — you can start this now

## The requirement this satisfies

- **REQ-002** (Functional, must) — The system must create scripts for Islamic videos using AI.

## How to build it

Develop script generation module using AI language models.

## Failure paths you must handle

- AI generates incomplete scripts
- Scripts are not logged
- System fails to save scripts
- Generated scripts are not flagged for review
- AI generates inappropriate content

## Where this fits

**Workspace:** Content Creation Dashboard · create scripts

## Acceptance — your stop condition

Tick each box as it genuinely passes. This file is yours — the platform reads
the same criteria out of `.colaberry/progress.json`, which Claude Code keeps in
step (see the managed block in CLAUDE.md). Ticking something you have not
actually met only misleads you.

- [ ] Given a video idea, when processed, then the system generates a script.
- [ ] Given an incomplete script, when reviewed, then it is flagged for human completion.
- [ ] Trust: All scripts are logged for review.

When every box above is ticked, stop and show the demo.
