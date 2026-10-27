# Storyboard

Status: draft for Alex's approval, 18 October 2026. Derived from the code in
`frontend/src/features/product/` (chapters, `motion/ScrollChapter.tsx` and the
`story-*.css` files). It describes what the build does; it was not checked frame by
frame in a browser for this document. Progress values (`p`) run from 0 to 1 across a
chapter, as written to the `--progress` custom property.

## Width classes

| Class | Rule in the code | Effect |
| --- | --- | --- |
| Phone | under 640 px wide (`max-width: 640px`) | Single column; hero counts and scroll cue hidden. Under 560 px the header wordmark and "Sign in" link, and the enquiry form's second column, are hidden too |
| Tablet | 640 to 899 px wide | Single column (`max-width: 899px` rules); hero counts shown |
| Desktop | at least 900 px wide **and** 700 px tall (`ROOMY` in `ScrollChapter.tsx`) | Two-column chapters; most chapters pin. Header chapter links appear above 1100 px |

A wide but short window (under 700 px tall) is not "roomy": it keeps two columns
from 900 px but plays chapters in passing mode. Tablet landscape at 1024 by 768 is
roomy and behaves as desktop.

## Modes

`ScrollChapter` gives each section a `data-mode`:

- **pinned**: the section is `(length + 1) × 100svh` tall and its stage sticks to the
  viewport; `p` follows the scroll through `length` screens.
- **passing**: no pinning; by default `p` rises from 0 when 5 percent of the section has
  crossed the viewport to 1 at 50 percent (`segment(passProgress, 0.05, 0.5)`). A
  chapter can set its own `passWindow`: the hero uses 0.5 to 1 (it is already in view
  at load, half way through its pass) and Observe uses 0.04 to 0.2 (see below).
- **still**: the story is paused or the device asks for reduced motion. Ordinary height,
  `p` fixed at 1 (the hero overrides it to 0), every scene in its end state.

Pinning by chapter: hero, Observe, Ask, Collect, Assess, Review, Workspaces and Trust
pin on desktop and pass elsewhere; Sources and Deploy always pass (`pin={false}`);
Tools, Contact and the three follow-on sections (Analytic standards, Watching, Choices
and limits) are ordinary sections with `Reveal` entrances only. No chapter pins below
the desktop class, as KAN-170 requires (the former `pinNarrow` option was removed on
18 October 2026). Checked in a browser at 375 by 812 and 768 by 1024 on that date:
every chapter passing, no horizontal page overflow.

## Header (all chapters)

Sticky, translucent (blur 14 px). Brand mark, chapter links (above 1100 px), pause
control, "Sign in", "Talk to us", and a 2 px ember-to-amber progress line scaled to
the page scroll. The progress line keeps tracking scroll position when the story is
still; it reports position rather than animating.

## 0. Hero: the Eye opens

- **Start:** the Eye opens from a narrow slit (1100 ms, from 150 ms), the title and
  lead rise in (900 ms, lead 120 ms later), the background grid drifts, the scroll cue
  line loops, and the four counts count up on first view.
- **Transition (pinned 0.9 screens on desktop; passing elsewhere, over the second half
  of the pass, as the hero leaves the screen):** the Eye scales from 1 to 2.4 and fades (gone at
  `p` 0.91); the copy rises 80 px and fades (gone at 0.63); the grid fades to 20 percent;
  the cue fades by 0.25. On a fine pointer the pupil follows the cursor.
- **End:** an empty dark stage; the Observe globe follows.
- **Text position:** centred column over the Eye at all widths. Phone: Eye 44svh tall,
  copy from 24svh, no counts or cue. Tablet: counts in four columns. Desktop: Eye up to
  60svh (560 px), title up to 8.5rem.
- **Still:** not pinned; `--progress` held at 0 so the opening frame stays readable;
  no wake, arrival, drift or cue animation; the Eye is paused (frame cap 1, flames
  stopped, pupil centred); counts show final values.

## 1. Observe

- **Start:** the whole Earth turns slowly (5 degrees per second); the first layer is
  fading in and is the active row.
