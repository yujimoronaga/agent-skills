---
name: loop-engineering
description: Run a build task through a gated 4-stage engineering loop — Plan (QA-style intake), Fact-check (LLM Council review, loops back to Plan), Code, and Final Check against the MVP checklist plus mandatory checks. Use when the user says "loop engineering", "/loop-engineering", "run the loop", or asks to build a feature/app/tool and wants it planned, verified, and checked before it's called done. Works in Claude Code, GitHub Copilot (CLI / VS Code agent mode), Cursor, Codex and any agent that reads SKILL.md.
---

# Loop Engineering

A gated loop for building anything. No stage starts until the previous gate passes.

```
 ┌──────────────┐   gaps/contradictions    ┌───────────────┐
 │ 1. PLAN      │◄─────────────────────────│ 2. FACT-CHECK │
 │ (QA intake)  │─────────────────────────►│ (LLM Council) │
 └──────────────┘                          └──────┬────────┘
        ▲                                         │ APPROVED
        │ scope / design wrong                    ▼
 ┌──────┴───────┐       defects            ┌───────────────┐
 │ 4. FINAL     │─────────────────────────►│ 3. CODE       │
 │    CHECK     │◄─────────────────────────│               │
 └──────┬───────┘                          └───────────────┘
        │ all checks PASS
        ▼
      DONE
```

All loop state lives in a `.loop/` folder at the project root so any agent (or a later session) can resume:

| File | Written in | Purpose |
|---|---|---|
| `.loop/intake.md` | Stage 1 | The user's answers, verbatim |
| `.loop/plan.md` | Stage 1 | The plan (template: `templates/plan.md`) |
| `.loop/council.md` | Stage 2 | Council verdicts, each round appended |
| `.loop/checklist.md` | Stage 1, used in 4 | Acceptance checklist (template: `templates/checklist.md`) |
| `.loop/final-report.md` | Stage 4 | Pass/fail per item, evidence |
| `.loop/state.md` | Every stage | Current stage, iteration counts, open issues |

On start: if `.loop/state.md` exists, read it and ask the user "Resume at <stage> or start over?" Otherwise create `.loop/` and begin Stage 1.

---

## Stage 1 — PLAN

### 1a. Pick the planning engine
Use the host's native planning mode if it has one, otherwise plan inline:

| Host | Native planning |
|---|---|
| GitHub Copilot CLI | `/plan` (or Shift+Tab into plan mode) |
| GitHub Copilot in VS Code | Plan agent / "Plan" mode in the chat mode picker |
| Claude Code | Plan mode (EnterPlanMode / Shift+Tab) |
| Cursor | Plan mode |
| Anything else | Write `.loop/plan.md` directly from `templates/plan.md` |

The native mode produces the plan; this skill still owns the intake (below) and saves the result to `.loop/plan.md`.
Native plan modes are usually **read-only**: draft the plan there, then write the `.loop/` files once you've left plan mode. Don't treat the native "approve plan" step as Gate 2, because the council hasn't reviewed the plan yet.

### 1b. QA intake — one question at a time
The questions are in `references/intake.md`.

**Ask one question at a time, QA style.**
- Send a single question, wait for the answer, then send the next. Never send the whole form at once.
- Start each question with its progress, e.g. `(3/14)`, and keep it to one or two lines.
- Show the default in brackets, e.g. `[default: 3]`. If the user replies "skip", "default" or "you decide", use the default or your best guess and record it as an assumption.
- Multiple-choice questions use the host's question tool if it has one (AskUserQuestion in Claude Code, the ask/choice UI in Copilot or Cursor), with the default as the first option. Otherwise list the options as `a / b / c`.
- Skip any question the user's request, an earlier answer, or the repo already answers. Say in one line what you pre-filled, e.g. "From your Terraform: API Gateway → Lambda → DynamoDB".
- Ask the most important question first: what we're building (Q1). Then the architecture (Q2), which often answers several later questions.
- If the user says "use defaults for the rest", stop asking and fill in every remaining answer with its default.
- After the last question, show a short summary of all the answers and ask "Anything to change?" before planning.
- Save the answers verbatim to `.loop/intake.md`.

