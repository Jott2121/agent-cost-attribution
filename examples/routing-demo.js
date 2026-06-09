export const meta = {
  name: 'routing-demo',
  description: 'Cheap before/after demo: route mechanical extractor agents to a cheap model, then measure token/$/quality with the meter.',
  phases: [
    { title: 'Extract', detail: '4 agents each extract one fact+number (mechanical → routable)' },
    { title: 'Synthesize', detail: '1 agent merges (stays on the strong model in both runs)' },
  ],
}

// args: { route: boolean }. route=false → all agents on the default (strong) model = BASELINE.
// route=true → the mechanical Extract agents run on a cheap model (haiku); Synthesize stays strong.
// (Workflow passes scriptPath args as a JSON string, so parse defensively — see the meter's harness fix.)
let A = args
if (typeof A === 'string') { try { A = JSON.parse(A) } catch { A = {} } }
if (!A || typeof A !== 'object') A = {}
const ROUTE = A.route === true
const DOER = ROUTE ? { model: 'haiku' } : {}   // spread into opts; absent → inherits the default model

// Fixed, self-contained inputs (no web fetch → cheap + deterministic). Each states one clear fact + number.
const BLURBS = [
  { id: 'mars',    text: "NASA's Perseverance rover landed in Jezero Crater on Mars on February 18, 2021, to search for signs of ancient microbial life and cache rock samples." },
  { id: 'everest', text: "Mount Everest stands 8,849 meters above sea level, making it Earth's highest peak; it lies on the border between Nepal and the Tibet Autonomous Region of China." },
  { id: 'python',  text: "Python 3.0 was released on December 3, 2008. It was a backwards-incompatible release that, among other changes, turned print into a function." },
  { id: 'pacific', text: "The Pacific Ocean is the largest and deepest of Earth's oceans, covering roughly 165 million square kilometers, with the Mariana Trench reaching about 10,935 meters deep." },
]

const EXTRACT_SCHEMA = {
  type: 'object',
  required: ['subject', 'key_fact', 'number'],
  properties: {
    subject: { type: 'string' },
    key_fact: { type: 'string', description: 'one precise sentence' },
    number: { type: 'string', description: 'the single most important figure, with its unit/date' },
  },
}

phase('Extract')
const extractions = (await parallel(BLURBS.map(b => () =>
  agent(
    "Extract the single most important fact and the key number from the text below. Be precise and literal — do not add anything not stated.\n\n" +
    "TEXT:\n" + b.text + "\n\n" +
    "Return: subject (short), key_fact (one sentence), number (the most important figure with its unit or date).",
    { label: 'extract:' + b.id, phase: 'Extract', schema: EXTRACT_SCHEMA, ...DOER }
  ).then(r => r ? { id: b.id, ...r } : null)
))).filter(Boolean)

phase('Synthesize')
const summary = await agent(
  "Combine these extracted facts into exactly four bullets, one per subject, each stating the fact and citing its number.\n\n" +
  JSON.stringify(extractions, null, 1) + "\n\nReturn just the four bullets.",
  { label: 'synthesize', phase: 'Synthesize' }   // no model override → strong model in BOTH runs
)

return { route: ROUTE, extractions, summary }
