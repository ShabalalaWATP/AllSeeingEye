# Visual direction

Status: draft for Alex's approval, 18 October 2026. Extracted from
`frontend/src/features/product/product.css`, the `story-*.css` files,
`frontend/src/styles/theme.css` and `frontend/src/lib/categories.ts`.

## Fixed dark palette

The page renders outside the app shell on a palette named once on `.product-story`
(`product.css`). It sets `color-scheme: dark` and redefines the app's `--color-*`
tokens locally, so shared components (brand mark, pause control) read the story
palette. The page stays dark whatever theme a signed-in visitor has chosen, and
the motion control stores a device choice only.

| Token | Value | Role | Obsidian (`theme.css`) |
| --- | --- | --- | --- |
| `--story-ground` | `#060606` | Page ground; same as the sign-in screen (`features/auth/auth.css`) | `#07070b` |
| `--story-ground-2` | `#0b0a0f` | Recessed panels, phone, export cards | |
| `--story-surface` | `#121118` | Cards, chips, panels | `#14141c` |
| `--story-surface-2` | `#1a1922` | Raised panels, console, toasts | `#1c1c26` |
| `--story-line` | `#2a2833` | Borders and rules | `#2a2a36` |
| `--story-text` | `#ece7df` | Body text | `#e9e4dc` |
| `--story-muted` | `#a29daa` | Secondary text | `#9a95a3` |
| `--story-ember` | `#ff6f37` | Accent, eyebrows, focus ring, primary button | `#ff6f37` |
| `--story-ember-glow` | `#ff6f3740` | Button shadow, orbit core, contact glow, thread glow | |
| `--story-ember-faint` | `#ff6f3714` | Selected chip and depth fill, grade legend | |
| `--story-cyan` | `#22d3ee` | Collect arcs | `#22d3ee` |
| `--story-amber` | `#f5b53f` | Likelihood bands, challenge, gap card, limits, progress gradient end | `#f5b53f` |
| `--story-good` | `#5cd39b` | "Ready" status, "Saved as version 1" | `#5cd39b` |
| `--story-critical` | `#ff5a5a` | Estimator validation errors | `#ff5a5a` |
| `--story-grid` | `#ffffff0b` | Hero background grid | |
| `--story-shadow` | `#000000cc` | Console and phone drop shadows | |
| `--color-control-border` | `#6b6875` | Form controls (3:1 against surfaces) | `#6b6875` |

The accent, status and control-border colours equal Obsidian exactly. The neutrals
are close to Obsidian but not equal. The `product.css` comment says the palette
matches the sign-in screen and Obsidian; in the code only the ground equals the
sign-in screen.

**Difference from the ticket:** KAN-171 asks for "a dark-first cinematic palette with
a light-theme fallback". The build has no light fallback; KAN-170 requires the page
to stay dark. Alex should confirm which applies. One small gap: while `/api/site` is
loading, `ProductPage.tsx` renders a shell with the app's `bg-ground` class outside
`.product-story`, which would follow the document's theme if one were applied. Not
checked in a browser.

## Typefaces

Both are self-hosted through Fontsource (`theme.css`); nothing is fetched at runtime.

- **Inter** (`--font-sans`, `'Inter Variable', 'Inter'`): all text and diagram labels.
- **JetBrains Mono** (`--font-mono`, weights 400 and 600): eyebrows, chips, counts,
  grades, receipts, timeline days, scope labels and captions, usually uppercase with
  0.08em to 0.22em tracking.

| Style | Size | Weight and tracking |
| --- | --- | --- |
| Hero title | `clamp(3rem, 8.5vw, 8.5rem)`, line height 0.92 | 650, −0.065em, ember full stop |
| Chapter title | `clamp(2rem, 4.2vw, 3.75rem)`, line height 1.02 | 650, −0.045em, balanced wrap |
| Subtitle | `clamp(1.5rem, 2.6vw, 2.25rem)` | 600, −0.03em |
| Lead | `clamp(1rem, 1.25vw, 1.2rem)`, line height 1.6, max 40rem | muted |
| Eyebrow | 0.75rem mono | 600, 0.22em, uppercase, ember |
| Footnote | 0.8125rem, line height 1.5 | muted |

## Layer and topic colours

Data colours come from `CATEGORY_STYLES` in `lib/categories.ts`, the same table the
globe, legends and event lists use.

| Topic (`categories.ts`) | Colour | Used for on the page |
| --- | --- | --- |
| Disasters | `#ff6f37` | Natural hazards layer, topic node and bar |
| Conflict & unrest | `#ff5a5a` | Conflict layer, topic |
| News | `#e9e4dc` | News layer, topic |
| Aviation | `#f5b53f` | Flights layer, topic |
| Maritime | `#5cd39b` | Boats layer, topic |
| Space | `#a78bfa` | Space layer, topic |
| Cyber | `#22d3ee` | Cyber layer, topic |
| Social | `#f472b6` | Topic |
| Political | `#94a3b8` | Topic |
| Humanitarian | `#fbbf24` | Topic |
| Economic | `#6ee7b7` | Topic |

