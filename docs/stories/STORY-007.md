# STORY-007 — Distribute content to YouTube

As an educator, I want to distribute content to YouTube, so that I can reach a wider audience.

**Release:** r1 · Advanced Content Creation and Distribution (weeks 2–3)
**Owner:** AI System
**Blocked by:** STORY-005, STORY-006

## The requirement this satisfies

- **REQ-006** (Functional, must) — The system must develop content for YouTube and other social media platforms.
- **REQ-013** (Constraint, must) — The system must connect to YouTube for content distribution.

## How to build it

Integrate with YouTube API for content distribution.

## Failure paths you must handle

- Failed upload to YouTube
- Uploads are not logged
- System crashes during upload
- Incorrect video uploaded
- API integration fails

## Where this fits

**Workspace:** Content Distribution Dashboard · upload to YouTube

## Acceptance — your stop condition

Tick each box as it genuinely passes. This file is yours — the platform reads
the same criteria out of `.colaberry/progress.json`, which Claude Code keeps in
step (see the managed block in CLAUDE.md). Ticking something you have not
actually met only misleads you.

- [ ] Given a completed video, when ready, then it is uploaded to YouTube.
- [ ] Given a failed upload, when retried, then it succeeds or logs an error.
- [ ] Trust: All uploads are logged with status.

When every box above is ticked, stop and show the demo.
