# Stage 4 — Final Check

## Mandatory checks (always copied into checklist.md)
Each needs evidence. Mark `N/A (reason)` only when it truly doesn't apply.

**Works**
- [ ] M1 Builds / installs from a clean state with the documented steps
- [ ] M2 Runs end-to-end on the main user flow (show the command/output or screenshot)
- [ ] M3 All tests pass (show the test command and summary)
- [ ] M4 Every MVP item demonstrably works (linked to its checklist line)

**Matches the request**
- [ ] M5 Output type matches intake Q3 (e.g. it's actually an API if an API was asked for)
- [ ] M6 Matches the user's image / reference (intake Q6) — compare side by side
- [ ] M7 Nothing from "Out of scope" was built; nothing in MVP was dropped

**Robustness**
- [ ] M8 Invalid / empty / large input handled without crashing; clear error messages
- [ ] M9 External calls (network, APIs, DB) have timeouts and failure handling

**Security & hygiene**
- [ ] M10 No secrets, keys, or tokens in code, logs, or committed files
- [ ] M11 User input is validated; no obvious injection (SQL, shell, XSS, path)
- [ ] M12 Dependencies are real, pinned, and maintained (no hallucinated packages)
- [ ] M13 No leftover TODO/FIXME/debug prints/dead code from this build

**Handover**
- [ ] M14 README or run notes: how to install, configure, run, test
- [ ] M15 Config/env vars documented with example values (no real secrets)
- [ ] M16 Open assumptions from plan.md listed in the final report

**Tests that really test**
- [ ] M17 For each critical property (thread safety, limits, security checks, money maths), break it on purpose in a temporary copy (remove the lock, drop the cap, skip the check) and confirm at least one test fails. A test suite that still passes against broken code is a FAIL for that property. In the test run, removing the lock went unnoticed until this check was added.

## final-report.md template
```
# Final Check — round <n> — <date>

| ID | Item | Result | Evidence |
|----|------|--------|----------|
| MVP-1 | ... | PASS | `npm test` → 12 passed (test: create_order.spec.ts) |
| U-1   | ... | FAIL | p95 = 340ms, target 200ms |
| M10   | No secrets in code | PASS | `git grep -nE "(api[_-]?key|secret|token)\s*="` → no hits |

Summary: <x> PASS, <y> FAIL, <z> N/A
Failures → route:
  - U-1 → Stage 3 (defect: N+1 query in /orders)
Open assumptions: ...
```
