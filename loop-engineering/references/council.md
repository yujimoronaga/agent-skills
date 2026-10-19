# Built-in LLM Council (fallback)

Use this only when no dedicated LLM Council skill/tool is available. Modeled on the council pattern: independent opinions → anonymous peer review → chair synthesis.

Context for every member: intake Q11 and Q13 (report format, models) are about how the loop runs, not about the product.

## Members
Each member reviews `.loop/intake.md` + `.loop/plan.md` + `.loop/checklist.md` independently.

| Member | Focus |
|---|---|
| **Fact Checker** | Every concrete claim: package names, API signatures, versions, service limits, quotas, pricing, config syntax. Verify with docs/web search when tools allow; otherwise mark `UNVERIFIED`. |
| **Requirements Auditor** | Every MVP item and user check maps to a plan task and a checklist item. Plan matches the user's output type and image. Nothing out of scope sneaks in. |
| **Architect** | Design fits the stated architecture and constraints; data flow, failure modes, auth, state, deployment are covered; simplest design that works. |
| **Skeptic** | Tries to make it fail: edge cases, bad input, missing error handling, security holes, things that work in a demo but not in use. |

## How to run it
- **Host supports subagents** (Claude Code Agent tool, Copilot `/fleet` or custom agents, etc.): spawn the 4 members in parallel, each with only its focus + the three files. If the host lets you pick models, give members different models for real diversity. A mid-tier model is enough for members, and each should cap its reply at about 300 words in the format below. Tell members not to write files. The Fact Checker should run small snippets to verify claims where it can; in the test run, that's how it reproduced the real blocker.
- **No subagents**: do 4 separate passes yourself, one role at a time. Write each member's findings before starting the next, and don't soften earlier findings.

Each member returns:
```
Member: <role>
Verdict: APPROVE | CHANGES | REJECT
Issues:
  1. [blocker|major|minor] <issue> — evidence: <source/reason> — fix: <suggestion>
Unverified claims: <list>
Questions only the user can answer: <list>
```

## Peer review
Anonymize the four reports (A–D). Each member (or one pass if no subagents) ranks them by accuracy and usefulness and notes any issue it thinks is wrong. Drop issues two or more reviewers reject as incorrect.

## Chair synthesis → `.loop/council.md`
```
## Council round <n> — <date>
Verdict: APPROVED | APPROVED WITH CHANGES | REJECTED
Blockers:   ...
Major:      ...
Minor:      ...
Unverified claims (must be resolved or tagged as risk): ...
Questions for the user: ...
Changes applied to plan.md: ...
```
Rules for the chair:
- Any blocker → `REJECTED`.
- An unverified claim that the MVP depends on counts as a major issue.
- Contradictions between intake and plan are always at least major.

**Models:** use `models.council` from state.md. With one model, every member runs on it. With a list, member N runs on model N. Mixing models gives the council real diversity; the default is the current session model.
