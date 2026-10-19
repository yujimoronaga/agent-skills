# Built-in capacity council (fallback)

Use this only when no dedicated LLM Council skill is installed. It runs the same way as loop-engineering's council: independent reviews, then anonymous peer review, then the chair's synthesis. Run members in parallel as subagents where the host supports that, otherwise as sequential passes. Members must not write files and should keep replies to about 300 words.

| Member | Focus |
|---|---|
| **Limits Verifier** | Every limit in `model.json`: is the value right for this account, region and plan? Is it hard or adjustable, and at what scope? Verify against docs or web, or read-only CLI if allowed. Look for limits that are missing entirely: payload, timeout, burst, connections, per-key. |
| **Load Modeler** | Are scenarios, fanout and durations realistic? Has the retry amplification been counted? Is the burst shape plausible? Are other consumers of shared limits included? Re-check the calculator's arithmetic for the top 3 breakpoints. |
| **Failure-Chain Analyst** | What happens over each limit: does the failure propagate or cascade (retry storms, timeout mismatches, connection storms after a cold start, queue backlog growth)? What does the user actually see? |
| **Cost Auditor** | Cost at expected, peak and spike load (compute, requests, data transfer, provisioned capacity, proxy). Flag any fix whose cost is out of proportion and suggest a cheaper one. |

Each member returns:
```
Member: <role>
Verdict: APPROVE | CHANGES | REJECT
Issues:
  1. [blocker|major|minor] <issue> — evidence: <source/calculation> — fix: <suggestion>
Unverified limits: <list>
Questions only the user can answer: <list>
```

Chair rules:
- A wrong limit value that changes the first-breakpoint ranking is a blocker.
- A missing component in the request path is a blocker.
- An unverified limit that sits within 2× of target peak is a major issue.
- In round 2 and later, use a single delta reviewer that marks each earlier issue RESOLVED or NOT RESOLVED and finds new issues.

**Models:** use `models.council` from state.md. With one model, every member runs on it. With a list, member N runs on model N. Mixing models gives the council real diversity; the default is the current session model.
