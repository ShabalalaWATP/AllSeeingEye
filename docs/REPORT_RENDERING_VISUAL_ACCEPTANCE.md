# Report rendering visual acceptance

8 September 2026. A local diagnostic projected a complete existing report fixture
through the application document builder and current HTML/font projection.
The 87 blocks included Arabic and Persian judgements, eight long assessment
sections, structured citations, source URLs, warnings and a frozen evidence annex.
All seven rendered pages were inspected. No clipping, overlap or missing-glyph
boxes were observed; joining appeared visually coherent. The annex continued
across pages without observed loss of visible content. Its forced page break
left substantial white space on page five. App-generated page numbers are absent.

Both pypdf and Poppler preserved the exact source URL, report UUID and structured
timestamp. pypdf preserved the grouped citation `[E1, E2]`, while default Poppler
moved its opening bracket ahead of adjacent right-to-left prose. Exact Arabic and
Persian prose matching failed in both extractors. Visually intact text is therefore
not evidence of faithful generic copy/paste or search.

The installed Google-signed Chrome ran sandboxed with a separate owned profile,
escaped offline content and embedded verified fonts. It exited successfully and
no process using that profile remained. No browser or dependency was installed.
This proves local HTML/font output only. It does not validate the unconfigured
Linux isolation runtime, network/resource controls or cancellation. Marked content
and a structure tree do not establish PDF/UA or screen-reader reading order.
Native-speaker, supported-viewer and accessibility acceptance remain outstanding.

The full diagnostic record is retained locally under `data/visual-proof/`, including
browser provenance, exact input/document/HTML/PDF, page images, contact sheets and
unchanged extractor outputs. Those ignored artefacts are local evidence, not a
portable CI test result or a declaration of Arabic/Persian PDF support.
