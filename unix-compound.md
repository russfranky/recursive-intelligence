# unix-compound

A recursive meta-skill **and** a terminal CLI plugin that turns any domain into modular, measurable, compounding progress using pure text streams.

```bash
pip install -e .
unix-compound start "daily operating system ≤15 min" --lock --run
# or
ri-engine compound start "daily operating system ≤15 min" --lock --run
```

Based on the Unix philosophy:

1. Write programs that do one thing and do it well.
2. Write programs to work together.
3. Write programs to handle text streams, because that is a universal interface.

Plus: build afresh rather than complicate; expect every output to become input to an unknown next program; try early and throw away clumsy parts; prefer tools over unskilled help.

---

## Standing Rules

- One thing well
- Text streams as the universal interface
- Early try → throw away → rebuild
- Prefer tools and high-quality human signal
- Occam applied at every step

---

## Modules

**goal**
Propose measurable success criteria to the human, refine them, then lock as a pure text stream.

- Prefer 3–5 binary or numeric criteria.
- Ask for hard constraints (time, tools, energy, money) and lock them as part of the criteria.
- If the human does not lock after two proposals, proceed with the latest proposal as *provisional*.
- Longitudinal criteria ("for 14 days") are marked *deferred verification*.

**skeleton**
Produce the modular structure of single-purpose components (Skeleton-of-Thought + Occam).

- Immediately apply all hard constraints from the goal.
- When starting from messy existing material, cluster near-duplicates and mark multi-purpose items for throwaway.
- Prefer fewer modules.

**sequence**
Derive order, blockers, and a light critical path. Skip when modules are independent.

- Default to skipping unless clear dependencies exist.
- Early router / classifier modules are expected to be blockers.

**build**
Implement the next atomic module in its simplest viable form.

- Uses Variation → Selection → Retention internally.
- Scores goal-fit, one-thing-well, and simplicity.
- Throws away bloated variants.

**check**
QA against “one thing well” and the locked goal criteria. If clumsy, throw away and rebuild.

Also verify the module does not violate any hard resource constraint from the goal.

**sidecar**
Emit the terminal Markdown progress view as the first content of every response.

When the module list exceeds ~8 items, prefer a compact view (active + last 3 completed + goal progress).

**next**
Capture residuals and decide whether to recurse or terminate.

Declare diminishing returns and stop when Goal Progress ≥ 90% and residuals have been low-impact for two consecutive cycles.

Before terminate, compare against a simple one-shot plan. Prefer the simpler winner if it already meets the goal.

---

## Process

```
goal → skeleton → sequence? → (build → check → sidecar)* → next
```

New capabilities are added only by creating new single-purpose modules — never by expanding existing ones.

---

## CLI

```bash
unix-compound start "domain text"
unix-compound lock                 # confirm proposed criteria
unix-compound lock --run           # lock then run to idle
unix-compound propose              # second proposal; auto-provisional lock
unix-compound step                 # one phase
unix-compound run                  # until terminate (needs --yes if goal open)
unix-compound sidecar              # print sidecar only
unix-compound status               # sidecar + module table
unix-compound status --json
unix-compound export -o out.json
```

Session file: `output/unix-compound-session.json`

Works offline (no API key). Deterministic heuristics plus VSR scoring.

---

## Sidecar Format

```markdown
### unix-compound · sidecar
**Phase** [name] | **Coverage** [bar] [x%] | **Depth** [n]
**Active** → `module`

| S | Module   | Purpose                    | Interface          |
|---|----------|----------------------------|--------------------|
| OK | ...      | ...                        | ...                |
| >> | **name** | ...                        | ...                | <- ACTIVE
| .. | ...      | ...                        | ...                |

**Focus** ...
**Goal Progress** x/y
**Decision** continue / lock / terminate
**Residuals** ...
```

Status set:

- OK locked (passed check)
- >> active / in progress
- .. pending
- XX discarded / thrown away
- -- residual / future

---

## How to use as a skill

Drop this file into any conversation, agent, or skill system. Point it at a domain. It will recursively define success, decompose into single-purpose modules, sequence when needed, build, check, and stop when the goal is met or diminishing returns appear.

Each successful run leaves behind reusable text-stream modules and a higher baseline for the next application.
