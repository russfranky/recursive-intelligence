# Getting Started (Non-Technical Guide)

This guide is for **business users, team leads, and anyone who uses AI tools** — no coding or ML background needed.

## What this product does

You give it a **rough prompt** (instructions for an AI assistant). It gives you back a **polished prompt** that:

- Has clear step-by-step instructions
- Defines exactly what output to produce
- Includes quality checks so the AI self-reviews before answering
- Uses the right tone for your audience (customers, developers, executives, etc.)

Think of it as an **editor for AI instructions**.

---

## Step 1: Install

Ask your IT team to run:

```bash
pip install -e .
```

Or if you have Python installed:

```bash
cd recursive-intelligence
pip install -e .
```

**No API key required** to try the demo and templates.

---

## Step 2: Choose a starting point

Run:

```bash
ri-engine templates
```

You'll see a list like:

| Name | What it's for |
|------|---------------|
| Customer Support Agent | Help desks |
| Code Review Agent | Engineering teams |
| AI Coding Assistant | Developer tools |
| Sales Outreach Agent | Sales emails |
| Security Incident Response | IT security teams |
| Research Analyst | Reports and analysis |

Pick the one closest to your need.

---

## Step 3: Run improvement

```bash
ri-engine improve --template customer-support
```

You'll see a progress screen with plain labels:

- **New versions** — trying improved drafts
- **Pick the best** — scoring each version
- **Keep winners** — carrying forward what works

This takes about 30–60 seconds.

---

## Step 4: Use your result

At the end you'll see:

### ✓ Results
- **Quality score** — how strong your prompt is (aim for 85%+)
- **Writing style** — the tone we matched for your task
- **Status** — whether improvement finished

### Your Improved Prompt — Copy This
Copy the entire box and paste it into:

- **ChatGPT** → Custom GPT instructions or system message
- **Claude** → Project instructions
- **Cursor / Copilot** → project rules or agent system prompt
- **Any API** → `system` parameter

### Saved file
`output/your_improved_prompt.json` contains the same result for your records.

---

## Using your own prompt

Create a text file with your current prompt, e.g. `my_prompt.txt`:

```
You are a sales assistant. Write emails to prospects.
```

Then run:

```bash
ri-engine improve --seed my_prompt.txt --goal "Write short personal emails that book meetings"
```

---

## See proof before you commit

```bash
ri-engine demo
```

Shows 6 business scenarios going from **~20% quality → 100% quality**. No technical terms.

---

## FAQ

**Do I need to understand what's happening under the hood?**  
No. The value is the improved prompt at the end.

**Does it work without internet?**  
Yes, for templates and demo (built-in mode). For GPT/Claude quality, add an API key.

**Can I improve the same prompt again?**  
Yes. Use the improved prompt as your new `--seed` and run again.

**Who is this for?**  
Support teams, sales, engineering, security, research, operations — anyone who relies on AI assistants and wants consistent, reliable outputs.

---

## Glossary (only if you're curious)

| You see | It means |
|---------|----------|
| Quality score | How complete and actionable your prompt is |
| Writing style | The tone (clear, friendly, formal, technical) |
| Improvement rounds | How many times we refined the prompt |
| Template | A pre-built starting point for a common job role |

---

*Questions? Run `ri-engine` with no arguments for a quick help screen.*
