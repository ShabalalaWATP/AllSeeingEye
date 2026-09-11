# Country subjects in fresh research

Country research can retain a newly collected RSS headline or summary that
explicitly names a selected country, even when the publisher gives no incident
location. For example, “Ukraine and Russia hold talks” can support subject
relevance for either selected country. It does not establish where the talks
took place, the participants' identities or nationalities, or that the claim is
true.

This applies only to original text returned by the Google News, reviewed
publisher and regional RSS research adapters in a public general research run.
It does not apply to drawn areas, map bounding boxes, ordinary live-map filters,
private uploads, translations, generated web context, registry records or
satellite observations. A record already carrying a country, point or geometry
keeps its existing geographical filtering rules. Country subjects cannot
override conflicting incident geography.

The reviewed alias table uses country names, not bare abbreviations, demonyms or
capital cities. Ambiguous names such as Georgia, Jordan, Chad and Turkey need
unambiguous longer forms or an alternative reviewed name. Longer place names are
protected: “South Sudan” does not become a subject match for Sudan alone, nor
“Northern Ireland” for Ireland. Publisher attribution phrases are excluded from
matches, including when copied into a headline suffix. The selected question,
search terms and publisher nationality cannot supply a positive match.

This is conservative text matching, not full entity disambiguation. A passing
name match establishes only what the source text mentions. Unlisted spellings,
some languages, abbreviations and indirect references can be missed. A match
does not raise a source's grade or establish independent corroboration.

## Frozen evidence and API representation

The existing evidence `attributes` array carries the additional provenance.
There is no new country or map-location field:

- `country_subject_policy`: `ase-original-rss-country-subject-v1`.
- `country_subject_notice`: states subject relevance and unverified incident
  geography.
- `country_subject_UA`, for example: a JSON string containing
  `["title", 0, 7, "Ukraine"]`.

Offsets are a half-open interval of Unicode code points in the frozen original
`title` or `summary`. The exact matched text remains alongside the offsets.
Selection rechecks the policy, notice and span against that original text before
admission. Prompts and exports repeat the distinction between country subjects
and incident geography. The source text, event ID, content hash, publication
date, source identity, grades and coordinates remain unchanged.

Processing uses the existing collection limits (at most 1,000 fresh items),
the existing private evidence-pool cap (4,000 candidates), and at most eight
selected countries. Only the bounded original title and summary are searched.
There are no new network requests or model calls. If preserving the match hints
would exceed the existing attribute limit, the original metadata wins and the
subject match is not admitted.
