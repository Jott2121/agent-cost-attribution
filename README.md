# agent-cost-attribution

**Get the most capability per token out of agentic coding — and prove it.**

Agentic workflows — fan-out subagents, multi-step research, tool-heavy pipelines — burn tokens fast,
and most of the waste is invisible. You can't fix what you can't see, and the platform's own "success"
flag is wrong more often than you'd think.

This repo is two things:

1. **`agent_cost_attribution`** — a tiny, dependency-free **meter**. Point it at a workflow run's
   telemetry and get a per-stage token waterfall, plus a **silent-degradation check** that flags runs
   that *reported success while quietly breaking*.
2. **[PLAYBOOK.md](PLAYBOOK.md)** — a playbook of transferable practices for cutting token burn in
   agentic coding **without losing capability**, each rated by expected savings, axis (tokens vs cost
   vs latency), capability risk, and effort.

Everything here is **measured, not asserted** — the numbers in this repo were produced by the meter
included here; point it at your own telemetry to do the same.

## Run it on your own runs (30 seconds, zero dependencies)

```bash
python3 -m agent_cost_attribution path/to/run.json
python3 -m agent_cost_attribution path/to/runs-dir/      # every run in a directory
```

Sample output:

```
deep-research  <run-id>  status=failed  total=1,192,692 tok  ~$28.62  invariant_ok=True
  Verify           601,658   50.4%  ~$  14.44  n=75  #########################
  Fetch            441,697   37.0%  ~$  10.60  n=24  ##################
  Search           134,608   11.3%  ~$   3.23  n=6   ######
  Scope             14,729    1.2%  ~$   0.35  n=1   #
  Synthesize             0    0.0%  ~$   0.00  n=1
  ($ = estimate: list prices, 85%-input blend; telemetry has no I/O split)
```

You get three things per run: **tokens**, an estimated **dollar cost**, and a **trust check**.

- **`invariant_ok`** means the per-agent token counts sum **exactly** to the run total — the parser is
  checking itself, so you can believe the breakdown.
- The **`~$` figures are estimates**: each agent's tokens are priced at its model's list price using a
  documented input/output blend (the telemetry exposes only a single token count, no I/O split), so read
  them as a calibrated band, not a billing statement. Because they're priced **per agent**, a
  model-routing win shows up directly (route a stage to a cheaper model → its `~$` drops).
- A **`DEGRADED`** banner appears when a stage errored or ran anomalously cheap — cost numbers on a
  degraded run aren't trustworthy and shouldn't be published.

## The headline finding (why you should trust the method)

I built this meter to support an optimization plan I'd already written. **The meter overturned my own
plan.** I had assumed the token whale was the page-**Fetch** stage; the telemetry showed it was the
**Verify** stage (50–74% of healthy runs vs Fetch's ~19–37%). The "expensive" run I'd anchored my
baseline on turned out to be a **silently broken outlier** — it reported `status=completed` while all
75 of its verifier agents had errored, which is the *only* reason Fetch looked dominant there.

Along the way the meter also showed the platform's own status flag was unreliable in **both**
directions: one run said `completed` but was broken; another said `failed` but was perfectly healthy.
The lesson, and the reason the silent-degradation check exists: **trust per-stage health, not the
run's self-report.** Full numbers in [`examples/self-correction-deep-research.md`](examples/self-correction-deep-research.md).

Measurement that kills your own hypothesis is the whole point. The rest of this repo is built on it.

## The playbook (TL;DR — full version in [PLAYBOOK.md](PLAYBOOK.md))

- **Right-size the model per task** — mechanical sub-tasks on a cheap model, judgment/synthesis on the
  strong one. (This repo's own builder/reviewer agents ran on the cheaper tier.)
- **Fan out only for read-heavy parallel work; keep writes single-threaded.**
- **Scope context tightly** — read the slice you need, don't re-read, hand a sub-agent only what it needs.
- **Don't re-gather redundantly · kill junk cheaply before expensive stages · dedup inputs · make your caps actually cap.**
- **Prompt caching · structured outputs.**
- **Meter every run · gate on quality · refuse the unsafe shortcut and prove it.**

Each practice is reported on the right axis and **never double-counted** (routing changes cost-per-token,
not token *count*; caching is a cost-axis win; only genuine token-count reductions go on the headline).

**Measured proof:** [`examples/routing-savings.md`](examples/routing-savings.md) — a live before/after
where routing four mechanical agents to a cheap model cut run cost **76% (~$1.80 → ~$0.43)** with
identical facts extracted, isolated by the meter to exactly the routed stage. Reproducible from
[`examples/routing-demo.js`](examples/routing-demo.js).

## What's here

```
README.md      — this file
PLAYBOOK.md    — the practices, each with what / why / how / savings / risk
agent_cost_attribution/   — the meter (stdlib-only): ledger, health, cli
tests/         — the meter's tests (the sum==total invariant is golden-tested)
examples/      — measured worked examples
LICENSE        — MIT
```

## Who it's for

Anyone running agentic workflows who wants maximum capability per token — and a way to *find their own
waste* instead of guessing. It's also a worked demonstration of rigorous, measured agentic-coding
practice: measure → attribute → gate on quality → publish what you kept *and* what you killed.

## License

MIT — see [LICENSE](LICENSE).
