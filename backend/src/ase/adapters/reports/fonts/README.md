# DejaVu LGC Sans 2.37

These two unmodified upstream fonts provide Latin, Greek and Cyrillic glyphs for
body text and headings in PDF exports. The app embeds only the glyphs used in
each PDF. No system font installation or runtime download is required.

The complete upstream `LICENSE` is included alongside the fonts. It retains
the Bitstream, Arev and other upstream notices; the application's licence is
unchanged. Do not replace these files with proprietary system fonts.

Source: [official 2.37 release](https://github.com/dejavu-fonts/dejavu-fonts/releases/tag/version_2_37).
The downloaded `dejavu-lgc-fonts-ttf-2.37.zip` was verified against the SHA-256
published on the [official download page](https://dejavu-fonts.github.io/Download.html):

`bc73bd1c64299a95951fd8c1d493d391ded78cef5b9d3dd3df5859e1f85f5ec6`

Bundled file SHA-256 digests:

- `DejaVuLGCSans.ttf`: `321487efd1b5fa5bffc0597755708fb7b308b3a9a613cebaa013f6a9dd873ab8`
- `DejaVuLGCSans-Bold.ttf`: `0746f87aafab1227658d304e36dab999bfa95f2a6811a1031ca38ed243540a78`
- `LICENSE`: `7a083b136e64d064794c3419751e5c7dd10d2f64c108fe5ba161eae5e5958a93`

Chinese report languages use the bundled ASE Research Sans SC/TC fonts. These
are renamed, static weight-400 derivatives of Noto Sans CJK Sans2.004, distributed
under the adjacent `OFL-NotoCJK.txt`. The application licence is unchanged.
`scripts/build_cjk_fonts.py` records pinned upstream source hashes and rebuilds
the assets using the locked development dependency fonttools. Run it with
`uv run --project backend python scripts/build_cjk_fonts.py` from the repository root.
Rendering uses bundled fonts without network downloads. Chinese paragraphs use
CJK wrapping; simplified and traditional narrative scripts select distinct fonts.

The PDF renderer does not implement Arabic shaping or bidirectional layout. Unsupported
characters remain explicit `[U+XXXX]` markers and trigger a notice. The DOCX
export retains the original characters, with display depending on the reader's
fonts and layout engine. Do not describe this change as full Unicode support.


## Noto Sans Arabic 2.013

Unmodified regular and bold fonts are used only by the optional isolated print-HTML adapter. They were copied from the verified local shaping proof and retain the accompanying `OFL-NotoArabic.txt` licence. Runtime SHA-256 checks are recorded in `print_html.py`:

- Regular: `7ed3fe069312aceac454f17cf613a30f95271d6ed7ce58005ed4d016bd3823d7`
- Bold: `5ccd1a8914f7c7e8aa8050f2c7c37b10fc5e855f06583c2a2248a436aad3fc0f`

Adding these assets does not change language capability flags or establish PDF text-extraction/accessibility acceptance.
