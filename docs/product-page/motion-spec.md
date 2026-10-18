# Motion specification

Status: draft for Alex's approval, 18 October 2026. Extracted from the code in
`frontend/src/features/product/` and `frontend/src/components/brand/`. Values are as
built; where the build departs from the KAN-171 ticket, the difference is noted.

## Principles as built

- Scroll motion is driven by one number per chapter, `--progress` (0 to 1), written by
  `motion/ScrollChapter.tsx`. CSS derives every beat from it with `clamp()` formulas,
  so scrolling never re-renders React.
- Entrances that are not scroll-linked use `motion/Reveal.tsx` (once per element, on
  first intersection) and CSS transitions.
- Canvas and WebGL loops run only while visible and allowed (see "Still and pause").
- Text is always in the document. Animated copies are `aria-hidden` with a screen
  reader copy beside them (typed question, count-ups).

## Easing curves

| Name | Value | Used by |
| --- | --- | --- |
| `--ease-out` | `cubic-bezier(0.16, 1, 0.3, 1)` (`product.css`) | Reveal, buttons, hero wake and arrival, layer list, depth selector, toasts, export flip |
| Contact close | `cubic-bezier(0.65, 0, 0.35, 1)` for transform, `ease` for opacity | Brand mark closing after an enquiry (`story-close.css`) |
| Count-up | cubic ease-out, `1 − (1 − t)³` | `motion/CountUp.tsx` |
| Globe camera | smoothstep, `f² × (3 − 2f)` | `scenes/GlobeCanvas.tsx` focus on the Red Sea |
| Loops | `ease-in-out` (grid drift, scroll cue), `linear` (orbit rings), `steps(1)` (caret) | `story-hero.css`, `story-sources.css`, `story-research.css` |
| Scroll-linked beats | linear in `p` inside each `clamp()` window | All `--t` formulas |

## Duration scale

| Duration | Where |
| --- | --- |
| 160 ms | Header link colour; workspace button border |
| 200 ms | Button hover lift, border and shadow |
| 300 ms | Depth selector step |
| 400 ms | Observe layer row opacity |
| 500 ms | Observe list scroll; active layer detail arrival |
| 650 ms | Export card flip |
| 700 ms | Reveal opacity; mask reveal opacity; alert toast |
| 900 ms | Reveal movement; mask clip; hero title and lead arrival; count-up; contact close |
| 1,100 ms | Hero Eye wake |
| 1 s, 1.8 s | Caret blink; scroll cue loop |
| 36 s, 60 s, 90 s | Hero grid drift; inner and outer orbit rings |

## Stagger scale

| Stagger | Where |
| --- | --- |
| 70 ms per `order` step | `Reveal` (`--reveal-order`); orders are the item index, or index modulo 6 for long lists |
| 120 ms | Hero lead after the title; Eye wake starts at 150 ms |
| 450 ms per item | Alert toasts on the phone |
| 300 ms, then 110 ms per item | Export card flip |
| Progress windows | Scroll-linked staggers, listed below |

Scroll-linked stagger formulas (each `t` is clamped to 0 to 1):

| Chapter | Element | Formula | Window per item |
| --- | --- | --- | --- |
| Sources | orbit node | `p × 14 − i` | 1/14 of `p`, all settled by 0.79 |
| Ask | scope chip | `p × 12 − 5.5 − 0.6i` | 1/12, from 0.46 |
| Collect | evidence card | `p × 8 − i − 0.4` | 1/8, from 0.05 |
| Collect | arc (`DrawPath`) | start `0.02 + 0.02i`, rate 6 | 1/6 |
| Assess | judgement | `p × 4 − 0.7i` | 1/4 |
| Assess | thread (`DrawPath`) | start `0.15 + i/16`, rate 4 | 1/4 |
| Assess | challenge outline; note and alternative | `p × 5 − 3.4`; `p × 5 − 3.6` | 0.68 to 0.88; 0.72 to 0.92 |
| Assess | closing chip | `p × 10 − 8.2 − 0.35i` | 1/10, from 0.82; the third chip completes at 0.99 |
| Review | timeline beat and dot | `p × 7 − i` | 1/7 |
| Trust | layer | `p × 5 − 0.8i`; spread `(1 − p) × i × −1rem` | 1/5 |
| Deploy | link; node | `p × 3 − 0.3i`; `p × 4 − 0.4i` | 1/3; 1/4; the last link and node complete at 0.93 and 0.95 |

## Animatable properties

Rule as built (`product.css` header, `Reveal.tsx`, `DrawPath.tsx`): animate
`transform` and `opacity`; use `clip-path` for the mask reveal, `stroke-dashoffset` for
line drawing, canvas drawing for the globe and WebGL uniforms for the Eye. `filter` is
used sparingly and statically (`drop-shadow` on Assess threads; `backdrop-filter` on the
header and hero eyebrow). Layout properties should not animate.

`storyMotionEnd.test.tsx` evaluates every formula above that combines `p` with `i`
for the last item of its list and fails if any element is short of 1 at `p` = 1.

On 18 October 2026 the Observe list scroll (formerly a 500 ms `margin-top` transition)
became a `transform` on every row, and the Trust stack spacing (formerly an animated
`gap`) became a fixed 1.3rem gap with each layer translated. Remaining exceptions in
the current CSS:

1. **Active layer label** (`story-hero.css`): `font-size` jumps to 1.25rem on the active
   row. Not transitioned, but it changes layout once per beat.
