# Claude Code integration

Use **ri-engine** to improve prompts, then **Claude Code** to execute work in the repo. Handoff is **off by default** — turn it on when you want runbook + terminal instructions after each improve run.

## Enable / disable

### User-wide (all projects)

```bash
ri-engine config claude-code on
ri-engine config claude-code off
ri-engine config claude-code show
```

Saved to: `~/.config/ri-engine/settings.yaml`

### This project only

```bash
ri-engine config claude-code on --project
```

Saved to: `./.ri-engine/settings.yaml` (override user config)

### One run only

```bash
ri-engine improve --seed "..." --goal "..." --claude-code
ri-engine improve --seed "..." --goal "..." --no-claude-code   # force off
```

## When handoff is ON

After `ri-engine improve`:

1. Prompt is approved to **`runbook/RUNBOOK.md`**
2. CLI prints a **Claude Code handoff** panel with copy-paste opener
3. In Claude Code: *“Read `runbook/RUNBOOK.md` and follow the approved prompt…”*

When handoff is **OFF** (default): behavior is unchanged — improved prompt + JSON only.

## Typical workflow

```bash
# once
ri-engine config claude-code on

# per task type
ri-engine improve \
  --seed CLAUDE.md \
  --goal "When this works, Claude Code researches before editing, writes a spec, waits for proceed, then implements."

# terminal B
claude
# paste opener from handoff panel, or rely on runbook/RUNBOOK.md
```

## Settings reference

| Key | Default | Description |
|-----|---------|-------------|
| `claude_code_handoff` | `false` | Write runbook + show Claude Code panel after improve |

```bash
ri-engine config show
```

## Related

- [agent_integration.md](agent_integration.md) — recursive improve loop
- [getting_started.md](getting_started.md) — install and first run

## Middle loop — know when to stop iterating

Structural rubric scores (inner loop) are not enough. Run the **workflow self-test**
to score the evolved prompt against a fixed task battery:

```bash
ri-engine real-world workflow
```

This runs `config/workflow_self_test.yaml` and scores pass/fail on checks like:
no code-review bleed, compact output, research → spec → implement, runbook reference.

Results land in `output/real_world/sessions/<id>/task_battery.json`.

| Signal | Meaning |
|--------|---------|
| Battery pass rate ≥ 85% | Prompt structurally fits the workflow |
| Seed → evolved ↑ | Improvement run helped |
| Battery flat + `--until-plateau` flat | Middle loop next — run Claude Code on held-out tasks |
| Task pass rate flat | As good as your evidence allows; revise objective if failures repeat |

Honest scope: the battery checks **prompt structure**, not live Claude Code behavior.
Confirm with real agent runs before claiming production readiness.
