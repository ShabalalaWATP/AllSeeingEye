// Vendors the React Bits EvilEye component source into the repo so the app
// has no runtime dependency on reactbits.dev. Run: npm run vendor:eye
// The vendored files are then adapted locally (transparency + external cursor
// target); re-running this script will overwrite those adaptations.
import { mkdirSync, writeFileSync } from 'node:fs'

const REGISTRY_URL = 'https://reactbits.dev/r/EvilEye-TS-CSS'
const LICENCE_URL = 'https://raw.githubusercontent.com/DavidHDev/react-bits/main/LICENSE.md'
const DIR = 'src/renderer/src/components/EvilEye'

const res = await fetch(REGISTRY_URL)
if (!res.ok) {
  console.error(`Registry fetch failed: ${res.status}`)
  process.exit(1)
}
const json = await res.json()
mkdirSync(DIR, { recursive: true })
for (const f of json.files ?? []) {
  const name = f.path.split('/').pop()
  writeFileSync(`${DIR}/${name}.vendored`, f.content)
  console.log(`vendored ${name}.vendored (${f.content.length} bytes)`)
}
console.log('dependencies declared by registry:', JSON.stringify(json.dependencies ?? []))

try {
  const lic = await fetch(LICENCE_URL)
  if (lic.ok) {
    writeFileSync(`${DIR}/REACT-BITS-LICENSE.md`, await lic.text())
    console.log('vendored REACT-BITS-LICENSE.md')
  }
} catch {
  console.warn('licence fetch failed; copy it manually from the react-bits repo')
}