- **Transition (pinned, 16 beats over 5.12 screens on desktop):** beats 0 to 14 reveal one layer
  each. The active layer is emphasised on the globe (others dimmed to 55 percent,
  points pulse). The list scrolls one row (500 ms) and the active row's detail (description,
  illustrative count with a fresh count-up, filter chips) rises in (500 ms). Beat 15
  turns the camera to the Red Sea (42 E, 16 N), zooms 30 percent, stops the spin and
  fades in a pulsing ember ring over the last 15 percent.
  The list moves by transform only (every row translates together). **Passing
  (elsewhere):** the globe leads a long section, so the 16 beats play between 4 and 20
  percent of the pass, while the globe is on screen (measured on 18 October 2026: at
  375 by 812 the beats run over about 700 px of scroll with the globe at least half
  visible for most of it; at 768 by 1024 the globe is fully visible for the later
  beats). The list shows every row with its detail and chips, as in the still state.
- **End:** all 15 layers visible, settled on the Red Sea with the ring.
- **Text position:** Desktop pinned: globe left, copy and layer list right (list 46svh,
  masked top and bottom). Unpinned: both columns start at the top. Phone and tablet:
  globe on top (46svh), then the title, lead and full list.
- **Still:** ordinary height; the globe draws one frame with every layer and the Red
  Sea focus, no emphasis; the list shows every row with its detail and chips.

## 1b. Filters and tools

- **Start:** heading, four filter rows and 17 tool cards hidden below their final place.
- **Transition (ordinary section):** each element rises in when it reaches the viewport
  (opacity 700 ms, movement 900 ms), staggered 70 ms (filter rows by index, cards by
  index modulo 6).
- **End:** filter table and tool grid.
- **Text position:** Desktop and tablet: filter label column (11rem) beside chips. Phone:
  label above chips. Tool grid auto-fills 15rem columns (one on phone, up to four or
  five on desktop).
- **Still:** everything shown at once.

## 2. Sources

- **Start:** two dashed rings rotating (90 s and 60 s, opposite ways) around a static
  "423 sources" core; topic nodes waiting off-stage at 90 percent radius.
- **Transition (passing):** node `i` flies to its ring between `p` = i/14 and (i+1)/14;
  all eleven settle by 0.79. Topic bars grow to their share with `p`. The lead's two
  counts count up on first view; topic rows and mode cards rise in.
- **End:** eleven coloured nodes on two rings, sized by count; bars at full share.
- **Text position:** Desktop: orbit on the left, sticky 6rem below the top, while the
  copy scrolls on the right. Phone and tablet: orbit above the copy (up to 26rem wide,
  not sticky); collection modes in one column.
- **Still:** nodes in place, bars full, rings stationary, rows shown.

## 3. Ask

- **Start:** an empty question line with a blinking caret; no chips; Basic selected.
- **Transition (pinned 1.8 screens on desktop, passing elsewhere; 8 beats):** the question
  types itself between `p` 0.05 and 0.45; the six scope chips snap in from 0.46 to 0.79
  (each rises 14 px and scales from 92 percent), the map-carried area chip first with an
  ember border; the depth selector moves to Deep at 0.75 and Advanced at 0.875 (300 ms,
  lifts 3 px). The feature ticks rise in.
- **End:** full question, six chips, Advanced selected.
- **Text position:** Desktop: copy left, console right. Phone and tablet: copy above
  the console.
- **Still:** full question, steady caret, all chips, Advanced selected.

## 4. Collect

- **Start:** an empty stage with undrawn connector arcs.
- **Transition (pinned 1.6 screens on desktop, passing elsewhere):** six arcs draw from
  the scope point (starting at 0.02, 0.04 and so on, each over a sixth of the chapter);
  cards fly in from different directions with an 8 degree turn, card `i` between
  (i + 0.4)/8 and (i + 1.4)/8; the dashed amber gap card arrives last (0.68 to 0.80).
  The grading legend rises in.
- **End:** six cards stacked, arcs drawn (cyan, the last amber).
- **Text position:** Desktop: copy left, cards right, arcs in the gutter. Phone and
  tablet: copy above cards; arcs hidden.
- **Still:** cards in place, arcs fully drawn.

## 5. Assess, then Analytic standards

- **Start:** three faint judgements (15 percent, shifted 30 px), undrawn citation
  threads, no alternative explanation.
- **Transition (pinned 2.2 screens on desktop, passing elsewhere):** judgements write in
  (0 to 0.25, 0.18 to 0.43, 0.35 to 0.60); five threads draw from the citations back to
  the evidence (from 0.15 to 0.65); an amber outline marks the challenged judgement
  (0.68 to 0.88); the challenge note and alternative fade in (0.72 to 0.92); the
  "what happens next" chips arrive from 0.83.
