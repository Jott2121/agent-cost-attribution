# The Token-Efficiency Playbook for Agentic Coding

Practices for getting maximum capability per token out of agentic workflows. Each is rated honestly,
reported on the correct **axis**, and **never double-counted**:

- **Token-count axis** — fewer tokens processed (the headline number).
- **Cost axis** — same tokens, cheaper per token (model routing, prompt caching). Real savings, but
  reported separately; never folded into the token-count headline.
- **Latency axis** — faster wall-clock (often a free side effect of the above).

Two rules underpin everything: **measure before you cut** (use the meter in this repo), and **gate on
capability** — a savings that drops answer quality isn't a savings, it's a regression. Verify each
change with a paired before/after on a fixed set of tasks, and keep the change only if quality holds.

---

## Tier A — Operating practices (broadest, cheapest, biggest day-to-day wins)

### A1. Right-size the model per task
**What:** Run mechanical sub-tasks (file edits, format conversions, search, extraction, boilerplate
review) on a cheaper/faster model; reserve the strongest model for judgment, design, and synthesis.
**Why:** Most sub-tasks in a coding workflow don't need the top model. Industry framing: model
**routing / cascades** (cf. *RouteLLM*, *FrugalGPT*).
**How:** Set the per-agent/per-call model explicitly instead of inheriting the session default. In a
fan-out, route the "doer" agents down a tier and keep the "judge"/"synthesizer" on top.
**Savings:** ~30–80% **cost** on the routed slice · *axis: cost (not token-count)* · risk: low *if* the
routed task is mechanical and its output is checked downstream · effort: small.
**Concrete:** in a real measured run the page-fetch stage cost **~$10.60** on the top model; those same
tokens on a cheap model ≈ **$0.71** — the meter prices per-agent, so the routing win is visible at once.
**Caveat:** Never route the *judge* down — a weak judge's failure mode is confidently approving wrong
work (see C3). And confirm the runtime actually honors a per-call model override (it's observable in
the run telemetry — the meter shows each agent's model).

### A2. Fan out only for read-heavy parallel work; keep writes single-threaded
**What:** Spawn parallel sub-agents for independent *reads* (search, audit, multi-file exploration).
Do not parallelize writes, and don't spawn agents that duplicate each other's work.
**Why:** Parallel readers cut wall-clock for free; parallel writers create conflicts and rework
(rework is pure wasted tokens).
**Savings:** latency-dominant; token savings come from *not* re-doing conflicted work · axis: latency +
avoided-waste · risk: low · effort: small.

### A3. Scope context tightly
**What:** Read only the slice of a file you need (not the whole file); don't re-read what's already in
context; hand a sub-agent exactly the context it needs, not your entire session history.
**Why:** Input tokens dominate most agentic runs. Re-reading and over-wide context is the quietest,
largest leak.
**Savings:** 10–40% **token-count** on context-heavy work · axis: token-count · risk: low (don't
under-scope to the point the agent lacks what it needs) · effort: small, mostly discipline.

### A4. Prompt caching
**What:** Structure prompts so a large, stable prefix (system instructions, schema, task framing) is
byte-identical across calls and can be cache-read; put the variable part at the end.
**Why:** Repeated fan-out calls share a big scaffold. Industry framing: prompt/context caching
(cf. *GPTCache*-style ideas applied to a fixed prefix).
**Savings:** up to ~90% **cost** on the cached prefix tokens · axis: cost · risk: none · effort: small.
**Caveat:** caches have a short TTL — claim within-run/back-to-back hits, not cross-day. And you can't
honestly claim it unless your telemetry exposes cache-read tokens; if it doesn't, mark it
"designed, not measured."

### A5. Structured outputs / bounded verbosity
**What:** Constrain outputs with a schema and a length budget where the downstream consumer only needs
the structured fields, not prose.
**Why:** Output tokens compound across large fan-outs (e.g. dozens of verifier verdicts).
**Savings:** small but real, multiplied by fan-out width · axis: token-count (output) · risk: low —
don't strip reasoning a stage genuinely needs · effort: small.

---

## Tier B — Workflow-design practices

### B1. Don't re-gather redundantly (gather once, use N times)
**What:** If N agents each independently fetch/search the same evidence to judge the same item, gather
the evidence **once** and share it across the N judges.
**Why:** Redundant retrieval is often the single largest cost in a verification/voting stage — each
voter re-running its own search is N× the retrieval bill for one item.
**Savings:** can be very large when a verify/vote stage dominates (it often does) · axis: token-count ·
risk: low–medium (shared evidence slightly correlates the judges' blind spots — keep N independent
*judgments*, just one *retrieval*) · effort: medium.

### B2. Kill junk cheaply before expensive stages
**What:** Put a cheap, deterministic, **one-directional** pre-screen (can only *drop* or *pass*, never
*confirm*) in front of an expensive stage: a substring/quote check, a source-quality floor, a
staleness check.
**Why:** Spending the expensive stage on items a one-line check could have dropped is pure waste.
One-directional means it can never *cause* a bad result — only save work.
**Savings:** scales with junk rate · axis: token-count · risk: low (it can only drop, never approve) ·
effort: medium.

### B3. Dedup inputs before expensive stages
**What:** Before an expensive fan-out, drop near-duplicate inputs (same URL, near-identical
title+snippet). A cheap Jaccard/`set` overlap is plenty — no embeddings needed.
**Savings:** proportional to duplication in your input pool · axis: token-count · risk: low (you're
dropping redundant copies) · effort: small.

### B4. Make your caps actually cap
**What:** Audit every "limit" in your workflow. A budget that high-priority items silently bypass
isn't a cap. (Real bug found with this meter: a `MAX_FETCH=15` that high-relevance sources skipped —
real fan-out was 19–24.)
**Why:** Phantom caps are invisible overspend; you think you're bounded and you're not.
**Savings:** the gap between your assumed cap and the real fan-out · axis: token-count · risk: low ·
effort: small.

