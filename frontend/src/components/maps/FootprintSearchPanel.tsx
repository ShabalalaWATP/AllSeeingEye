import { useEffect, useRef, useState, type SyntheticEvent } from 'react';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';
import { describeError } from '@/lib/api/errors';
import { searchFootprints, type FootprintCollection } from '@/lib/api/footprints';
import type { LocalCollection } from '@/lib/map/geoJsonTypes';
import { isHttpUrl } from '@/lib/urls';
import { footprintDisplay } from './footprintGeometry';

export function FootprintSearchPanel({
  onChange,
}: {
  onChange: (data: LocalCollection | null) => void;
}) {
  const [bounds, setBounds] = useState({ west: '', south: '', east: '', north: '' });
  const [since, setSince] = useState('');
  const [until, setUntil] = useState('');
  const [disclose, setDisclose] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<FootprintCollection | null>(null);
  const [omitted, setOmitted] = useState(0);
  const [visible, setVisible] = useState(true);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  const submit = async (event: SyntheticEvent) => {
    event.preventDefault();
    if (busy) return;
    const bbox = [bounds.west, bounds.south, bounds.east, bounds.north].map(Number);
    const [west = NaN, south = NaN, east = NaN, north = NaN] = bbox;
    const start = Date.parse(since + 'T00:00:00Z'),
      end = Date.parse(until + 'T00:00:00Z');
    if (
      !disclose ||
      Object.values(bounds).some((value) => !value.trim()) ||
      !bbox.every(Number.isFinite) ||
      west < -180 ||
      east > 180 ||
      south < -90 ||
      north > 90 ||
      west >= east ||
      south >= north ||
      east - west > 10 ||
      north - south > 10 ||
      !Number.isFinite(start) ||
      !Number.isFinite(end) ||
      start >= end ||
      end - start > 14 * 86400000
    ) {
      setError(
        'Confirm disclosure and provide an ordered WGS84 box no larger than 10 degrees by 10 degrees, with a date interval of up to 14 days. Wrapped boxes are not supported.',
      );
      return;
    }
    const pending = new AbortController();
    controller.current?.abort();
    controller.current = pending;
    setBusy(true);
    setError(null);
    setResult(null);
    onChange(null);
    try {
      const response = await searchFootprints(
        {
          bbox: [west, south, east, north],
          since: new Date(start).toISOString(),
          until: new Date(end).toISOString(),
          disclose_to_provider: true,
        },
        pending.signal,
      );
      if (pending.signal.aborted) return;
      const display = footprintDisplay(response);
      setResult(response);
      setOmitted(display.omitted);
      setVisible(true);
      onChange(display.data);
    } catch (caught) {
      if (!pending.signal.aborted) setError(describeError(caught));
    } finally {
      if (!pending.signal.aborted) setBusy(false);
    }
  };
  return (
    <details className="rounded border border-line p-3">
      <summary className="cursor-pointer text-sm font-medium">
        Copernicus acquisition footprints
      </summary>
      <p className="my-3 text-xs text-muted">
        Search the public catalogue for dated acquisition footprints. This sends your chosen area
        and dates to Copernicus. No imagery or asset files are retrieved; a footprint does not prove
        a clear view or an event.
      </p>
      <form
        aria-label="Search acquisition footprints"
        onSubmit={(event) => void submit(event)}
        className="space-y-3"
      >
        <fieldset disabled={busy} className="grid gap-3 sm:grid-cols-2">
          {(['west', 'south', 'east', 'north'] as const).map((key) => (
            <TextField
              key={key}
              label={`${key[0]?.toUpperCase()}${key.slice(1)} bound`}
              type="number"
              step="any"
              value={bounds[key]}
              onChange={(event) => setBounds({ ...bounds, [key]: event.target.value })}
            />
          ))}
          <TextField
            label="Acquisition from (UTC)"
            type="date"
            value={since}
            onChange={(event) => setSince(event.target.value)}
          />
          <TextField
            label="Acquisition until (UTC, exclusive)"
            type="date"
            value={until}
            onChange={(event) => setUntil(event.target.value)}
          />
        </fieldset>
        <label className="flex items-start gap-2 text-sm">
          <input
            type="checkbox"
            checked={disclose}
            onChange={(event) => setDisclose(event.target.checked)}
          />
          Send this area and date interval to Copernicus for this search.
        </label>
        <div className="flex gap-2">
          <Button type="submit" variant="secondary" busy={busy} disabled={!disclose}>
            Search footprints
          </Button>
          {busy && (
            <Button
              variant="ghost"
              onClick={() => {
                controller.current?.abort();
                setBusy(false);
                setError('Search cancelled.');
              }}
            >
              Cancel footprint search
            </Button>
          )}
        </div>
      </form>
      {error && <Alert tone="error">{error}</Alert>}
      {result && (
        <div className="mt-3 space-y-2">
          <p className="text-sm">
            {result.features.length} catalogue footprints · {result.status} · queried{' '}
            {result.queried_at}
          </p>
          {result.truncated && (
            <Alert tone="warning">
              Results are truncated. Narrow the area or dates; this is not complete catalogue
              coverage.
            </Alert>
          )}
          {omitted > 0 && (
            <Alert tone="warning">
              {omitted} footprints cannot be safely displayed with the current geometry limits.
              Their metadata remains listed.
            </Alert>
          )}
          <p className="text-xs text-muted">{result.limitations}</p>
          {result.features.length === 0 && (
            <p className="text-sm">
              {result.status === 'unavailable'
                ? 'Catalogue unavailable. No conclusion about coverage can be drawn.'
                : 'No catalogue entries returned for this query.'}
            </p>
          )}
          {result.features.length > 0 && (
            <>
              <label className="flex min-h-11 items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={visible}
                  onChange={(event) => {
                    setVisible(event.target.checked);
                    onChange(event.target.checked ? footprintDisplay(result).data : null);
                  }}
                />
                Show purple footprint outlines
              </label>
              <ul aria-label="Acquisition footprint metadata" className="space-y-2 text-xs">
                {result.features.map((feature) => (
                  <li key={feature.id} className="rounded border border-line p-2">
                    <strong>{feature.id}</strong>
                    <p>
                      {feature.properties.collection} · acquired {feature.properties.captured_at} ·
                      cloud cover{' '}
                      {feature.properties.cloud_cover === null
                        ? 'unknown'
                        : `${feature.properties.cloud_cover}%`}
                    </p>
                    <p>{feature.properties.licence}</p>
                    {isHttpUrl(feature.properties.source_url) && (
                      <a
                        href={feature.properties.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="underline"
                      >
                        Catalogue record
                      </a>
                    )}
                  </li>
                ))}
              </ul>
            </>
          )}
          <Button
            variant="secondary"
            onClick={() => {
              setResult(null);
              onChange(null);
            }}
          >
            Clear footprint results
          </Button>
        </div>
      )}
    </details>
  );
}
