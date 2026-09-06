# Third Party Notices

This file records third-party source code copied into the frontend, as opposed to
packages installed from npm (whose licences travel with the packages in
`node_modules`).

## React Bits: Evil Eye

| Item                | Detail                                                                              |
| ------------------- | ----------------------------------------------------------------------------------- |
| Component           | `EvilEye` (registry item `EvilEye-TS-TW`, TypeScript + Tailwind variant)            |
| Source page         | https://reactbits.dev/backgrounds/evil-eye                                          |
| Registry file       | https://reactbits.dev/r/EvilEye-TS-TW.json (`files[0].path`: `EvilEye/EvilEye.tsx`) |
| Copied to           | `frontend/src/components/brand/EvilEye.tsx`                                         |
| Retrieved           | 4 September 2026                                                                    |
| Declared dependency | `ogl@^1.0.11` (installed as `ogl` 1.0.11)                                           |
| Licence             | MIT + Commons Clause License Condition v1.0, Copyright (c) 2026 David Haz           |
| Licence source      | https://raw.githubusercontent.com/DavidHDev/react-bits/main/LICENSE.md              |

The Commons Clause permits using the component inside this application. It does not
permit selling, sublicensing or redistributing the component itself, alone or in a
bundle, so the component must not be published as part of any library or template
derived from this repository.

### Modifications made to the copied file

The registry copy has no header comment; a header comment was added recording the
source, licence and the changes below. The shader, colours and every default value
are unchanged.

1. Two optional props were added to `EvilEyeProps`: `maxFps?: number` caps the
   `requestAnimationFrame` loop by skipping frames, and `paused?: boolean` stops
   the loop while true. Both are read through refs so that changing them does not
   rebuild the WebGL context.
2. The `update` loop honours those two props, a `start` helper resumes the loop
   when `paused` returns to false, and the effect cleanup clears the resume ref.
3. A `ResizeObserver` updates the canvas when the container changes size after
   responsive layout. The effect disconnects the observer during cleanup and
   retains the original window-resize fallback. The vendor file remains together
   at 352 lines to preserve its source structure; its shader is unchanged.

### Licence text

```
MIT + Commons Clause License Condition v1.0

Copyright (c) 2026 David Haz

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, and distribute the Software **as part of an application, website, or product**, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

## Commons Clause Restriction

You may use this Software, including for any commercial purpose, **so long as you do not sell, sublicense, or redistribute the components themselves-whether alone, in a bundle, or as a ported version.**

## No Warranty

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### Static brand assets

The files under `public/brand/` (`eye-32.png`, `eye-48.png`, `eye-192.png`, `eye-512.png`,
`apple-touch-icon.png`) are frame captures of this same component rendered by the app's
development-only `/brand/capture` page on 4 September 2026, downscaled without other edits.
They exist so the favicon, PWA icons and print or export headers show the real eye rather
than a redrawn imitation. They carry the same licence terms as the component.
