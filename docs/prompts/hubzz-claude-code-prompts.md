# Hubzz Claude Code — copy-paste prompts

Use these in Claude Code (pre-alpha) so agents stop CSS-proxy “fixes” and follow research → synthesize → implement.

---

## 1. Session opener (paste first in a new Claude Code thread)

```markdown
## Operating mode: ri-engine discipline

Before any edit:
1. Confirm desired outcome in one falsifiable sentence ("When this works, …").
2. If research answers the question, do not AskUserQuestion again.
3. Research → write spec (files + lines + observable success) → get my OK or explicit "proceed" → implement.
4. CSS/layout-only changes do NOT count as avatar pipeline work unless the spec says so.

My stack: pre-alpha monorepo, hubzz-coordinator skill available.

Do not start coding until the spec is written and I say proceed (or I invoked /hubzz-coordinator).
```

---

## 2. Desired outcome — full-body avatar on `/u/Russ` (the one that failed before)

**Paste as your task message:**

```markdown
## Desired outcome (read first)

When this works, visiting https://hubzz.app/u/Russ shows a **live full-body VRM avatar render** matching admin `UserVRMPreview` behavior—not a reframed `thumb.jpg`, not `rounded-full` removed, not object-contain on the same 256×256 head crop.

## Success criteria (all required)
- [ ] Full body visible in sidebar slot (same visual class as admin dashboard)
- [ ] Uses VRM from `path.split('|')[0]` (or ported `avatarThumbnailRenderer.ts` pipeline)
- [ ] Loading / null path / error → initials fallback (keep existing PFP fallback pattern)
- [ ] Mount: `PublicProfile.tsx` ~line 163 (lg slot only; do not break explore/collection pages)
- [ ] `pnpm` typecheck passes in affected package
- [ ] Sentry: no new unresolved issues in last 30m after deploy

## Explicit non-goals
- Do NOT ship CSS-only changes and call it full-body
- Do NOT run 1m+ production build until spec is approved
- Do NOT delete shared PFP without verifying all call sites

## Execution
Run `/hubzz-coordinator` with this message. Research in parallel, synthesize spec, wait for my "proceed", then implement.
```

---

## 3. `/hubzz-coordinator` invoke (one line)

```
/hubzz-coordinator Deliver full-body VRM render on /u/Russ per the desired outcome in my last message: port avatarThumbnailRenderer.ts from pre-cb7dff21, add VrmFullBodyAvatar.tsx, wire at PublicProfile.tsx:163. Research → spec → my proceed → implement → verify Sentry.
```

---

## 4. Coordinator system addendum (if you edit `CLAUDE.md` or project instructions)

```markdown
## Hubzz coordinator rules (mandatory)

### Phase gates
| Phase | Output | Edits allowed? |
|-------|--------|----------------|
| Research | Findings + file:line refs | NO |
| Synthesize | Spec table: change / file / success test | NO |
| Implement | Patch + typecheck | YES |
| Verify | Sentry + manual URL check | YES |

### Avatar / profile tasks
- "Full body" = VRM thumbnail renderer or live VRM canvas—not CSS on thumb.jpg
- Admin reference: `UserVRMPreview.tsx`
- Deleted source to recover: `avatarThumbnailRenderer.ts` @ cb7dff21^

### Question budget
- Max 3 blocking questions before research starts
- Zero AskUserQuestion after research workers return—synthesize instead

### Proxy fixes (reject)
- Frame/crop CSS presented as pipeline work
- Long question menus when codebase already has the answer
- Skipping synthesize after parallel agents complete
```

---

## 5. Plan agent prompt (before `claude` worker)

```markdown
You are Plan-only. No edits.

Goal: When this works, /u/:username shows full-body VRM render matching admin UserVRMPreview.

Deliver:
1. Current state (3 bullets): what PublicProfile renders, what API returns, what admin renders
2. Gap analysis (1 paragraph): why thumb.jpg + CSS cannot satisfy the goal
3. Implementation plan: numbered steps, exact file paths, line ranges, new files
4. Risk table: layout blast radius, bundle size, lazy-load strategy
5. Verification checklist: typecheck command, URL to hit, Sentry query

Do not propose CSS-only solutions as the primary plan.
```

---

## 6. Implementation worker prompt (after you approve the plan)

```markdown
Execute the approved plan exactly. No scope expansion.

Approved plan:
[paste Plan output here]

Rules:
- Minimal diff, match conventions
- Run typecheck before claiming done
- If thumb.jpg is not full-body asset, do not pretend CSS fixed it—port renderer
- Report: files changed, commands run, what to verify on hubzz.app/u/Russ
```

---

## 7. ri-engine CLI (generate + lock your own runbook)

Run on your machine in `recursive-intelligence/`:

```bash
pip install -e .

# Sharpen your task prompt
ri-engine improve \
  --seed docs/prompts/hubzz-claude-code-prompts.md \
  --goal "When this works, Claude Code agents follow research-synthesize-implement for Hubzz avatar work with falsifiable success criteria and no CSS proxy fixes."

# Cycle until stable, save for next session
ri-engine improve \
  --seed my_hubzz_task.md \
  --goal "When this works, /u/Russ shows full-body VRM matching admin UserVRMPreview with initials fallback on error." \
  --until-plateau --runbook --runbook-name hubzz-profile-avatar --share-traits
```

Then point the next Claude session at `runbook/RUNBOOK.md`.

---

## 8. Quick goal templates (swap `[...]`)

| Task | Desired outcome line |
|------|----------------------|
| Profile API | When this works, `/api/users/:username/profile` returns all fields `ProfileView` needs so embeds never scrape `/u/:username` HTML. |
| PoC demo | When this works, I can open `[URL]` and see `[feature]` working end-to-end in under 2 minutes without manual setup. |
| Avatar | When this works, `/u/:username` shows full-body VRM matching admin, not thumb crop. |
| Bugfix | When this works, `[action]` produces `[observable result]` without `[regression]`. |

---

## 9. Vague goal → fixed (clarity gate examples)

**Blocked (don't send):**
- "make full body avatar display"
- "proof of concept for pre-alpha"
- "fix the button"

**Pass (send these):**
- "When this works, /u/Russ renders full-body VRM via ported avatarThumbnailRenderer, matching admin UserVRMPreview."
- "When this works, the PoC demo at `/demo/profile` shows embedded profile data from API only, with /u/:username as visual parity check."
- "When this works, clicking Save on avatar settings updates the thumb on R2 and reflects on /u/Russ within one refresh."

---

## 10. Paste into Claude.ai (no terminal)

If you're not running ri-engine locally, paste **§2 + §4** at the start of the session, then **§3** when ready to execute.
