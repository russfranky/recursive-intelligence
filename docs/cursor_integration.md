# Cursor Agent Integration — Recursive Intelligence Loop

Use this workflow to run the Recursive Intelligence Engine as an automated improvement loop inside Cursor or any agentic environment.

## Phase 1: Seed

Create a task config:

```yaml
# config/my_agent.yaml
seed_prompt: |
  <your current system prompt or task prompt>

objective: |
  <what "fitness" means for this prompt — be specific and measurable>

max_generations: 8
population_size: 6
survivors_count: 2
enable_membrane_bridge: true

domains:
  - "<domain relevant to your task>"
  - "<adjacent domain for cross-pollination>"

fitness_weights:
  clarity: 0.25
  novelty: 0.20
  utility: 0.40
  coherence: 0.15

output_path: ./output/my_agent_run.json
```

## Phase 2: Evolve

```bash
ri-engine --config config/my_agent.yaml --provider openai
```

## Phase 3: Deploy

Copy `best_prompt` from the output JSON into your Cursor rules, `.cursorrules`, or agent system prompt.

## Phase 4: Recursive Meta-Loop

After the agent runs on real tasks:

1. Collect failures and successes
2. Update `seed_prompt` with the deployed prompt + failure examples
3. Update `objective` to target observed failure modes
4. Re-run the engine

This closes the loop: **agent output → new selection pressure → evolved prompt → better agent**.

## Phase 5: Meta-Improvement

When fitness plateaus, use `prompts/meta_improvement.md` as a system prompt and ask the agent to diagnose:

- Is the selection environment optimizing a proxy metric?
- Are variations clustering locally?
- Are membrane domains too narrow?

Apply the YAML adjustments the meta-operator recommends.

## Single-Generation API (for n8n, Make, CI)

```python
from ri_engine import RecursiveIntelligenceEngine, RunConfig

engine = RecursiveIntelligenceEngine()
config = RecursiveIntelligenceEngine.load_config("config/my_agent.yaml")

# Generation 1
g1 = engine.run_single_generation(config, generation=1)
parents = g1.survivors

# Generation 2
g2 = engine.run_single_generation(config, parents, generation=2, lineage_memory=g1.notes)
```

## Anti-Patterns to Avoid

| Failure Mode | Research Analog | Fix |
|-------------|-----------------|-----|
| Optimizing prompt length | Engagement optimization | Increase `utility` weight |
| Variants too similar | Local search in sparse topology | Increase `population_size`, enable membrane |
| Premature convergence | 20ms generations without review | Raise `convergence_threshold`, add domains |
| No recursive hook | Output doesn't feed back | Require self-eval rubric in seed prompt |
