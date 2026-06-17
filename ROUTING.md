# Model Routing: the enforcement layer for A1

*The meter tells you where tokens go. This is how you make the fix permanent — a case
study of adding a routing layer to a live agent fleet in one day, plus the reusable
module (`agent_cost_attribution/routing.py`) it produced.*

## The honest setup (read this before the numbers)

My fleet — a chat chief-of-staff agent, a research scout, and a handful of scheduled
routines (daily reply drafting, job sourcing, weekly research deep dives) — runs on a
fixed subscription budget where the binding constraint is a **weekly usage limit**, and
models burn that limit at very different rates (at list prices, blended, the premium
tier is ~10x the cheap tier and ~3x the standard tier per token).

The fleet **never had a routing layer**. Every call site hardcoded the premium tier:
Opus-class from launch, then swapped wholesale to the newest premium model one morning.
One call site carried **no model flag at all** and silently inherited the most
expensive configured default — the quietest failure mode in this repo (a second
unpinned site turned up later; see the QC section).

Hours after that swap, the burn showed up: **10% of the weekly budget gone with ~50
hours left to reset.** So the claim here is *not* "I cut costs 90%" — the all-premium
baseline was hours old and comparing against it would be a strawman. The claim is the
one that matters operationally: **time from cost regression to shipped, QC'd policy fix
was one day**, and the fleet now has a governance layer it never had. Measured deltas
come from the meter after real routed weeks, labeled with what the baseline actually was.

## What shipped (same day)

**1. The audit.** Two read-only agents mapped every model invocation: **11 call sites
across 2 repos** (serving 12 routed roles), 100% premium-pinned (or worse, unpinned),
zero routing capability, model strings baked into source at each site.

**2. One table.** Every call site now resolves through a single role table:

| Role | Tier | Why |
|---|---|---|
| chat (default) | standard | Q&A, status, drafting — escalates per message |
| chat_deep | premium | debugging, architecture, specs — on demand |
| search/extraction | cheap | mechanical; defensive parsing catches weak passes |
| drafting / digests / sourcing / pattern-mining | standard | writing is the standard tier's sweet spot |
| weekly research deep dive | mid-premium | the one research artifact that earns synthesis |
| **builds** | **premium, max effort — unchanged** | the workload that earns it |
| loop eval judge | premium | deliberately a *different* model than every producer it grades |

**3. Per-message escalation for chat.** Explicit `!tag` (stripped before the model sees
it) > imperative-only deep-work regex > cheap default. Tags beat heuristics because the
two failure modes are asymmetric: a missed escalation is recoverable (type `!deep`); a
false escalation silently burns budget forever.

**4. Live tuning without deploys.** A JSON overrides file merges over the table and
**fails soft** — a corrupt tuning file degrades to defaults rather than silencing a
production routine. Unknown roles **fail closed** (KeyError) so a typo surfaces instead
of routing somewhere quietly.

## What independent QC caught (why you don't grade your own work)

A different-model refute-first reviewer was run over the change before ship. It caught:

- **The escalation heuristic over-fired on status chatter.** "the migration finished
  overnight", "did the refactor land?", "postmortem went well" — six probe phrases all
  silently routed to the premium tier. The fix gates work verbs to imperative/request
  position; the reviewer's probes became the regression tests.
- **A 2nd unpinned call site the audit missed** — silently inheriting premium. Found by
  grepping for *absence* of a model flag, not presence of a model name. Audit your
  defaults, not just your constants.
- A second independent verifier re-checked both fixes (no self-grading on fixes either).

Cross-model judging is also load-bearing *inside* the fleet: the loop-eval judge that
grades autonomous work products is pinned to a different model family than every
producer it reviews. Same-family grading is weaker QC; the routing table enforces the
invariant and a test guards it.

## Receipts

- 11 call sites converted to 12 routed roles; 0 hardcoded model strings remain at any
  invocation site (the rule going forward: add a role, never a literal). The table's
  load-bearing invariants ARE test-enforced: builds stay premium, the judge differs
  from every producer it grades, the chat default is never the premium tier.
- 330 tests green at ship, including the reviewer's probe set.
- The decision log (kept/killed with real numbers) lives in the fleet's decision ledger.
- **Measured before/after (first routed week, 2026-06-09 → 06-16).** What the loop
  ledgers actually instrument is only the **weekly research deep-dive loops** — the one
  workload the table deliberately keeps near the top (mid-premium producer + a premium
  cross-model judge). So this is the *hardest* place to see a routing win, not the
  easiest: the cheap-tier moves (Haiku search/extraction, standard-tier drafting and
  sourcing) run in routines that don't write a per-call cost line anywhere I can read, so
  I can't measure them yet and won't assert them. MEASURED, from `total_cost_usd` in the
  loop ledgers (`state/loops/*.jsonl`, `state/ghost/loops/*.jsonl`), split at
  2026-06-09T23:45Z:
  - **Pre** (Jun 8–9, almost entirely the **Opus-class** era — the all-Fable swap was
    only hours old at the fix): 11 loop runs / 21 eval iterations, **$18.50 total**,
    **$0.88 / iteration**, **$1.68 / run**, 1.9 iterations/run.
  - **Post** (routed: 2 deep-dive runs, Jun 10 + Jun 15): 3 eval iterations,
    **$2.90 total**, **$0.97 / iteration**, **$1.45 / run**, 1.5 iterations/run.
  - **Honest read:** per-iteration cost on this workload is **flat** ($0.88 → $0.97),
    which is the *expected, designed* result — deep dive and judge were kept premium on
    purpose. The slight drop in cost/run and iterations/run is **inside the noise** at
    n=2 post-routing runs (the weekly routine fired ~once). The all-premium baseline was
    also hours old, so any cross-boundary total is a strawman; do not read the $18.50 →
    $2.90 total drop as a savings figure (different windows, different routine mix).
  - **Verdict: too thin and too biased to publish a savings number.** The instrumented
    sample is the premium-by-design tail, not the routed cheap path; one week gave two
    post runs. The defensible claim stays the operational one from the top of this doc
    (regression → shipped QC'd fix in a day). Real per-stage savings wait on a per-call
    cost line in the cheap-tier routines. ESTIMATES (never measurements) remain available
    from `routing.savings_estimate()`, fed with real volumes from the meter's waterfall.

## Use the module

```python
from agent_cost_attribution.routing import Router, MessageRouter

router = Router(ROLES, overrides_path=Path("routing.json"))
model = router.model_for("extract")                  # cheapest sufficient, centrally

chat = MessageRouter(router, tags=TAGS, deep_pattern=IMPERATIVE_ONLY_RE)
cfg, cleaned = chat.route(user_message)              # !tag > heuristic > cheap default
```

Design rules, each earned by a real failure above: one table, no literals at call
sites; unknown role fails closed; overrides fail soft; escalation is imperative-only
and tag-overridable; builds and judges keep the premium tier — capability is preserved
where it pays, removed where it was just the default.
