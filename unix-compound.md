# unix-compound

A drop-in AI skill. Point it at any domain. It recursively defines success, decomposes the work into single-purpose modules, sequences blockers, builds, checks, and stops when the goal is met or returns diminish.

Every output is a text stream. Every module does one thing. Leftover modules compound into the next run.

---

## Philosophy (McIlroy)

1. Write programs that do one thing and do it well.
2. Write programs to work together.
3. Write programs to handle text streams, because that is a universal interface.

Also: build afresh rather than complicate old programs; expect every output to become the input of an unknown next program; try early and throw away clumsy parts; prefer tools over unskilled help.

---

## Standing Rules

- One thing well.
- Text streams are the universal interface.
- Early try → throw away → rebuild.
- Prefer tools and high-quality human signal.
- Occam at every step: if two designs meet the goal, keep the simpler one.
- New capability = a new module. Never fatten an existing one.
- This skill is a process, not a framework. Do not add modules to the skill unless a real gap appears twice.

---

## Process

```
goal → skeleton → sequence? → (build → check → sidecar)* → next
```

Emit the sidecar as the first content of every response while the skill is running.

---

## Modules

### goal
Propose measurable success criteria, refine them with the human, then lock as a text stream.

- Prefer 3–5 binary or numeric criteria.
- Ask for hard constraints (time, tools, energy, money) and lock them with the criteria.
- If the human does not lock after two proposals, proceed with the latest proposal as *provisional* and mark it clearly.
- Longitudinal criteria ("for 14 days") may be marked *in-progress / deferred verification*.
- Without a locked goal, later progress is unmeasurable. Do not skip this module.

### skeleton
Produce the modular structure (Skeleton-of-Thought + Occam).

- Hierarchical decomposition into single-purpose components.
- Immediately apply all hard constraints from the goal.
- When starting from messy existing material, cluster near-duplicates and mark multi-purpose items for throwaway.
- Prefer fewer modules.

### sequence
Chain-of-Logic over the skeleton: order, blockers, critical path. Skip when modules are independent.

- SoT answers *what the pieces are*. Chain-of-Logic answers *what must happen first*.
- Default to skipping unless clear dependencies exist.
- Early router / classifier modules are expected to be blockers — this is normal.
- Emit a compact Gantt-style block only when dependencies exist.

### build
Implement the next atomic module in its simplest viable form.

- Inside build, run a short VSR cycle: generate 2–4 variants → score → retain one.
- Score: goal-fit, one-thing-well, simplicity. Discard bloated variants.
- Keep a one-line lineage (which variant won, why).
- Do not implement two modules at once.

### check
QA the module against “one thing well” and the locked goal criteria.

- If clumsy, throw away and rebuild. Do not patch a multi-purpose module.
- Verify it does not violate any hard resource constraint from the goal.
- A passing check locks the module (`OK`).

### sidecar
Emit the terminal Markdown progress view as the first content of every response.

- Module status + goal progress + decision + residuals.
- When the module list exceeds ~8 items, use a compact view: active + last 3 completed + goal progress.
- HTML / visual dashboards are residuals. Terminal Markdown is the interface.

### next
Capture residuals and decide whether to recurse or terminate.

- Recurse to the next pending, unblocked module.
- Declare diminishing returns when Goal Progress ≥ 90% and residuals have been low-impact for two consecutive cycles. Recommend stop.
- After a third consecutive stall at ≥ 90%, force-stop.
- Before terminate, compare the modular result against a simple one-shot plan of the same goal. If the one-shot already meets the criteria, keep the one-shot.

---

## Sidecar (emit first)

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

- `OK` locked (passed check)
- `>>` active
- `..` pending
- `XX` discarded
- `--` residual / future

---

## Success Criteria

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

## Sequence / Critical Path (only if dependencies exist)

```markdown
### Sequence / Critical Path
1. module-a
2. module-b          <- blocks everything after it
3. module-c           (depends on 2)

**Critical path**: a -> b -> c
**Current blockers**: c blocked by b
```

---

## Worked example

Domain: `daily operating system, ≤15 minutes, notes app only`

**goal (proposed, then locked)**
1. Done when: capture, plan, and review are separate modules that talk via text streams
2. Done when: the whole system fits in ≤15 minutes
3. Done when: each day produces one archivable text output
4. Done when: it ran 5 consecutive days *(longitudinal — deferred)*

**skeleton**
`morning-capture` · `daily-plan` · `evening-review` · `archive-stream`

**sequence**
`morning-capture` blocks `daily-plan` blocks `evening-review` blocks `archive-stream`

**build / check**
VSR on `morning-capture` retains the contract-first variant. Check passes. Lock. Next.

**next**
3/4 criteria met, one deferred. Residuals low-impact. Terminate. One-shot checklist does not meet criterion 1, so the modular set is kept.

---

## Anti-patterns

- Skipping `goal` and “just starting”
- Expanding a module instead of creating a new one
- Building two modules in one step
- Treating the sidecar as optional
- Continuing after two low-impact cycles at ≥ 90%
- Keeping a clever modular design when a one-shot already meets the locked goal
- Inventing HTML, dashboards, or extra lexicon when terminal Markdown already shows the state

---

## How to use

Drop this file into any conversation, agent, or skill system. Name a domain. Follow the process. Stop when the sidecar says terminate.

Each successful run leaves reusable text-stream modules and a higher baseline for the next application. That is the compounding return.
