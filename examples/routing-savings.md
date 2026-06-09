# Measured receipt: model-routing saved 67% cost at held capability

A live before/after of **Playbook A1 (right-size the model per task)**, measured with the meter in this
repo — **67% cost reduction at held capability**. Reproducible: the workflow is [`routing-demo.js`](routing-demo.js), run twice — `{route:false}`
(baseline) and `{route:true}` (routed).

**The task (identical in both runs):** four agents each extract one fact + key number from a short,
self-contained text (a mechanical, routable job), then one agent synthesizes a 4-bullet summary. The
only change between runs: in the routed run the four *extractor* agents run on a cheap model (Haiku);
the *synthesizer* stays on the strong model (Opus) in both.

## What the meter reported

**Baseline — all agents on Opus:**
```
routing-demo  wf_5ba026c3-250  status=completed  total=74,991 tok  ~$0.60  invariant_ok=True
  Extract           60,694   80.9%  ~$   0.49  n=4   ########################################
  Synthesize        14,297   19.1%  ~$   0.11  n=1   ##########
  ($ = estimate: list prices, 85%-input blend; telemetry has no I/O split)
```

**Routed — extractors on Haiku, synthesizer on Opus:**
```
routing-demo  wf_8e2be971-29e  status=completed  total=67,684 tok  ~$0.20  invariant_ok=True
  Extract           53,382   78.9%  ~$   0.09  n=4   #######################################
  Synthesize        14,302   21.1%  ~$   0.11  n=1   ###########
  ($ = estimate: list prices, 85%-input blend; telemetry has no I/O split)
```

## The result

| | Baseline | Routed | Δ |
|---|---|---|---|
| **Run cost** | ~$0.60 | ~$0.20 | **−$0.40 / −67%** |
| Extract stage | ~$0.49 | ~$0.09 | **−82% (~5.4× cheaper)** |
| Synthesize stage | ~$0.11 | ~$0.11 | unchanged (kept on Opus) ✓ |
| Tokens | 74,991 | 67,684 | −9.7% |

**Routing took effect** — the telemetry's per-agent `model` field flipped to Haiku for the extractors
and stayed Opus for the synthesizer; the meter prices each agent accordingly, so the win is isolated to
exactly the routed stage (the untouched synthesizer costs the same in both runs).

## Capability held

Both runs extracted **all four facts correctly** — Mars (Feb 18, 2021), Everest (8,849 m), Python 3.0
(Dec 3, 2008), Pacific (165M km² / ~10,935 m). The *only* difference: for the Pacific, the routed run
chose "165 million km²" as the headline number while the baseline chose the Mariana Trench depth — both
are true figures stated in the source text, a defensible judgment difference, not an error. No
hallucination, no dropped fact. Capability held.

## Honest framing

This is a **cost-axis** win, reported as such — it is **not** a token-count cut (the token count was
roughly flat, even slightly lower because Haiku was a touch terser). The savings come from a lower price
per token on a stage whose work didn't need the strong model. And the dollars are **estimates**: the
telemetry has no input/output split, so each agent's tokens are priced at its model's list rate via a
documented 85%-input blend — exactly right for *comparing* two runs, which is the point.

**The receipt:** *route mechanical sub-tasks to a cheap model → 67% lower run cost at held capability,
reproducible from `routing-demo.js`.* The same lever applied to the deep-research workflow's
~$3.53 page-fetch stage (see [`self-correction-deep-research.md`](self-correction-deep-research.md)) is
where this scales.