---

## Tier C — Measurement discipline (the meta-practices that make the rest credible)

### C1. Meter every run, attribute per stage
**What:** Decompose each run's tokens per stage before optimizing. Optimize the actual cost center, not
the one you assume. (This is what the tool in this repo does.)
**Why:** The headline finding of this whole project was that the assumed cost center was wrong. Don't
optimize on a guess.

### C2. Catch silently-degraded runs
**What:** Check per-stage health, not the run's self-reported status. Flag stages whose agents errored
or ran anomalously cheap. (The meter's `detect_degradation` does this.)
**Why:** A run's status flag lies in both directions. A "successful" run with a crashed stage produces
a cost profile that will mislead every optimization decision you make from it.

### C3. Refuse the unsafe shortcut — and prove the refusal with numbers
**What:** Some "savings" trade away capability: cheapening the *judge*, dropping adversarial coverage
on confident-looking claims, trusting an upstream cheap model's output as ground truth without a check.
Build the tempting-but-unsafe version, **measure the quality drop**, and document why you refused it.
**Why:** A measured rejection is more credible than a feature. It proves you optimized for capability,
not just a smaller number.

---

## Considered and rejected (discernment, not buzzwords)

- **Speculative decoding** — cuts *latency*, not billed tokens, and lives below the API surface. Not a
  token-efficiency lever for application-level agentic work.
- **Ultra-compact output encodings (e.g. TOON-style)** — trims *output* tokens, but agentic coding is
  *input*-dominated; output is a rounding error. <1% on these workloads.

Naming a real technique and explaining why it *doesn't* apply here is part of the method.

---

## How to apply this

1. Run the meter on a representative workflow run → find your real cost center (Tier C1).
2. Confirm the run is healthy (Tier C2) before you trust its numbers.
3. Pick the highest-leverage practice for *that* cost center (usually Tier B if a verify/fan-out stage
   dominates, Tier A otherwise).
4. Make a paired before/after run, measure with the meter, and check quality held. Keep it only if it
   did. Report the win on the correct axis.
5. Write down what you killed, not just what you kept.
