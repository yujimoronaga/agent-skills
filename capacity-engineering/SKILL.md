---
name: capacity-engineering
description: Run an architecture through a gated 4-stage capacity loop — Plan (QA intake of architecture + expected load), Fact-check (LLM Council verifies every service limit/quota and finds where it breaks, e.g. "Lambda concurrency caps at N, so the API fails at X req/s"), Code (mitigations + load tests), and Final Check (load-test evidence vs targets). Use when the user says "capacity engineering", "/capacity-engineering", "will this scale", "where will this break", "check limits/quotas/concurrency", or wants an architecture stress-reviewed before or after building. Works in Claude Code, GitHub Copilot (CLI / VS Code agent mode), Cursor, Codex and any agent that reads SKILL.md.
---

# Capacity Engineering

Same gated loop as `loop-engineering`. The difference is the question it asks at every stage: **at what load does each part of this architecture break, and what happens when it does?**

```
 ┌──────────────┐  wrong limits / unknown load  ┌────────────────┐
 │ 1. PLAN      │◄──────────────────────────────│ 2. FACT-CHECK  │
 │ arch + load  │──────────────────────────────►│ limits council │
 └──────────────┘                               └───────┬────────┘
        ▲                                               │ capacity model APPROVED
        │ design can't reach target                     ▼
 ┌──────┴───────┐        target missed          ┌────────────────┐
 │ 4. FINAL     │──────────────────────────────►│ 3. CODE        │
 │ load evidence│◄──────────────────────────────│ mitigations +  │
 └──────┬───────┘                               │ load tests     │
        │ all targets met with headroom         └────────────────┘
        ▼
      DONE
```

## Modes
- **Review only**: Stages 1–2 plus the capacity report. Use it for an existing system or a design on paper; no code changes. Pick this when the user only asks "will this scale?" or "where does it break?"
- **Full loop**: all 4 stages. Use it when the user wants fixes and load tests.
- **Inside loop-engineering**: when `loop-engineering` is running on a system with real load, run this skill's Stage 2 as an extra council member, and add its checklist items to that loop's checklist.

Ask which mode only if the request doesn't make it obvious.

State lives in `.capacity/` at the project root:

| File | Stage | Purpose |
|---|---|---|
| `.capacity/intake.md` | 1 | The user's answers, verbatim |
| `.capacity/model.json` | 1→2 | Components, limits, load (input to `scripts/capacity_calc.py`) |
| `.capacity/limits.md` | 2 | Every limit, with its source URL, the date checked, and whether it's adjustable |
| `.capacity/council.md` | 2 | Council rounds |
| `.capacity/report.md` | 2, 4 | Optional Markdown version of the report (template: `templates/capacity-report.md`) |
| `.capacity/simulator.html` | 2, 4 | **The deliverable**: one HTML file with simulator + report (template `templates/simulator.html`, built by `scripts/build_simulator.py`) |
| `.capacity/checklist.md` | 1, 4 | Targets plus mandatory capacity checks |
| `.capacity/state.md` | all | Stage, rounds, open issues, mode |

If `.capacity/state.md` exists, ask "Resume at <stage> or start over?"

---

## Stage 1 — PLAN (architecture + load intake)

1. **Planning engine**: use the host's native plan mode if it has one (Copilot `/plan`, Claude Code plan mode, Cursor plan mode). Plan modes are usually read-only, so write the `.capacity/` files after leaving it.
2. **QA intake, one question at a time**: the questions are in `references/intake.md`.

   **Ask one question at a time, QA style.**
   - Send a single question, wait for the answer, then send the next. Never send the whole form at once.
   - Start each question with its progress, e.g. `(3/14)`, and keep it to one or two lines.
   - Show the default in brackets, e.g. `[default: 3]`. If the user replies "skip", "default" or "you decide", use the default or your best guess and record it as an assumption.
   - Multiple-choice questions use the host's question tool if it has one (AskUserQuestion in Claude Code, the ask/choice UI in Copilot or Cursor), with the default as the first option. Otherwise list the options as `a / b / c`.
   - Skip any question the user's request, an earlier answer, or the repo already answers. Say in one line what you pre-filled, e.g. "From your Terraform: API Gateway → Lambda → DynamoDB".
   - Ask the most important question first: the architecture. It often answers several later ones.
   - If the user says "use defaults for the rest", stop asking and fill in every remaining answer with its default.
   - After the last question, show a short summary of all the answers and ask "Anything to change?" before planning.

   Pre-fill whatever is already known. If there's a repo, read the infrastructure code (Terraform, CDK, SAM, serverless.yml, k8s manifests, docker-compose, Bicep) and pre-fill the architecture from it.
