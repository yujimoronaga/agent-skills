# Stage 1 Intake — QA form

Ask these **one at a time** (see SKILL.md § 1b), in this order. Each line is a question; the text in brackets is its default.

```
1. What are we building? (one sentence)  [required]
2. Do you have an architecture? link / file / describe, or "no"  [default: no, I'll propose one]
3. What output do you need? web app / API / CLI / script / library / report / mobile app / automation  [default: inferred from 1]
4. What's the MVP? The must-haves for "working"  [default: I propose 3–5 items for you to confirm]
5. Stack / constraints: language, framework, cloud, budget, must-use / must-avoid  [default: you decide]
6. Do you have an image of it? mockup, screenshot, sketch, sample output, "like <product>"  [default: none]
7. Who uses it, how many, where does it run?  [default: just you, locally]
8. What do you want checked at the end, on top of the standard checks?  [default: standard checks only]
9. Anything else? existing repo, data, credentials, deadlines, links  [default: none]
10. Out of scope: things NOT to build now  [default: anything not in the MVP]
11. How should I report back to you (plan, council results, final report)? HTML page / Markdown files / both  [default: Markdown]. This is the report format, not what we're building.
12. Max loops: council rounds and final-check rounds before stopping to ask you  [default: 3]
13. Model per stage  [default: the current model for every stage]
```

## Handling answers
- Save verbatim to `.loop/intake.md` under the matching numbers.
- `skip` / `you decide` → write your choice into `plan.md` tagged `[ASSUMPTION]`.
- Q2 = yes → read the architecture they point to before planning; the council will check the plan against it.
- Q6 image provided → describe it in `plan.md` (layout, components, data shown) so "matches the image" becomes a checkable item.
- Q4 empty → propose an MVP of 3–5 items in the plan and flag it for confirmation at Gate 2.
- Q8 → every item becomes a line in the "User-specific checks" section of `checklist.md`.
- Q10 → copied into the plan's "Out of scope" section; the council flags anything that creeps back in.
- Q12 sets `max_loops:` in state.md.
- Q13 sets `models:` in state.md (see SKILL.md § Models per stage). Skipped means the current model for every stage.
- Q11 sets the deliverable format (see SKILL.md § Deliverable format).

Ask follow-up questions only for things that block the plan, still one at a time.
