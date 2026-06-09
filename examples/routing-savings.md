# Measured receipt: model-routing saved 76% cost at held capability

A live before/after of **Playbook A1 (right-size the model per task)**, measured with the meter in this
repo. Reproducible: the workflow is [`routing-demo.js`](routing-demo.js), run twice — `{route:false}`
(baseline) and `{route:true}` (routed).

**The task (identical in both runs):** four agents each extract one fact + key number from a short,
self-contained text (a mechanical, routable job), then one agent synthesizes a 4-bullet summary. The
only change between runs: in the routed run the four *extractor* agents run on a cheap model (Haiku);
the *synthesizer* stays on the strong model (Opus) in both.

## What the meter reported

**Baseline — all agents on Opus:**
```
routing-demo  status=completed  total=74,991 tok  ~$1.80  invariant_ok=True  (healthy)
  Extract     extract:mars     claude-opus-4-8     15,173 tok  ~$0.3642
  Extract     extract:everest  claude-opus-4-8     15,170 tok  ~$0.3641
  Extract     extract:python   claude-opus-4-8     15,168 tok  ~$0.3640
  Extract     extract:pacific  claude-opus-4-8     15,183 tok  ~$0.3644
  Synthesize  synthesize       claude-opus-4-8     14,297 tok  ~$0.3431
  STAGE Extract     ~$1.4567
  STAGE Synthesize  ~$0.3431
```

**Routed — extractors on Haiku, synthesizer on Opus:**
```
routing-demo  status=completed  total=67,684 tok  ~$0.43  invariant_ok=True  (healthy)
  Extract     extract:mars     claude-haiku-4-5-20251001  13,335 tok  ~$0.0213
  Extract     extract:everest  claude-haiku-4-5-20251001  13,377 tok  ~$0.0214
  Extract     extract:python   claude-haiku-4-5-20251001  13,333 tok  ~$0.0213
  Extract     extract:pacific  claude-haiku-4-5-20251001  13,337 tok  ~$0.0213
  Synthesize  synthesize       claude-opus-4-8            14,302 tok  ~$0.3432
  STAGE Synthesize  ~$0.3432
  STAGE Extract     ~$0.0854
```

## The result

| | Baseline | Routed | Δ |
|---|---|---|---|
| **Run cost** | ~$1.80 | ~$0.43 | **−$1.37 / −76.2%** |
| Extract stage | ~$1.4567 | ~$0.0854 | **−94% (~17× cheaper)** |
| Synthesize stage | ~$0.3431 | ~$0.3432 | unchanged (kept on Opus) ✓ |
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

**The receipt:** *route mechanical sub-tasks to a cheap model → 76% lower run cost at held capability,
reproducible from `routing-demo.js`.* The same lever applied to the deep-research workflow's
~$11 page-fetch stage (see [`self-correction-deep-research.md`](self-correction-deep-research.md)) is
where this scales.