3. **Draw the request path.** List every component a request touches, in order, including the hidden ones: DNS, CDN, WAF, load balancer, API gateway, compute, connection pool, database, cache, queue, third-party APIs, logging and metrics ingestion. Write it into `report.md` as a chain diagram.
4. **Build `model.json`** (format in `references/capacity-model.md`). Include `connects_to` for every call, `kind` for each component, `shared_id` for pools that several components draw on (such as account-wide Lambda concurrency), and `async: true` for queue and stream consumers. Every resource number the user could change (quotas, shards, per-shard concurrency, batch size, pool size, instance count…) goes in `globals` or `params`, and limits refer to them through formulas. Rules that aren't throughput limits (SQS visibility ≥ 6× timeout, queue delay after a spike vs the SLA, scale-up time, timeout chain) go in `checks`. Set `load_unit` when the load isn't requests (e.g. uploads/s, orders/s). Use the load figures from the intake. Fill limits from `references/limits-cheatsheet.md` as **provisional** values, marked `"verified": false`.
5. **Write the checklist** from `templates/checklist.md`:
   - **Targets**: one per load target the user gave, e.g. "500 req/s peak, p95 < 300ms, 0 errors at 2× peak burst".
   - **Mandatory capacity checks**: copied from `references/capacity-model.md`.

**Gate 1:** chain diagram + model.json + checklist exist, and peak load has a number. If the user doesn't know their load, propose three scenarios (expected, 10×, launch spike) and use all three.

---

## Stage 2 — FACT-CHECK (limits council)

### 2a. Verify every limit
Each limit gets a source; nothing comes from memory alone.
- **Account-specific values beat docs.** Default quotas differ per account and region, and new accounts often get lower defaults. If CLI access is available and the user agrees, query the real values. Commands are listed in `references/limits-cheatsheet.md`; all of them are read-only.
- Otherwise use official docs or web search, and record the URL and today's date.
- For each limit, record: value, scope (per function / account / region / partition / connection), hard or adjustable, and how it fails (throttle 429, queue, timeout, crash, data loss).
- Anything not verified stays `"verified": false` and is reported as a risk.

