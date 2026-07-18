// Demo insurance: verifies the API key and model work BEFORE you present.
// Run: npm run preflight
import 'dotenv/config'
import OpenAI from 'openai'

const key = process.env.OPENAI_API_KEY
const model = process.env.OPENAI_MODEL ?? 'gpt-5.6-sol'

if (!key) {
  console.error('FAIL: OPENAI_API_KEY is not set. Copy .env.example to .env and add your key.')
  process.exit(1)
}

const client = new OpenAI({ apiKey: key, timeout: 30_000, maxRetries: 0 })
const started = Date.now()
try {
  const effort = process.env.OPENAI_REASONING_EFFORT
  const response = await client.responses.create({
    model,
    input: 'Reply with the single word OK.',
    store: false,
    ...(effort ? { reasoning: { effort } } : {})
  })
  const text = (response.output_text ?? '').trim().slice(0, 40)
  console.log(`OK  model=${model}  latency=${Date.now() - started}ms  output="${text}"`)
} catch (err) {
  const code = err?.code ?? err?.error?.code ?? err?.name ?? 'error'
  console.error(`FAIL  model=${model}  status=${err?.status ?? 'n/a'}  code=${code}`)
  if (err?.status === 404 || code === 'model_not_found') {
    console.error('The model is not available on this account. Set OPENAI_MODEL in .env.')
  }
  process.exit(1)
}