2. **Typed question** (`AskChapter.tsx`): writes `textContent` per frame, which reflows
   that line. Deliberate; no React render.
3. **Paint-only properties driven by progress or transitions:** `box-shadow` (timeline
   dot glow, challenged judgement outline, button hover), `background` (challenged
   judgement tint, depth selector), `border-color` (trust layers, depth selector,
   buttons), `color` (header links). These repaint but do not reflow.

The KAN-171 ticket names WebGL uniforms and `filter` as allowed; the build adds
`clip-path`, `stroke-dashoffset` and 2D canvas drawing.

## Pinning and scroll distance

A pinned section is `(length + 1) × 100svh` tall; its stage is `100svh` and sticky, so
the pinned scroll distance is `length` screens. Pinned progress uses the stage's own
height, not `innerHeight`, so a collapsing mobile address bar cannot end a chapter early.

| Chapter | `length` | Pins on desktop | Pins on phone and tablet | Beats (`steps`) |
| --- | --- | --- | --- | --- |
| Hero | 0.9 | yes | passing (window 0.5 to 1) | 1 |
| Observe | 16 × 0.32 = 5.12 | yes | passing (window 0.04 to 0.2) | 16 |
| Tools | none | ordinary section | ordinary section | |
| Sources | 1.6 | no (`pin={false}`), passing | passing | 1 |
| Ask | 1.8 | yes | passing | 8 |
| Collect | 1.6 | yes | passing | 1 |
| Assess | 2.2 | yes | passing | 1 |
| Review | 2.0 | yes | passing | 1 |
| Workspaces | 2.4 | yes | passing (swipe row) | 1 |
| Trust | 1.6 | yes | passing | 1 |
| Deploy | 0.6 | no (`pin={false}`), passing | passing | 1 |
| Contact | none | ordinary section | ordinary section | |

Total pinned distance on desktop is 17.62 screens; nothing pins on phones and tablets.
For passing chapters `length` only switches the motion on; it adds no height. Passing
progress is `segment(passProgress(top, height, viewport), start, end)`, with the window
0.05 to 0.5 unless the chapter sets `passWindow`.

## Shared scroll scheduler

`motion/scrollScheduler.ts`:

- One passive `scroll` listener and one passive `resize` listener on `window`, added
  with the first subscriber and removed with the last.
- At most one `requestAnimationFrame` pending. Each frame runs every subscriber's
  `measure()` first (layout reads), then every `apply()` (style writes), so reads and
  writes never interleave across chapters.
- Subscribers: each animated `ScrollChapter` and the header progress line.
- `apply` writes `--progress` with four decimals, calls `onProgress` (canvas controls,
  typed text, horizontal track), and calls `onStep` only when the beat changes.

Other per-element work stays off the scroll path: connector and fan paths are measured
on mount and on resize (`ResizeObserver`), the horizontal track's travel is measured on
resize, and the unpinned workspace row follows its own scroll with one frame per event.

## Pointer follow

Only the hero Eye follows the pointer (`chapters/HeroChapter.tsx`):

- On when the device matches `(hover: hover) and (pointer: fine)` and the story is not
  still; otherwise `pupilFollow` is 0 and the pupil stays centred.
- `pointerScope="page"`: a passive `mousemove` listener on `window`, so copy over the Eye
  does not block it; the target is clamped to the Eye's edge and returns to centre when
  the pointer leaves the window.
- Touch and coarse pointers never attach the listener. The header and contact marks use
  `pupilFollow={0}`.

## Still and pause

- `still` = the operating system asks for reduced motion **or** the visitor pressed the
  header pause (`motion/useProductMotionPause.ts`). The choice is stored on the device
  only, under `ase.brand-motion`, and never reads or writes account preferences. With
  system reduced motion the button is `aria-disabled` and explains why.
- `idle` = `still` **or** the tab is hidden. Idle stops continuous loops (globe spin,
  Eye flames, video loops) without tearing down renderers.
- When still: the story root carries `data-motion="still"`; chapters stop pinning and
  show end states; `Reveal` and `CountUp` show content at once; every CSS animation and
  transition under the feature has a still override, enforced by
  `storyMotionStill.unit.test.ts`; the globe draws one final frame; the Eyes run at a
  1 fps cap with flames stopped and are paused; the workspace gallery becomes a list.
- Print styles show unrevealed content.

## Device handling

- **Globe canvas** (`scenes/GlobeCanvas.tsx`): 2D canvas, no WebGL needed. Backing store
  capped at `min(2, devicePixelRatio)`. Draws only while intersecting and not idle;
  pausing or hiding the tab stops the loop and keeps the Earth's position. Land drawing
  reuses typed arrays, so frames allocate almost nothing.
- **Eye** (`components/brand/EvilEyeSurface.tsx`): OGL renderer at `dpr: 1`; frame caps of
  30 fps (hero) and 24 fps (header and contact marks), 1 fps when still.
  `deferUntilVisible` keeps the captured image until first intersection.
  `workerRendering` renders in an OffscreenCanvas worker where supported, falling back
  to a fresh main-thread canvas on failure. `saveDataFallback` keeps the static capture
  when the browser reports Save-Data. A lost context keeps the capture without a
  recovery loop.
- **Media** (`chapters/WorkspaceMedia.tsx`): images lazy-load at their declared size;
  loops are muted, inline, `preload="none"`, play only on screen and pause when idle.
