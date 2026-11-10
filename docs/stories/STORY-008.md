# STORY-008 — Analyze audience interests using AI

As an educator, I want AI to analyze audience interests, so that I can tailor content.

**Release:** r2 · Analytics and Audience Engagement (weeks 4–5)
**Owner:** AI System
**Blocked by:** STORY-007

## The requirement this satisfies

- **REQ-007** (Functional, must) — The system must use AI-powered analytics to understand audience interests.

## How to build it

Develop analytics module to process audience data and generate insights.

## Failure paths you must handle

- AI generates incorrect insights
- Insights are not logged
- System fails to analyze data
- Analysis results are not flagged for review
- AI generates irrelevant insights

## Where this fits

**Workspace:** Analytics Dashboard · analyze interests

## Acceptance — your stop condition

Tick each box as it genuinely passes. This file is yours — the platform reads
the same criteria out of `.colaberry/progress.json`, which Claude Code keeps in
step (see the managed block in CLAUDE.md). Ticking something you have not
actually met only misleads you.

- [ ] Given audience data, when analyzed, then the system provides insights.
- [ ] Given incorrect insights, when reviewed, then they are flagged for correction.
- [ ] Trust: All analysis results are logged for review.

When every box above is ticked, stop and show the demo.