Layers without a category use literal values in `content/observe.ts`, described there
as mirrored from the globe's filter panels:

| Layer | Colour | Check against globe code |
| --- | --- | --- |
| Fires and thermal detections | `#ffb15a` | Not matched in this check |
| Public cameras | `#62debe` | Matches `[98, 222, 190]` in `features/globe/cameras/cameraLayers.ts` |
| Technology & communications | `#7ddaec` | Matches `[125, 218, 236]` in `features/globe/infrastructure/infrastructureLayers.ts` |
| Infrastructure | `#fbbf24` | Same value as the Humanitarian category |
| Public figures | `#f5c462` | Matches `[245, 196, 98]` in `features/globe/figures/figureLayers.ts` |
| Conflict regions | `#ff6a6a` | Matches the war colour `[255, 106, 106]` in `features/globe/layers/conflictRegions.ts` |
| GPS and GNSS interference | `#f5b53f` | Globe uses separate red and amber cell fills; not matched exactly |
| British National Grid | `#9aa3b2` | Not matched in this check |

Workspace panel accents (`content/platform.ts`) reuse the same family: Live monitoring
`#ff5a5a`, Ukraine `#f5b53f`, Cyber `#22d3ee`, Economy `#6ee7b7`, Photo geolocation
`#a78bfa`, Map tools `#38bdf8`, Teams `#ff6f37`.

## Depth, glow and texture

- **Globe** (`scenes/drawGlobe.ts`): ember atmosphere (radial gradient from 22 percent
  to 0), ocean gradient `#1a1622` to `#09080d`, ember rim at 35 percent, land dots in four
  depth bands of `rgba(233, 228, 220, 0.20 to 0.65)`, layer points faded towards the limb,
  pulsing halos on the active layer and a pulsing ember ring on the Red Sea.
- **Eye**: the React Bits Evil Eye brand mark (`components/brand/EvilEyeSurface`), never
  redrawn; masked with a radial gradient in the hero.
- **Glow**: primary button shadow (`0 10px 40px -10px` ember glow, larger on hover);
  layer dots (`0 0 14px`); orbit nodes (`0 0 30px` in their colour); orbit core and
  contact radial ember glows; timeline dots glow with progress; Assess threads use a
  6 px ember `drop-shadow`.
- **Depth**: console and phone drop shadows (`0 40px 120px -40px` and
  `0 40px 100px -30px`, `#000000cc`); Trust layers in 1200 px perspective with a 35
  degree tilt; export cards flip in perspective; hero title `text-shadow` against the
  ground; translucent header with `backdrop-filter: blur(14px) saturate(1.2)`.
- **Surfaces**: gradient cards (`160deg` and `170deg`, surface to ground-2); workspace
  cards tinted by a 22 percent accent radial in the top corner; topic bars 22 percent of
  the topic colour; yardstick bands step ember from 8 percent by 9 percent per band.
- **Texture**: a 64 px hero grid at `#ffffff0b`, masked to an ellipse and drifting
  slowly. There is no grain or noise texture; KAN-171 lists grain as allowed, and none
  was built.

## Performance budget

| Budget | Ceiling | Latest recorded | Source |
| --- | --- | --- | --- |
| Product route JavaScript (`ProductPage` static closure beyond the common entry, including the Eye worker and fallback engine) | 150 KiB gzip (153,600 bytes) | 62,248 bytes gzip | `pnpm check:bundle`, final follow-up at `ca810947`, 10 October 2026 |
| Initial JavaScript | 240 KiB gzip (245,760 bytes) | 129,439 bytes gzip | Same build |
| Mobile Lighthouse (performance, accessibility, SEO) | 90, 95, 90 (KAN-172) | 90/97/100 | Same record |

All figures are from [PUBLIC_PRODUCT_PAGE_ACCEPTANCE.md](../PUBLIC_PRODUCT_PAGE_ACCEPTANCE.md).
They predate the KAN-173 to KAN-180 and KAN-196 work integrated on this branch, which
adds chapters, scenes and images; the bundle and Lighthouse figures must be re-measured
before release. CSS, fonts and images are outside the JavaScript budget. Product images
are WebP with PNG fallback (`content/assets.ts`); the hero's 512 px Eye capture is
preloaded by Caddy on `/enterprise` only. The Open Graph image is now
`/brand/og-enterprise.png` (1200 by 630, `content/assets.ts`); the acceptance record
still names `/brand/eye-512.png` and should be updated by its owner.
