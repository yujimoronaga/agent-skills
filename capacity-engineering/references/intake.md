# Stage 1 Intake — capacity QA form

Ask these **one at a time** (see SKILL.md Stage 1 step 2), in this order, starting with the architecture. Pre-fill from the request and from any infra code in the repo, and skip what's already answered.

```
1. Architecture: infra code path (Terraform/CDK/SAM/serverless.yml…), diagram, link, or a chain like
   "CloudFront → API Gateway → Lambda → RDS Postgres, + SQS → worker Lambda"
2. What does the system do? (one sentence)  [skip if obvious from 1]
3. Cloud / region / account: shared with other apps?  [default: AWS, single region, account shared]
4. Load today: average and peak req/s or users  [default: unknown → model 3 scenarios]
5. Load target: peak to handle, plus 12-month growth  [default: 10× today]
6. Spikes: launches, cron jobs, email blasts? How sharp?  [default: 4× peak within 1 min]
7. Per request: step durations, DB queries / downstream calls  [default: typical values, marked as assumptions]
8. Performance targets: p95 latency, error rate  [default: p95 < 1s, errors < 0.1%]
9. Third-party APIs and their tiers  [default: none]
10. Can I query real quotas read-only? yes / no  [default: no]
11. Mode: review only / full loop (fixes + load tests)  [default: review only]
12. Budget ceiling at peak  [default: none given]
13. Anything you already suspect will break?  [default: none]
14. Output: one HTML file (live diagram + every variable editable + full report) / Markdown / both  [default: one HTML file]
15. Max loops: council rounds and fix/check rounds before stopping to ask you  [default: 3]
16. Model per stage  [default: the current model for every stage]
```

## Handling answers
- Save them verbatim to `.capacity/intake.md`.
- Q4/Q5 unknown: build three scenarios (expected, 10× expected, launch spike) and say they're assumptions.
- Q6 sets the burst scenario. Burst behaviour often fails before steady-state does: scaling rate, cold starts, connection storms.
- Q7 unknown: use typical durations (DB query 5–20ms, Lambda handler 100–500ms, LLM call 2–30s), each tagged `[ASSUMPTION]` in `model.json` notes.
- Q3 "shared account": ask what else uses the shared limits, or record a `baseline` placeholder and flag it as a risk.
- Q15 sets `max_loops:` in state.md.
- Q16 sets `models:` in state.md (see SKILL.md § Models per stage). Skipped means the current model for every stage.
- Q14 sets the deliverable format (see SKILL.md § Output format). If the user skips it, use (a).
- Q10 = yes: still show each command before running it.
