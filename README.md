# agent-skills

Two engineering skills in the open `SKILL.md` format, so they work in Claude Code, GitHub Copilot (CLI and VS Code agent mode), Cursor, Codex and any other agent that reads skills.

| Skill | What it does |
|---|---|
| [`loop-engineering`](loop-engineering/SKILL.md) | Takes a build through four gated stages: **plan** (one-question-at-a-time intake), **fact-check** (an LLM Council of reviewers that sends the plan back until it holds up), **code**, and **final check** against the MVP checklist plus mandatory checks. Failures loop back to the right stage. |
| [`capacity-engineering`](capacity-engineering/SKILL.md) | Finds where an architecture breaks under load, e.g. "the SQS trigger caps the worker at 20 uploads/s" or "RDS runs out of connections at 218 req/s". Every limit gets a source, and the result is **one HTML page**: a live architecture diagram (green / amber / red), every quota and resource variable editable, rule checks, fixes you can try, and quota requests to file. |

## Shared features
- **QA intake**: questions come one at a time, each with a default. "Use defaults for the rest" skips ahead.
- **LLM Council**: uses an installed LLM Council skill if there is one. Otherwise four built-in reviewers run in parallel and peer-review each other, then a delta reviewer handles later rounds.
- **Max loops**: caps how many review and fix rounds run before it stops to ask you (default 3).
- **Model per stage**: choose a model for each stage, and one per council member. The default is the model you're already using.
- **State on disk**: `.loop/` or `.capacity/` in your project, so any agent or a later session can resume.
- **Report format**: Markdown, HTML, or both. In the Claude apps, the HTML is published as an Artifact.

## Install

**Claude Code** (personal, all projects):
```bash
git clone https://github.com/yujimoronaga/agent-skills.git ~/agent-skills
mkdir -p ~/.claude/skills
ln -s ~/agent-skills/loop-engineering ~/.claude/skills/loop-engineering
ln -s ~/agent-skills/capacity-engineering ~/.claude/skills/capacity-engineering
```

**GitHub Copilot**, personal:
```bash
mkdir -p ~/.copilot/skills
ln -s ~/agent-skills/loop-engineering ~/.copilot/skills/loop-engineering
ln -s ~/agent-skills/capacity-engineering ~/.copilot/skills/capacity-engineering
```
For a single repository, copy the two folders into that repo's `.github/skills/` instead.

**Other agents** (Codex, Cursor and others that read `~/.agents/skills`): link them the same way into `~/.agents/skills/`.

## Use
- `/loop-engineering`, or "build X with the loop"
- `/capacity-engineering`, or "will this scale?" / "where does this break?"

To try the capacity tools without an agent (Python 3.9+, standard library only):
```bash
python3 capacity-engineering/scripts/capacity_calc.py capacity-engineering/examples/serverless-api.json
python3 capacity-engineering/scripts/build_simulator.py capacity-engineering/examples/serverless-api.json demo.html --standalone
open demo.html
```

## Notes
- The limits in `capacity-engineering/references/limits-cheatsheet.md` are starting points. The skill verifies each one against docs or your account before relying on it.
- Load tests and cloud quota commands only run with your explicit OK. The skills never file quota increases or change live infrastructure.