### 1c. Write the plan
Fill `templates/plan.md` into `.loop/plan.md`. Every assumption gets an `[ASSUMPTION]` tag so the council can attack it.

### 1d. Write the checklist
Fill `templates/checklist.md` into `.loop/checklist.md`:
- **MVP items** — one per MVP requirement, each with a concrete, testable pass condition. Anything measurable (speed, memory, size, load) gets a number, e.g. "peak RSS < 500MB on a 50MB file". "Measure it" alone is not a pass condition.
- **User-specific items** — anything the user said they care about (Q8 in intake).
- **Mandatory items** — copied from `references/final-check.md` (M1–M17), always included.

**Gate 1:** plan + checklist exist, no `TBD` left in required sections. → Stage 2.

---

## Stage 2 — FACT-CHECK (LLM Council)

Goal: independent reviewers try to break the plan *before* code exists.

### 2a. Choose the council
1. If an **LLM Council** skill/tool is installed (look for a skill named like `llm-council`, `council`), invoke it with `.loop/plan.md` + `.loop/intake.md` as input.
2. Otherwise run the built-in council in `references/council.md` (parallel subagents if the host supports them, sequential role-play if not; multiple models if the host lets you pick models).

### 2b. What the council checks
- **Facts**: library/API names, versions, limits, pricing, service quotas, syntax — verify against docs/web where tools allow. Anything unverifiable gets flagged, not assumed.
- **Fit**: does the plan actually deliver every MVP item and match the user's image/output?
- **Gaps**: missing error handling, auth, data, deployment, edge cases.
- **Contradictions**: between intake answers, plan, and checklist.
- **Over-build**: anything outside MVP that should be cut.

### 2c. Verdict and loop-back
The chair writes the verdict to `.loop/council.md`: `APPROVED`, `APPROVED WITH CHANGES`, or `REJECTED`, plus a numbered issue list (severity: blocker / major / minor).

- `REJECTED` or any **blocker** → go back to **Stage 1**, revise `plan.md` (and ask the user only the questions the council says only the user can answer). Re-run Stage 2.
- `APPROVED WITH CHANGES` → apply the changes to `plan.md`, note them in `council.md`, continue.
- `APPROVED` → continue.

Whenever council feedback adds or changes behaviour in `plan.md` (error handling, edge cases, exit codes…), add a matching item to `checklist.md` under "Plan behaviours". Otherwise Stage 4 never checks it.

Round 2 and later: run a single **delta reviewer** instead of the full council. It marks each earlier issue RESOLVED or NOT RESOLVED and looks only for new problems introduced by the revision. Re-run the full council only if the revision changed the architecture.

**Gate 2 — confirm with the user.** Show a short summary: what changed after council, remaining assumptions, final checklist. Ask: "Plan is confirmed by the council. Start coding?" Do not code until the user says yes (unless they said up front to run unattended).

Cap: `max_loops` council rounds (intake question, default 3). After the last one, stop and show the user the unresolved issues.

---

## Stage 3 — CODE

