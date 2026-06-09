# Worked example: the meter overturned my own optimization plan

This is the example that motivated the whole repo. It uses the meter in this repo on a set of real
runs of a deep-research workflow (Scope → Search → Fetch → Verify → Synthesize, ~100 agents/run). You
can run the same meter on your own runs.

## The hypothesis (before measuring)

I wrote an optimization plan that assumed the token "whale" was the **Fetch** stage — the ~15–20 agents
that each pull a full web page into context. The plan's two biggest levers both targeted Fetch. I
anchored the baseline on a specific ~738K-token run where Fetch was **66%** of all tokens. Case closed,
or so I thought.

## What the meter actually found

Decomposing the runs per stage (the parser self-checks: per-agent tokens sum **exactly** to the run
total) flipped the conclusion.

**The 738K "anchor" run — flagged DEGRADED:**

```
deep-research  <broken-run>  status=completed  total=738,087  invariant_ok=True
  Fetch            490,309   66.4%  n=19
  Verify           119,111   16.1%  n=75
  Search           113,259   15.3%  n=5
  Scope             15,408    2.1%  n=1
  ! DEGRADED — cost numbers on this run are NOT publishable:
      [high] Verify: errors — 75/75 agents in state 'error'
      [high] Verify: cheap — mean 1588 tok/agent over 75 agents < 25% of run median 19030
```

Fetch only looked dominant because **all 75 verifier agents had errored** — each spent a tiny ~1,588
tokens instead of the normal ~8–24K. The run reported `status=completed`. It was not complete; it was
broken, and it was the cheapest, most abnormal run in the set. A discrediting baseline.

**A healthy run, by contrast:**

```
deep-research  <healthy-run>  status=failed  total=1,192,692 tok  ~$28.62  invariant_ok=True
  Verify           601,658   50.4%  ~$  14.44  n=75  #########################
  Fetch            441,697   37.0%  ~$  10.60  n=24  ##################
  Search           134,608   11.3%  ~$   3.23  n=6   ######
  Scope             14,729    1.2%  ~$   0.35  n=1   #
  Synthesize             0    0.0%  ~$   0.00  n=1
  ($ = estimate: list prices, 85%-input blend; telemetry has no I/O split)
```

In dollars (list-price estimate): this single run is **~$29** — Verify ~$14, Fetch ~$11. That reframes
the levers: routing Fetch's 442K tokens to a cheap model would cut that stage from ~$10.60 to ~$0.71,
but the bigger prize is the **~$14 Verify stage** — and the honest fix there (gather evidence once,
keep three independent judges) is worth more than squeezing Fetch.

**Verify is the whale — not Fetch.** Across the healthy runs, Verify ran **50–74%** of total tokens
(72–74% on the fully-completed ones) while Fetch was a stable **~19–37%**. The cause: every verifier
runs its *own* web search, so a 3-vote verification stage pays the retrieval bill three times per claim.

My plan's Fetch levers were aimed at a ~25% stage. Even a *perfect* Fetch lever is capped below the
Fetch share — it could never reach the savings I'd promised. The real money is in the Verify stage, and
the highest-leverage fix is **gathering evidence once and sharing it across the three judges** (Playbook
B1) rather than cheapening the judge (which Playbook C3 explicitly refuses).

## The status flag lies in both directions

Note the two runs above: the **broken** one reported `status=completed`; the **healthy** one reported
`status=failed`. The platform's own status flag was wrong both ways. A third run in the set had a
stalled Search stage (all search agents returned 0 tokens) that its status also didn't surface. This is
why the meter checks **per-stage health**, not the run's self-report — and why you should never publish
a cost number from a run you haven't health-checked.

## The takeaways

1. **Measure before you optimize.** The assumed cost center was wrong; a 20-line decomposition
   corrected a plan I was about to spend heavily executing.
2. **Health-check before you trust a number.** A "successful" run with a crashed stage produces a cost
   profile that misleads every downstream decision.
3. **The biggest lever lives in the stage you measure to be the whale** — here, verification — and the
   honest fix preserves capability (share retrieval, keep independent judgments) instead of cheapening
   the judge.

Run `python3 -m agent_cost_attribution <your-run.json>` on your own workflows and see where *your*
tokens actually go.
