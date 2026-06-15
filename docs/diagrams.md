# Diagrams

Visual overview of **ri-engine** — how prompt improvement works, how to validate results, and how Claude Code fits in.

> GitHub renders these Mermaid charts in the markdown viewer. For a plain-text fallback, see [technical_reference.md](technical_reference.md).

---

## 1. What you do (30 seconds)

```mermaid
flowchart LR
  subgraph input["Your input"]
    S["Seed prompt<br/>(what you have today)"]
    G["Goal<br/>(When this works, …)"]
  end

  subgraph engine["ri-engine"]
    I["improve"]
  end

  subgraph output["Your output"]
    P["Improved prompt"]
    J["JSON report"]
  end

  S --> I
  G --> I
  I --> P
  I --> J
  P --> U["Copy into system prompt<br/>or Claude Code / runbook"]
```

**Command:** `ri-engine improve --seed "…" --goal "…"`

---

## 2. VSR pipeline (how improvement runs)

Each **generation** runs Variation → Selection → Retention. The loop repeats until fitness plateaus or `max_generations` is reached.

```mermaid
flowchart TB
  IN["Seed + goal"] --> LG["Linguistic gate<br/>(plain / latinate / mixed …)"]
  LG --> MP["Macro priors<br/>(opt-in, off by default)"]
  MP --> MB["Membrane bridge<br/>(optional cross-domain insight)"]

  MB --> V["Variation<br/>8 mutation strategies"]
  V --> SEL["Selection<br/>score fitness"]
  SEL --> R["Retention<br/>survivors + lineage memory"]

  R --> C{"Converged?"}
  C -->|no| V
  C -->|yes| BR["Baseline vs VSR pick<br/>(Occam guardrail)"]
  BR --> OUT["Best prompt + fitness report"]
```

**Honest scope:** default **mock** provider scores **structure** locally. It does not prove live LLM task success — use `--provider openai` or `--provider anthropic` for semantic rewriting, then evaluate tasks separately.

---

## 3. Baseline vs VSR (Occam guardrail)

VSR does not always beat a one-shot finalize. The engine returns the **simpler** result when the evolutionary winner adds bloat without gain.

```mermaid
flowchart LR
  VSR["VSR winner"] --> CMP{"Compare vs<br/>one-shot finalize"}
  FIN["One-shot finalize"] --> CMP
  CMP -->|VSR wins| W["Return VSR prompt"]
  CMP -->|Finalize wins<br/>or tie on utility| F["Return compact finalize"]
```

---

## 4. Recursive validation — knowing when to stop

Three nested loops answer different questions. All three should plateau before you call the workflow “done.”

```mermaid
flowchart TB
  subgraph inner["Inner loop — prompt structure"]
    IMP["ri-engine improve<br/>or --until-plateau"]
    RUB["Rubric + diagnostics"]
    IMP --> RUB
  end

  subgraph middle["Middle loop — workflow fit"]
    WF["ri-engine real-world workflow"]
    BAT["Task battery<br/>(8 structural checks)"]
    WF --> BAT
  end

  subgraph outer["Outer loop — real behavior"]
    CC["Claude Code / your agent"]
    TASK["Held-out task battery<br/>(pass / fail)"]
    CC --> TASK
  end

  inner -->|"fitness flat"| middle
  middle -->|"battery ≥ threshold"| outer
  outer -->|"failures"| FEED["Update seed + goal<br/>with failure modes"]
  FEED --> inner
```

| Loop | Command | Stops when… |
|------|---------|-------------|
| Inner | `ri-engine improve --until-plateau` | Fitness gain below threshold |
| Middle | `ri-engine real-world workflow` | Task battery pass rate ≥ 85% and stable |
| Outer | Live agent on real tasks | Pass rate flat on held-out cases |

---

## 5. Claude Code integration

Handoff is **off by default**. Turn it on when you want runbook + terminal instructions after each improve run.

```mermaid
sequenceDiagram
  participant U as You
  participant RI as ri-engine
  participant RB as runbook/RUNBOOK.md
  participant CC as Claude Code

  U->>RI: improve --seed … --goal …
  Note over RI: config claude-code on<br/>or --claude-code
  RI->>RI: VSR + finalize
  RI->>RB: Approve prompt (when handoff on)
  RI->>U: Improved prompt + handoff panel
  U->>CC: Read runbook/RUNBOOK.md …
  CC->>CC: Research → spec → proceed → implement
```

**Settings**

```mermaid
flowchart TD
  ON["Handoff ON"] --> RB["Write runbook entry"]
  ON --> PN["Print handoff panel"]
  OFF["Handoff OFF (default)"] --> ONLY["Prompt + JSON only"]

  subgraph controls["How to control"]
    C1["ri-engine config claude-code on"]
    C2["--claude-code / --no-claude-code"]
    C3[".ri-engine/settings.yaml (project)"]
  end

  controls --> ON
  controls --> OFF
```

Details: [claude_code_integration.md](claude_code_integration.md)

---

## 6. Middle-loop task battery

When `metadata.task_battery` is set (e.g. `config/workflow_self_test.yaml`), the engine scores **seed vs evolved** against fixed checks.

```mermaid
flowchart LR
  SEED["Raw seed"] --> SCORE["Task battery<br/>8 checks"]
  EV["Evolved prompt"] --> SCORE
  SCORE --> REP["Pass rate + delta<br/>task_battery.json"]
```

Example checks: no code-review bleed, compact length, research→spec→implement, runbook reference, no benchmark boilerplate.

```bash
ri-engine real-world workflow
```

---

## 7. Collective intelligence (patterns, not secrets)

Local learning is built; federated sync is phased and opt-in.

```mermaid
flowchart TB
  RUN["improve run completes"] --> SEL{"Fitness ≥ threshold?"}
  SEL -->|yes| TR["Parse Retention traits"]
  TR --> LOCAL["Local macro registry<br/>(opt-in)"]

  LOCAL --> V1["v1 ✓ Local pool"]
  LOCAL --> V2["v2 ✓ --share-traits export"]
  LOCAL --> V3["v3 Planned: curated aggregation"]
  LOCAL --> V4["v4 Planned: encrypted sync"]

  V2 --> EXP["Trait JSON only<br/>no raw prompts"]
  V3 --> PUB["Shared registry<br/>PR-reviewed merges"]
```

**Principle:** personal prompts stay local; only **trait patterns** (e.g. `constraint_first`, `failure_mode_guards`) are candidates for pooling — gated by task batteries before any global merge.

Macro registry: **off by default** (`--use-persistent-macro-registry`).

---

## 8. Typical user paths

```mermaid
flowchart TD
  START(["New user"]) --> GS["getting_started.md"]
  GS --> A{"Use case"}

  A -->|One-off prompt| IMP["ri-engine improve"]
  A -->|Claude Code repo work| CC["config claude-code on"]
  A -->|Research / benchmarks| DEMO["ri-engine demo"]
  A -->|Prove workflow fit| RW["ri-engine real-world workflow"]

  CC --> IMP2["improve + handoff"]
  IMP2 --> RB["runbook/RUNBOOK.md"]

  IMP --> DONE["Copy improved prompt"]
  RW --> BAT2["Task battery report"]
  BAT2 --> DONE2["Iterate or ship"]
```

---

## Related docs

| Topic | Document |
|-------|----------|
| Install & first run | [getting_started.md](getting_started.md) |
| Claude Code handoff | [claude_code_integration.md](claude_code_integration.md) |
| Agent embedding | [agent_integration.md](agent_integration.md) |
| Architecture detail | [technical_reference.md](technical_reference.md) |
| Scope & limitations | [publication.md](publication.md) |
