# agent-cost-attribution

[![CI](https://github.com/Jott2121/agent-cost-attribution/actions/workflows/ci.yml/badge.svg)](https://github.com/Jott2121/agent-cost-attribution/actions/workflows/ci.yml)
[![CodeQL](https://github.com/Jott2121/agent-cost-attribution/actions/workflows/codeql.yml/badge.svg)](https://github.com/Jott2121/agent-cost-attribution/actions/workflows/codeql.yml)
[![Coverage](https://raw.githubusercontent.com/Jott2121/agent-cost-attribution/python-coverage-comment-action-data/badge.svg)](https://github.com/Jott2121/agent-cost-attribution/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)

**Get the most capability per token out of agentic coding, and prove it. Headline result, measured by the meter in this repo: routing four mechanical agents to a cheap model cut run cost 67% (~$0.60 → ~$0.20) with identical facts extracted ([receipt](https://github.com/Jott2121/agent-cost-attribution/blob/main/examples/routing-savings.md)).**

Agentic workflows (fan-out subagents, multi-step research, tool-heavy pipelines) burn tokens fast,
and most of the waste is invisible. You can't fix what you can't see, and the platform's own "success"
flag is wrong more often than you'd think.

> 🧩 One layer of a five-repo [**cost-governance stack**](https://github.com/Jott2121/bow#the-system-a-cost-governance-stack) for operating AI agents cost-efficiently; [bow](https://github.com/Jott2121/bow) is the flagship that runs every layer in production.

This repo is two things:

1. **`agent_cost_attribution`**: a tiny, dependency-free **meter**. Point it at a workflow run's
   telemetry and get a per-stage token waterfall, plus a **silent-degradation check** that flags runs
   that *reported success while quietly breaking*.
2. **[PLAYBOOK.md](https://github.com/Jott2121/agent-cost-attribution/blob/main/PLAYBOOK.md)**: a playbook of transferable practices for cutting token burn in
   agentic coding **without losing capability**, each rated by expected savings, axis (tokens vs cost
   vs latency), capability risk, and effort.

Everything here is **measured, not asserted**. The numbers in this repo were produced by the meter
included here; point it at your own telemetry to do the same.

## Try it in 30 seconds (zero dependencies, sample included)

```bash
git clone https://github.com/Jott2121/agent-cost-attribution
cd agent-cost-attribution
python3 -m agent_cost_attribution examples/sample-run.json
```

Output (from the synthetic sample shipped in [`examples/sample-run.json`](https://github.com/Jott2121/agent-cost-attribution/blob/main/examples/sample-run.json)):

```
sample-research  wf_sample-001  status=completed  total=1,006,200 tok  ~$3.92  invariant_ok=True
  Verify           720,748   71.6%  ~$   3.46  n=12  ####################################
  Search           254,248   25.3%  ~$   0.41  n=6   #############
  Scope             31,204    3.1%  ~$   0.05  n=1   ##
  ($ = estimate: list prices, 85%-input blend; telemetry has no I/O split)
```

Then point it at your own runs:

```bash
python3 -m agent_cost_attribution path/to/run.json
python3 -m agent_cost_attribution path/to/runs-dir/      # every wf_*.json in a directory
```

**Where does `run.json` come from?** The meter reads Claude Code workflow telemetry: the `wf_*.json`
files that Claude Code writes automatically when you run agentic workflows, found under
`~/.claude/projects/*/tasks/`. If you run Claude Code workflows, you already have these files; no
instrumentation, SDK, or proxy is required. The shipped sample is synthetic but format-exact, so you
can see the output before you have telemetry of your own.

You get three things per run: **tokens**, an estimated **dollar cost**, and a **trust check**.

- **`invariant_ok`** means the per-agent token counts sum **exactly** to the run total. The parser is
  checking itself, so you can believe the breakdown.
- The **`~$` figures are estimates**: each agent's tokens are priced at its model's list price using a
  documented input/output blend (the telemetry exposes only a single token count, no I/O split), so read
  them as a calibrated band, not a billing statement. Because they're priced **per agent**, a
  model-routing win shows up directly (route a stage to a cheaper model and its `~$` drops).
- A **`DEGRADED`** banner appears when a stage errored or ran anomalously cheap. Cost numbers on a
  degraded run aren't trustworthy and shouldn't be published.

## How this differs from Langfuse / Helicone

Langfuse, Helicone, and similar LLM observability platforms are excellent at what they do: they sit
in your request path (SDK or proxy), capture every call, and give you dashboards over time. This tool
is deliberately the opposite shape. It is a **post-hoc forensic meter**: a single stdlib-only Python
package, no server, no account, no instrumentation, that reads telemetry files the platform already
wrote and answers two narrow questions per run: *which stage of this multi-agent workflow ate the
tokens*, and *can I trust this run's numbers at all* (the invariant check plus silent-degradation
detection). If you want fleet-wide dashboards, use those platforms. If you want to audit one run's
cost attribution in 30 seconds with zero setup, use this.

## The headline finding (why you should trust the method)

I built this meter to support an optimization plan I'd already written. **The meter overturned my own
plan.** I had assumed the token whale was the page-**Fetch** stage; the telemetry showed it was the
**Verify** stage (50-74% of healthy runs vs Fetch's ~19-37%). The "expensive" run I'd anchored my
baseline on turned out to be a **silently broken outlier**: it reported `status=completed` while all
75 of its verifier agents had errored, which is the *only* reason Fetch looked dominant there.

Along the way the meter also showed the platform's own status flag was unreliable in **both**
directions: one run said `completed` but was broken; another said `failed` but was perfectly healthy.
The lesson, and the reason the silent-degradation check exists: **trust per-stage health, not the
run's self-report.** Full numbers in [`examples/self-correction-deep-research.md`](https://github.com/Jott2121/agent-cost-attribution/blob/main/examples/self-correction-deep-research.md).

Measurement that kills your own hypothesis is the whole point. The rest of this repo is built on it.

## The playbook (TL;DR; full version in [PLAYBOOK.md](https://github.com/Jott2121/agent-cost-attribution/blob/main/PLAYBOOK.md))

- **Right-size the model per task**: mechanical sub-tasks on a cheap model, judgment/synthesis on the
  strong one. (This repo's own builder/reviewer agents ran on the cheaper tier.)
- **Fan out only for read-heavy parallel work; keep writes single-threaded.**
- **Scope context tightly**: read the slice you need, don't re-read, hand a sub-agent only what it needs.
- **Don't re-gather redundantly · kill junk cheaply before expensive stages · dedup inputs · make your caps actually cap.**
- **Prompt caching · structured outputs.**
- **Meter every run · gate on quality · refuse the unsafe shortcut and prove it.**

Each practice is reported on the right axis and **never double-counted** (routing changes cost-per-token,
not token *count*; caching is a cost-axis win; only genuine token-count reductions go on the headline).

**Measured proof:** [`examples/routing-savings.md`](https://github.com/Jott2121/agent-cost-attribution/blob/main/examples/routing-savings.md), a live before/after
where routing four mechanical agents to a cheap model cut run cost **67% (~$0.60 to ~$0.20)** with
identical facts extracted, isolated by the meter to exactly the routed stage. Reproducible from
[`examples/routing-demo.js`](https://github.com/Jott2121/agent-cost-attribution/blob/main/examples/routing-demo.js).

## Making A1 stick: the routing layer ([ROUTING.md](https://github.com/Jott2121/agent-cost-attribution/blob/main/ROUTING.md))

Right-sizing the model per task fails in practice when the model is a string literal at N call
sites: one unpinned call silently inherits your most expensive default. [ROUTING.md](https://github.com/Jott2121/agent-cost-attribution/blob/main/ROUTING.md)
is the case study of retrofitting a live agent fleet (11 call sites, zero routing, all premium-pinned)
with a central role table, per-message escalation (`!tag` > imperative-only heuristic > cheap
default), fail-soft live tuning, and an independent cross-model QC pass that caught the policy's own
over-escalation bug before ship. Audited, built, and live in one day. The reusable module is
[`agent_cost_attribution/routing.py`](https://github.com/Jott2121/agent-cost-attribution/blob/main/agent_cost_attribution/routing.py) (stdlib-only, like the meter):
`Router` (fail-closed roles, fail-soft overrides), `MessageRouter` (chat escalation), and
`savings_estimate()` (planning estimates from the meter's real volumes; labeled estimates, never
published as measurements).

## What's here

```
README.md      - this file
PLAYBOOK.md    - the practices, each with what / why / how / savings / risk
ROUTING.md     - case study + design rules: retrofitting model routing onto a live fleet in a day
agent_cost_attribution/   - the meter (stdlib-only): ledger, health, cli, plus routing.py (A1's enforcement layer)
tests/         - the meter's tests (the sum==total invariant is golden-tested)
examples/      - measured worked examples + sample-run.json (synthetic quickstart telemetry)
pyproject.toml - package metadata + pytest config
.github/       - CI (pytest on Python 3.9-3.12 + a smoke run of the meter on the sample)
LICENSE        - MIT
```

## Who it's for

Anyone running agentic workflows who wants maximum capability per token, and a way to *find their own
waste* instead of guessing. It's also a worked demonstration of rigorous, measured agentic-coding
practice: measure, attribute, gate on quality, publish what you kept *and* what you killed.

## Reliability & security

A meter people trust has to be measured itself, so the repo is gated:

- **Coverage-gated test matrix** — pytest on Python 3.9–3.12, build fails below the coverage floor (currently 96% covered), plus a smoke-test of the meter on the shipped sample run.
- **CodeQL** — `security-extended` static analysis on every push, PR, and weekly; findings surface in the Security tab.
- **Pinned supply chain** — GitHub Actions pinned to commit SHAs, kept current by **Dependabot**.
- **Branch protection** — `main` requires CI + CodeQL to pass before a merge.
- **Disclosure policy** — see [SECURITY.md](https://github.com/Jott2121/agent-cost-attribution/blob/main/SECURITY.md); private reporting is enabled.

## About

Built by **Jeff Otterson** ([Jott2121](https://github.com/Jott2121)). Part of the Fleet Mode line:
[**bow**](https://github.com/Jott2121/bow) (the flagship agent case study) ·
[**fleet-mode**](https://github.com/Jott2121/fleet-mode) (the orchestration doctrine as a live skill) ·
[**agent-gate**](https://github.com/Jott2121/agent-gate) · [**rag-guard**](https://github.com/Jott2121/rag-guard) ·
[**sabot**](https://github.com/Jott2121/sabot) (own-checks fault detection — its silent
model-downgrade operator grew out of the degraded-run detector in this repo).
The same discipline throughout: measure it, gate it, keep the receipts.

## License

MIT, see [LICENSE](https://github.com/Jott2121/agent-cost-attribution/blob/main/LICENSE).
