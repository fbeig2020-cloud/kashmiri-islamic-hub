# STORY-001 — Generate AI-powered video ideas

As an educator, I want AI to generate video ideas, so that I can create engaging Islamic content.

**Release:** r0 · Initial Setup and Basic Content Creation (weeks 0–1)
**Owner:** AI System
**Blocked by:** nothing — you can start this now

## The requirement this satisfies

- **REQ-001** (Functional, must) — The system must generate engaging Islamic video ideas using AI.

## How to build it

Implement AI model to generate video ideas based on Islamic content themes.

## Failure paths you must handle

- AI generates irrelevant ideas
- AI fails to generate any ideas
- Generated ideas are not logged
- System crashes during idea generation
- Inappropriate ideas are not flagged

## Where this fits

**Workspace:** Content Creation Dashboard · generate ideas

## Acceptance — your stop condition

Tick each box as it genuinely passes. This file is yours — the platform reads
the same criteria out of `.colaberry/progress.json`, which Claude Code keeps in
step (see the managed block in CLAUDE.md). Ticking something you have not
actually met only misleads you.

- [ ] Given the AI system, when prompted, then it generates a list of video ideas.
- [ ] Given an inappropriate idea, when flagged, then it is removed from the list.
- [ ] Trust: All generated ideas are logged for review.

When every box above is ticked, stop and show the demo.