### 2b. Compute where it breaks
Run `python3 scripts/capacity_calc.py .capacity/model.json` (stdlib only). It reports, per component and per scenario: the demand it derives (with Little's law for concurrency), utilization, headroom, the **break point** (load at which the component hits 100%), and the **first component to fail**. If Python isn't available, do the same arithmetic by hand using `references/capacity-model.md`. `examples/serverless-api.json` is a worked example: API Gateway → Lambda → RDS breaks at about 218 req/s on DB connections, long before it reaches Lambda's concurrency limit.

### 2c. Council
If an **LLM Council** skill is installed, give it `report.md` + `model.json` + `limits.md`. Otherwise use the built-in council in `references/council.md`: a Limits Verifier, a Load Modeler, a Failure-Chain Analyst, and a Cost Auditor.

### 2d. Verdict and loop-back
The chair writes `council.md`: `APPROVED`, `APPROVED WITH CHANGES`, or `REJECTED`.
- A limit that turned out wrong, or a load assumption the council rejects → back to **Stage 1** to fix `model.json`, re-run the calculator, then re-check with a single delta reviewer.
- The design can't reach the target even with adjustable limits raised → back to **Stage 1** with a redesign proposal. The user decides.
- Cap: `max_loops` rounds (intake question, default 3).

### 2e. Capacity report (the main deliverable)
Fill `templates/capacity-report.md`. It must say plainly:
- **"It breaks here first"**: component, limit, the load at which it breaks, and what the user experiences when it does.
- The full break-point ranking, from weakest to strongest.
- Each fix, labelled as a quota increase (the user must request it), config, code, or redesign, with its effort and cost.

### 2f. Deliverable: one HTML file (intake Q14)
The final product is a **single self-contained HTML file**: the simulator and the full report in one page. Build it with `python3 scripts/build_simulator.py .capacity/model.json <out>.html`. The page contains:
- **Verdict**: what breaks first, at what load, and what users see. Plus the load slider and scenario buttons.
- **Architecture diagram**: boxes connected by arrows (`connects_to`), each labelled with the rate flowing in. Boxes are **green** under 70%, **amber** at 70–100% and **red** over the limit, and the first to break pulses with a "BREAKS FIRST · N/s" tag.
- **Selected component**: click a box to see each limit's formula, demand, utilization and break point, with sliders for all of its variables.
- **All variables & quotas**: every global and every component param in one grid, all editable. Examples: Lambda concurrency quota, API Gateway throttle, shards, parallelization factor per shard, batch size, reserved concurrency, max_connections, pool size, cache hit ratio, fanout, duration, timeout.
- **Report**: a break-point ladder; fixes with **Try it** buttons that apply their changes and show the new break point; the quota-request table for the user to file; warnings; limit sources with dates; assumptions.
- **Copy adjusted model.json**, so tuned values come back for the next round.

So that every resource variable is editable, model them as `globals`/`params` with formulas (see `references/capacity-model.md`). Don't hard-code numbers inside limits. Run `scripts/capacity_calc.py` on the same model and check that the HTML's first break point matches it before delivering.

Where to put it:
- **Host has an Artifact tool** (Claude app / claude.ai / Claude Code desktop): load the `artifact-design` skill first, build without `--standalone`, and publish as an Artifact (icon `chart`). Give the user the link.
- **Any other host** (Copilot, Cursor, Codex, plain CLI): build with `--standalone` to `.capacity/simulator.html`, and tell the user to open it in a browser, or open it yourself if the host has a browser tool.
- `.capacity/report.md` is only written if the user picks Markdown (Q14 b or c).

**Gate 2:** show the user the top 3 breakpoints and the proposed fixes. In review-only mode, stop here and deliver the report. In the full loop, ask "Apply these fixes and load test?"

---

## Stage 3 — CODE (mitigations + load tests)

- Apply the approved fixes in order of break point, weakest first. Typical fixes are in `references/capacity-model.md` § Mitigations: queue buffering, reserved/provisioned concurrency, connection pooling or a DB proxy, batching, caching, backoff with jitter, circuit breakers, DLQs, autoscaling settings, timeouts aligned along the chain.
- **Quota increases are the user's action.** Write each one as a ready-to-file request (service, quota name, current value, requested value, justification) in `report.md`. Never file one yourself.
- Write a load test for every target, in whatever tool the project already uses (k6, Locust, Artillery, JMeter, Gatling, `hey`/`wrk` for simple cases). Include: a steady peak, a burst at 2× peak, a soak if the user asked for one, and a ramp-to-failure test that confirms the predicted break point.
- **Never point a load test at production or a third-party API** without the user's explicit OK naming the target. Default to a staging or local environment, and mock third parties.

**Gate 3:** fixes applied, load tests written and runnable, and the target environment confirmed by the user.

---

## Stage 4 — FINAL CHECK

Run the load tests (with the user's OK on the target) and record the evidence in `report.md` § Results:
1. **Targets**: each one PASS/FAIL, with the measured RPS, p50/p95/p99 latency, error rate, and throttle count.
2. **Prediction vs reality**: did the system break where the model said, and at about the predicted load? If it broke somewhere else, the model is wrong: update `model.json` and add a note on what was missed.
3. **Mandatory capacity checks**: the list in `references/capacity-model.md`, including what happens to requests over the limit (queued, retried, or dropped?), retry storms, timeouts, DLQ, and alarms.

Loop-back:
- Target missed because of a defect or misconfiguration → **Stage 3**.
- Target unreachable with this design → **Stage 1**.
- Cap: `max_loops` rounds (intake question, default 3).

When load tests can't run (no environment, or no permission), mark the targets `PASS (modelled only)` and say so prominently. A model is not a measurement.

**Done** when no target is FAIL. Final report contents: the first breakpoint before and after the fixes, the headroom at peak, quota requests still pending on the user, and the remaining risks.

---

## Models per stage
The user can pick a model for each stage. **Default: every stage uses the model this session is running on.** Ask once, as the last intake question, and record the answer in `.capacity/state.md` as:
```
models:
  plan: current        # or e.g. opus / sonnet / haiku / gpt-5 / gemini-2.5-pro
  council: current     # one model for all members, or a list, one per member, e.g. [opus, sonnet, gpt-5, gemini-2.5-pro]
  code: current
  final_check: current
```
How to honour it:
1. **Same as the session model** (or `current`): run the stage here.
2. **Different model, and the host can start a sub-agent on a chosen model**, e.g. the Claude Code Agent/Task tool with `model`, GitHub Copilot custom agents with a `model:` field, or a Cursor background agent: give that stage to a sub-agent on the chosen model. Hand it the `.capacity/` files and this stage's instructions, then check its output against the stage gate yourself before moving on.
3. **Different model, and the host can't do that**: stop at the start of the stage and tell the user which model to switch to and how (`/model <name>` in Claude Code or Copilot CLI, or the model picker in VS Code / Cursor). Continue when they say so.
4. **Model not available on this host**: say so, suggest the closest one available, and wait for the user's choice. Never silently substitute.
5. Record the model that actually ran each stage in `.capacity/state.md`, and list it in the final report.

---

## Rules
- Update `.capacity/state.md` at every stage transition.
- Every limit has a source and a date. Limits change, so docs from memory are a starting point, never evidence.
- Separate **hard limits** (redesign needed) from **adjustable quotas** (ask the provider). Don't present a quota as a wall, or a wall as a quota.
- A component's capacity is the minimum over all its limits. Think of throughput, concurrency, connections, payload size, timeout, burst rate, and per-partition or per-key hot spots.
- Count every caller of a shared limit, such as account-wide Lambda concurrency or a shared DB connection pool, not just the service under review.
- Results are `PASS`, `PASS (modelled only)`, `PASS (risk)` (headroom under 30%), `FAIL`, or `N/A (reason)`.
- Run only read-only cloud commands, and only with the user's OK. Never change quotas or infrastructure in a live account during review.