- Build exactly what `.loop/plan.md` says, in the task order listed there. MVP first; nothing out of scope.
- After each task: run it / test it, tick it in `plan.md`, update `.loop/state.md`.
- If you discover the plan is wrong mid-build (a fact was wrong, an API doesn't behave as expected): stop, log it in `state.md`, and go back to **Stage 1** for that piece only, then a mini council (Stage 2) on just the change.
- Write tests for every checklist item that can be tested automatically.

**Gate 3:** all plan tasks done, code runs, tests pass. → Stage 4.

---

## Stage 4 — FINAL CHECK

Walk `.loop/checklist.md` line by line and record evidence in `.loop/final-report.md` (template inside `references/final-check.md`):

1. **MVP / requested output** — every item, with proof: command run + output, screenshot, test name, file path.
2. **User-specific checks** — everything the user said they want checked.
3. **Mandatory checks** — the fixed list in `references/final-check.md` (runs, tests, security, secrets, errors, docs, matches the user's image, no leftover TODOs…).

Each item gets one of the results listed under "Rules that apply in every stage" below. "Looks fine" is not evidence.

### Loop-back
- Any `FAIL` that's a **defect** → back to **Stage 3**, fix, re-run Stage 4 (only the failed items + mandatory checks).
- Any `FAIL` caused by **wrong scope/design** → back to **Stage 1**, then Stage 2 on the change.
- Cap: `max_loops` final-check rounds (default 3), then report the remaining failures to the user.

**Done** only when no item is `FAIL`. Every `partial`, `risk` and `N/A` is explained in the report. Finish with a short report: what was built, how to run it, checklist results, assumptions still open, suggested next steps.

---

## Models per stage
The user can pick a model for each stage. **Default: every stage uses the model this session is running on.** Ask once, as the last intake question, and record the answer in `.loop/state.md` as:
```
models:
  plan: current        # or e.g. opus / sonnet / haiku / gpt-5 / gemini-2.5-pro
  council: current     # one model for all members, or a list, one per member, e.g. [opus, sonnet, gpt-5, gemini-2.5-pro]
  code: current
  final_check: current
```
How to honour it:
1. **Same as the session model** (or `current`): run the stage here.
2. **Different model, and the host can start a sub-agent on a chosen model**, e.g. the Claude Code Agent/Task tool with `model`, GitHub Copilot custom agents with a `model:` field, or a Cursor background agent: give that stage to a sub-agent on the chosen model. Hand it the `.loop/` files and this stage's instructions, then check its output against the stage gate yourself before moving on. A sub-agent's report isn't evidence: re-run its tests and read its diff.
3. **Different model, and the host can't do that**: stop at the start of the stage and tell the user which model to switch to and how (`/model <name>` in Claude Code or Copilot CLI, or the model picker in VS Code / Cursor). Continue when they say so.
4. **Model not available on this host**: say so, suggest the closest one available, and wait for the user's choice. Never silently substitute.
5. Record the model that actually ran each stage in `.loop/state.md`, and list it in the final report.

---

## Deliverable format (intake Q11)
The `.loop/*.md` files are always written, because they're the loop's working state. Q11 controls what the user receives in addition:
- **HTML page**: one page per gate. Gate 2 gets the plan, council changes, open assumptions and checklist. Done gets the final report with PASS/FAIL per item and its evidence.
  - Build it with `python3 scripts/build_report.py .loop <out>.html`. It renders every `.loop/*.md` file into one page, with a stage rail and run metadata, and colours PASS/FAIL/APPROVED/REJECTED. Run it again at every gate.
  - **Host has an Artifact tool** (Claude app / claude.ai / Claude Code desktop): build it without `--standalone` and publish it as an Artifact. Re-publish the same file at each gate so the link stays the same, and give the user the link.
  - **Any other host** (Copilot, Cursor, Codex, plain CLI): build `.loop/report.html` with `--standalone` and tell the user to open it.
  - Tell council members that Q11 is the *report* format. In the test run, one reviewer mistook "HTML page" for the product's output.
- **Markdown**: point the user to the `.loop/` files.
- **Both**: both.
- If the build itself includes capacity-sensitive parts (APIs, queues, databases under load), offer to run `capacity-engineering` Stage 2 and include its simulator.

---

## Rules that apply in every stage
- Update `.loop/state.md` at every transition: `stage`, `iteration`, `council_rounds`, `final_check_rounds`, `open_issues`.
- Never mark something PASS without evidence you actually produced in this session.
- Keep user interaction to the gates: intake (1b), plan confirmation (Gate 2), and final report. Don't pester between gates.
- If the user says "skip council" or "skip final check", record it in `state.md` and say in the final report that the stage was skipped.
- **Unattended / dry-run mode**: if the user says "run unattended", "don't ask", or "test the loop", fill intake answers with stated defaults marked `(SIMULATED)`, auto-pass Gate 2, and record `mode: unattended` in `state.md`. The final report must say which answers were simulated.
- Don't install tools globally just to run a check. Use what's available, a throwaway venv or `npx`, or mark the item `PASS (partial)` and say what wasn't verified.
- Results can be `PASS`, `PASS (partial)` with what's unverified, `PASS (risk)` when it met the bar but is close to a limit, `FAIL`, or `N/A (reason)`.
