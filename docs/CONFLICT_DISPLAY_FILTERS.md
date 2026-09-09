# Conflict report display filters

The map conflict controls support loaded-report text search, provider selection
and source-labelled location precision alongside incident type and the optional
historical baseline. All search words must appear across the report title,
English title, summary, country code or subtype, ignoring letter case. This
search operates only on records already loaded by the current map scope.

Type counts apply the other display filters first. Available source choices
come from loaded conflict records, including the optional historical baseline.
A source that later has no loaded records remains selected and is labelled as
empty; the UI does not silently widen the operator's selection.

Exact requires a point and the source's exact label. Approximate requires a
point labelled city, region or country. Neither label independently verifies
accuracy. Records with unknown or absent coordinates remain available under All.
No severity filter is applied because source severity scales are not comparable.

Non-conflict categories and main visibility switches remain unchanged. An
excluded selected conflict record is deselected so its details and highlight
stay consistent with the filtered map.
