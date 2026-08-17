# unix-compound

A recursive meta-skill that turns any domain into modular, measurable, compounding progress using pure text streams.

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

Guidance:
- Prefer 3–5 binary or numeric criteria.
- Explicitly ask for hard constraints (time, tools, energy, money) and lock them as part of the criteria.
- If the human does not lock criteria after two proposals, proceed with the latest proposal as *provisional* and mark it clearly.
- Longitudinal criteria ("for 14 days") may be marked *in-progress / deferred verification*.

**skeleton**
Produce the modular structure of single-purpose components (Skeleton-of-Thought + Occam).

Guidance:
- Immediately apply all hard constraints from the goal.
- When starting from messy existing material, cluster near-duplicates and mark multi-purpose items for throwaway.
- Prefer fewer modules.

**sequence**
Derive order, blockers, and a light critical path. Skip when modules are independent.

Guidance:
- Default to skipping unless clear dependencies exist.
- Early router / classifier modules are expected to be blockers — this is normal.

**build**
Implement the next atomic module in its simplest viable form.

**check**
QA against “one thing well” and the locked goal criteria. If clumsy, throw away and rebuild.

Also verify the module does not violate any hard resource constraint from the goal.

**sidecar**
Emit the terminal Markdown progress view as the first content of every response (module status + goal progress).

When the module list exceeds ~8 items, prefer a compact view (active + last 3 completed + goal progress).

**next**
Capture residuals and decide whether to recurse or terminate.

Declare diminishing returns and recommend stopping when Goal Progress ≥ 90% and residuals have been low-impact for two consecutive cycles.

---

## Process

```
goal → skeleton → sequence? → (build → check → sidecar)* → next
```

New capabilities are added only by creating new single-purpose modules — never by expanding existing ones.

---

## Sidecar Format

Emit this block first in every response while the skill is running. Update it after every major phase.

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

Status set (fixed):

- OK locked (passed check)
- >> active / in progress
- .. pending
- XX discarded / thrown away
- -- residual / future

---

## Sequence / Critical Path (optional)

When dependencies exist, emit a compact text block:

```markdown
### Sequence / Critical Path
1. module-a
2. module-b          <- blocks everything after it
3. module-c           (depends on 2)

**Critical path**: a -> b -> c
**Current blockers**: c blocked by b
```

---

## Success Criteria Block

While proposing:

```markdown
### Success Criteria (proposed)
1. Done when: [concrete, observable outcome]
2. Done when: [testable metric or condition]
3. Done when: [user-visible result]
-> Confirm / edit / reject?
```

Once locked:

```markdown
### Success Criteria (locked)
1. [ ] Done when: ...
2. [ ] Done when: ...
3. [ ] Done when: ...
Goal Progress: 0/3
```

---

## How to use

Drop this file into any conversation, agent, or skill system. Point it at a domain. It will recursively define success, decompose into single-purpose modules, sequence when needed, build, check, and stop when the goal is met or diminishing returns appear.

Each successful run leaves behind reusable text-stream modules and a higher baseline for the next application.
