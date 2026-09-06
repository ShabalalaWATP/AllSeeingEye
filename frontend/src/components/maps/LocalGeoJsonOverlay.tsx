import { useEffect, useRef, useState } from 'react';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField, TextField } from '@/components/ui/Field';
import type { LocalOverlay } from '@/lib/map/geoJsonTypes';
import { MAX_GEOJSON_BYTES, parseLocalGeoJson } from '@/lib/map/localGeoJson';

export function LocalGeoJsonOverlay({
  overlay,
  visible,
  onChange,
  onVisible,
}: {
  overlay: LocalOverlay | null;
  visible: boolean;
  onChange: (value: LocalOverlay | null) => void;
  onVisible: (value: boolean) => void;
}) {
  const [source, setSource] = useState('');
  const [datasetDate, setDate] = useState('');
  const [attribution, setAttribution] = useState('');
  const [precision, setPrecision] = useState<LocalOverlay['precision']>('unknown');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [page, setPage] = useState(0);
  const reader = useRef<FileReader | null>(null);
  const generation = useRef(0);
  useEffect(
    () => () => {
      generation.current++;
      reader.current?.abort();
    },
    [],
  );
  const importFile = (file: File) => {
    reader.current?.abort();
    const current = ++generation.current;
    setError(null);
    if (
      !source.trim() ||
      !attribution.trim() ||
      !/^\d{4}-\d{2}-\d{2}$/.test(datasetDate) ||
      !Number.isFinite(Date.parse(datasetDate)) ||
      new Date(datasetDate).toISOString().slice(0, 10) !== datasetDate
    ) {
      setError('Enter a source, a valid dataset date and attribution before selecting a file.');
      return;
    }
    if (file.size > MAX_GEOJSON_BYTES) {
      setError('GeoJSON is limited to 5 MiB.');
      return;
    }
    if (!/\.(geojson|json)$/i.test(file.name)) {
      setError('Select a local .geojson or .json file.');
      return;
    }
    const metadata = {
      source: source.trim(),
      datasetDate,
      attribution: attribution.trim(),
      precision,
    };
    const input = new FileReader();
    reader.current = input;
    setBusy(true);
    input.onload = () => {
      if (current !== generation.current) return;
      try {
        const text = typeof input.result === 'string' ? input.result : '';
        onChange({ ...parseLocalGeoJson(text), ...metadata });
        onVisible(true);
        setPage(0);
      } catch (caught) {
        setError(
          caught instanceof SyntaxError
            ? 'The file is not valid JSON.'
            : caught instanceof Error
              ? caught.message
              : 'The GeoJSON could not be read.',
        );
      } finally {
        setBusy(false);
        reader.current = null;
      }
    };
    input.onerror = () => {
      if (current === generation.current) {
        setBusy(false);
        setError('The local file could not be read.');
      }
    };
    input.readAsText(file);
  };
  const currentPage = Math.min(
    page,
    Math.max(0, Math.ceil((overlay?.canonical.features.length ?? 0) / 20) - 1),
  );
  return (
    <details className="rounded border border-line p-3">
      <summary className="cursor-pointer text-sm font-medium">
        Private local GeoJSON overlay
      </summary>
      <p className="my-3 text-xs text-muted">
        A temporary visual reference, not saved report evidence. Nothing is uploaded or added to
        live feeds. Source and precision below are your declarations, not verified facts. This
        overlay does not filter research collection.
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        <TextField
          label="Overlay source"
          value={source}
          maxLength={200}
          onChange={(event) => setSource(event.target.value)}
        />
        <TextField
          label="Dataset date"
          type="date"
          value={datasetDate}
          onChange={(event) => setDate(event.target.value)}
        />
        <TextField
          label="Attribution / licence note"
          value={attribution}
          maxLength={500}
          onChange={(event) => setAttribution(event.target.value)}
        />
        <SelectField
          label="Declared overlay precision"
          value={precision}
          onChange={(event) => setPrecision(event.target.value as LocalOverlay['precision'])}
          options={[
            { value: 'unknown', label: 'Unknown' },
            { value: 'approximate', label: 'Approximate' },
            { value: 'exact', label: 'Source declares exact' },
          ]}
        />
      </div>
      <label className="mt-3 block text-sm">
        Local GeoJSON file
        <input
          aria-label="Local GeoJSON file"
          type="file"
          accept=".geojson,.json,application/geo+json,application/json"
          disabled={busy}
          className="mt-2 block max-w-full"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) importFile(file);
            event.target.value = '';
          }}
        />
      </label>
      <p className="mt-2 text-xs text-muted">
        WGS84 longitude/latitude only. Limits: 5 MiB, 2,000 features, 100,000 vertices and 256
        vertices per polygon. Wrapped polygons must be pre-split. URLs and file properties are never
        fetched.
      </p>
      {busy && <p role="status">Reading local geometry</p>}
      {error && <Alert tone="error">{error}</Alert>}
      {overlay && (
        <div className="mt-3 space-y-2">
          <p className="text-sm">
            {overlay.source} · {overlay.datasetDate} · {overlay.precision} precision ·{' '}
            {overlay.canonical.features.length} features · {overlay.vertices} vertices
          </p>
          <p className="text-xs text-muted">{overlay.attribution}</p>
          <label className="flex min-h-11 items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={visible}
              onChange={(event) => onVisible(event.target.checked)}
            />
            Show private overlay
          </label>
          <Button variant="secondary" onClick={() => onChange(null)}>
            Remove local overlay
          </Button>
          <ul aria-label="Imported geometry" className="space-y-1 text-xs">
            {overlay.canonical.features
              .slice(currentPage * 20, (currentPage + 1) * 20)
              .map((feature) => (
                <li key={feature.id}>
                  {feature.properties.label} · {feature.geometry.type}
                </li>
              ))}
          </ul>
          {overlay.canonical.features.length > 20 && (
            <div className="flex gap-3">
              <Button
                variant="secondary"
                disabled={currentPage === 0}
                onClick={() => setPage(currentPage - 1)}
              >
                Previous geometry
              </Button>
              <Button
                variant="secondary"
                disabled={(currentPage + 1) * 20 >= overlay.canonical.features.length}
                onClick={() => setPage(currentPage + 1)}
              >
                Next geometry
              </Button>
            </div>
          )}
        </div>
      )}
    </details>
  );
}
