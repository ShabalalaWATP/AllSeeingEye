# Natural hazard map filters

The disaster layer can be narrowed by source subtype: earthquakes, severe weather
and cyclones, floods, volcanoes, wildfire alerts, satellite thermal detections,
tsunamis, drought, landslides, sea/lake ice and other/unclassified records.
Exact aliases include the plural snake-case category IDs emitted by EONET,
alongside singular GDACS, USGS, GVP and cyclone-adapter subtypes. Unknown
subtypes remain unclassified; report titles are not used to guess a hazard type. Thermal observations remain
separate from wildfire alerts: a hot pixel does not establish a wildfire or cause.

Counts describe currently loaded records after the time, magnitude and GDACS
filters, before the selected type. They do not establish complete coverage or
unique incidents; FIRMS input is geographically sampled. Other map categories
and the main disaster visibility switch are unchanged by these controls.

The time window uses publication/acquisition time and refreshes every minute. It
never substitutes download time for an unknown publication date. Magnitude uses
only an explicit numeric earthquake magnitude, not GDACS variable-unit severity.
The impact selector applies only to GDACS green/orange/red alerts. Missing values
are retained by default and can be excluded explicitly when a relevant filter is
active. Future timestamps are excluded from bounded past-time windows.

Closing detail selection remains independent of filtering. Changing a hazard
filter clears a selected disaster record if that filter excludes it, while
preserving unrelated selections. These are display controls, not upstream
collection settings, and resetting restores all loaded hazards.