- **End:** the full report, all three closing chips fully in (fixed 18 October 2026).
- **Text position:** Desktop: heading above; evidence list left, report right, threads
  between. Phone and tablet: evidence above the report; threads hidden.
- **Analytic standards (ordinary section):** the seven-band yardstick (two columns on
  phone and tablet) is static; the seven checks rise in.
- **Still:** end state.

## 6. Review, then Watching

- **Start:** an undrawn timeline line; six faint beats (30 percent) with small dots.
- **Transition (pinned 2 screens on desktop, passing elsewhere):** the line grows with
  `p`; beat `i` brightens between i/7 and (i+1)/7 while its dot grows and glows. When
  pinned, the beats form one row that slides left by up to `6 × 16rem − 85vw`; otherwise
  they form a vertical list (up to 40rem wide) beside a line that grows downwards.
- **End:** all six beats bright.
- **Watching (ordinary section):** three panels rise in; on the phone, the five channel
  toasts drop in one by one (700 ms each, 450 ms apart); export cards flip into place
  (650 ms, from 300 ms, 110 ms apart); the sharing panel fades in.
- **Text position:** Desktop: heading above the sliding row; panels in three columns
  (panel, 18rem phone, exports). Phone and tablet: one column, phone centred at up to
  20rem.
- **Still:** vertical list, line full, beats bright, toasts and exports in place.

## 7. Specialist workspaces

- **Start:** panel 1 of 7 in view; "Panel 1 of 7" with previous and next buttons.
- **Transition (pinned 2.4 screens on desktop):** vertical scroll moves the track
  sideways; the position updates as each panel arrives. Buttons and arrow keys scroll
  the page to a panel's share of the chapter. **Passing (elsewhere):** a native
  horizontal swipe row with snap points; buttons and arrow keys scroll the row.
- **End:** panel 7 (Teams) in view.
- **Text position:** heading above; cards `min(80vw, 24rem)` wide, at least 22rem tall,
  at all widths.
- **Still:** an ordinary vertical list of the seven full-width cards, without carousel
  controls or carousel roles.

## 8. Trust and control, then Choices and limits

- **Start:** four tilted, faint layers close together.
- **Transition (pinned 1.6 screens on desktop, passing elsewhere):** layer `i` opens
  between `p` 0.16i and 0.16i + 0.2: it untilts from 35 degrees, shifts sideways by up to
  18 px, gains an ember border and full opacity; the layers start 1rem closer each and
  move apart to the 1.3rem gap by transform (the gap itself is fixed).
- **End:** an exploded four-layer stack.
- **Text position:** Desktop: copy and data minimisation note left, stack right. Phone
  and tablet: copy above the stack.
- **Choices and limits (ordinary section):** "Bring your own AI" and "Engineered with
  care" rise in; "What it will not pretend" is static. Three columns on desktop, one on
  phone and tablet.
- **Still:** exploded stack; all panels shown.

## 9. Deploy

- **Start:** an empty diagram frame.
- **Transition (passing at every width):** the server boundary fades in over the first
  quarter; the seven links draw in turn; the eight nodes fade in turn. The cost section
  (production sentence, or the draft estimator in development) rises in.
- **End:** the full diagram, every link drawn and node opaque (fixed 18 October 2026).
- **Text position:** centred column; the diagram scales to the column width; the
  estimator uses two columns on desktop and one below 900 px.
- **Still:** the end state.

## 10. Talk to us and footer

- **Start:** a static ember glow; the block below it hidden until it reaches the viewport.
- **Transition (ordinary section):** the block rises in. After an enquiry is received,
  the brand mark closes softly (900 ms) unless the story is still.
- **End:** the call to action and, when enabled, the enquiry form.
- **Text position:** centred, up to 46rem; form fields in two columns, one under 560 px.
- **Still:** shown immediately; the Eye stays open after sending. The footer is static.

## Build issues found

Three issues found when this document was written were fixed on 18 October 2026:
the Assess closing chips and the Deploy diagram now reach their end state at `p` = 1
(`storyMotionEnd.test.tsx` evaluates every staggered formula for the last item of
each list), and the Review timeline is a vertical list whenever it is not pinned.
No open build issues are recorded here.
