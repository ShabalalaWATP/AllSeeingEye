# Conflict report display filters

## Regional overview, 9 September 2026

Conflict controls now open a regional overview, with a separate Report filters
view for individual source records. War regions use red crossed-swords symbols;
tension areas use amber. These are curated catalogue classifications, not current
independent assessments. Region search matches names, country codes and parties;
the main nation filter also applies. Selecting a symbol or list entry locates
the area, shows its name, adds a cyan halo and draws its broad catalogue outline.
Closing details, selecting another object or changing the region filters clears
the highlight. Symbols stop accepting picks during drawing or measurement.

The inspector links to the existing conflict evidence and timeline. Counts use
the tracker's retained seven-day evidence groups, including related reporting,
and are not total attacks, independent corroboration or a completeness claim.
Report filters apply to individual points; they do not recalculate this summary.
The region centre and outline are locators, not incident coordinates, frontlines
or controlled territory. Original source report positions and dates are retained.

The overview fetches the existing authenticated tracker endpoint once when the
category is enabled, with manual refresh. It adds no feed polling loop or new
event store. Requests are aborted and snapshots masked on account/access changes.
At most 100 valid catalogue regions are drawn. Only the selected name and outline
are displayed to limit clutter.

## Individual reports

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
