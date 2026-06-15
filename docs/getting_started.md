# Getting Started

## What it does

Give **ri-engine** a seed prompt and a goal. It runs **Variation → Selection → Retention** with a **linguistic gate** (plain / latinate / mixed register) and returns an improved prompt. Works offline by default.

## Install

```bash
pip install recursive-intelligence
```

## Improve your prompt

```bash
ri-engine improve \
  --seed "You are a helper." \
  --goal "When this works, the AI will produce a structured answer with measurable success criteria"
```

Copy the improved prompt from the output into your AI tool's system prompt field.

## Optional: templates

Templates are benchmark fixtures, not required:

```bash
ri-engine templates
ri-engine improve --template code-review
```

## Demo

```bash
ri-engine demo
```

Scores are from the internal structural rubric — not live task performance.

## Python API

```python
from ri_engine import improve

result = improve(
    seed_prompt="You are a helper.",
    objective="When this works, the AI will produce a structured answer.",
)
print(result.improved_prompt)
```

See [technical_reference.md](technical_reference.md) for architecture details.
