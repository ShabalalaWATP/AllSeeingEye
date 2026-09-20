import { useState } from 'react';
import { parseCoordinatePair } from '@/lib/map/coordinateWorkbench';
import type { Position } from '@/lib/map/geoJsonTypes';
import type { useTerrainAnalysis, TerrainStudyDraft } from './useTerrainAnalysis';
import { TerrainProfileChart } from './TerrainProfileChart';

export function TerrainAnalysisPanel({
  points,
  study,
}: {
  points: readonly Position[];
  study: ReturnType<typeof useTerrainAnalysis>;
}) {
  const [inputError, setInputError] = useState<string | null>(null);
  const { draft, result } = study;
  function edit(patch: Partial<TerrainStudyDraft>) {
    study.clear();
    setInputError(null);
    study.setDraft({ ...draft, ...patch });
  }
  function run() {
    setInputError(null);
    try {
      if (draft.mode === 'visibility' && (!draft.observerHeightM.trim() || !draft.radiusKm.trim()))
        throw new Error('Enter an observer height and visibility radius.');
      void study.run({
        mode: draft.mode,
        origin: parseCoordinatePair(draft.originLat, draft.originLon),
        ...(draft.mode === 'profile'
          ? { end: parseCoordinatePair(draft.endLat, draft.endLon) }
          : {}),
        radiusKm: Number(draft.radiusKm),
        observerHeightM: draft.mode === 'profile' ? 2 : Number(draft.observerHeightM),
      });
    } catch (failure) {
      setInputError(failure instanceof Error ? failure.message : 'Check the coordinates.');
    }
  }
  const fields = [
    ['originLat', 'Start / observer latitude'],
    ['originLon', 'Start / observer longitude'],
    ...(draft.mode === 'profile'
      ? [
          ['endLat', 'End latitude'],
          ['endLon', 'End longitude'],
        ]
      : []),
  ] as [keyof TerrainStudyDraft, string][];
  return (
    <section className="map-tool-workspace" aria-label="Terrain analysis">
      <p>
        Inspect ground elevation or sampled geometric visibility. Choose sites from your drawing or
        enter coordinates.
      </p>
      <label className="block">
        Analysis
        <select
          className="mt-1 w-full rounded border border-white/20 bg-black p-2"
          value={draft.mode}
          onChange={(event) => edit({ mode: event.target.value as TerrainStudyDraft['mode'] })}
        >
          <option value="profile">Terrain profile</option>
          <option value="visibility">Sampled viewshed</option>
        </select>
      </label>
      <button
        type="button"
        className="rounded border border-white/20 px-3 py-2 disabled:opacity-40"
        disabled={points.length < (draft.mode === 'profile' ? 2 : 1)}
        onClick={() => {
          const first = points[0],
            second = points[1];
          if (first)
            edit({
              originLat: String(first[1]),
              originLon: String(first[0]),
              ...(second ? { endLat: String(second[1]), endLon: String(second[0]) } : {}),
            });
        }}
      >
        Use first {draft.mode === 'profile' ? 'two points' : 'point'} from drawing / measurement
      </button>
      {draft.mode === 'profile' && points.length > 2 && (
        <p className="text-muted">
          The profile follows a direct geodesic between the first two points, not the complete drawn
          path.
        </p>
      )}
      {fields.map(([key, label]) => (
        <label key={key} className="block">
          {label}
          <input
            className="mt-1 w-full rounded border border-white/20 bg-black p-2"
            value={draft[key]}
            maxLength={100}
            onChange={(event) => edit({ [key]: event.target.value })}
          />
        </label>
      ))}
      {draft.mode === 'visibility' && (
        <>
          <label className="block">
            Radius (km)
            <input
              className="mt-1 w-full rounded border border-white/20 bg-black p-2"
              type="number"
              min="0.01"
              max="50"
              step="0.1"
              value={draft.radiusKm}
              onChange={(event) => edit({ radiusKm: event.target.value })}
            />
          </label>
          <label className="block">
            Observer height above ground (m)
            <input
              className="mt-1 w-full rounded border border-white/20 bg-black p-2"
              type="number"
              min="0.5"
              max="500"
              step="0.5"
              value={draft.observerHeightM}
              onChange={(event) => edit({ observerHeightM: event.target.value })}
            />
          </label>
        </>
      )}
      <p className="text-muted">
        Profiles: up to 200 km. Visibility: up to 50 km, 409 ground samples. Large tile requests may
        need a smaller area.
      </p>
      <div className="flex gap-2">
        <button
          type="button"
          className="rounded border border-cyan/50 px-3 py-2 disabled:opacity-40"
          disabled={study.busy}
          onClick={run}
        >
          {study.busy ? 'Analysing terrain…' : 'Analyse terrain'}
        </button>
        <button
          type="button"
          className="rounded border border-white/20 px-3 py-2"
          onClick={study.clear}
        >
          {study.busy ? 'Cancel' : 'Clear result'}
        </button>
      </div>
      {(inputError ?? study.error) && (
        <p role="alert" className="text-red-300">
          {inputError ?? study.error}
        </p>
      )}
      {result && (
        <div className="space-y-3" aria-live="polite">
          {result.input.mode === 'profile' ? (
            <TerrainProfileChart
              study={result}
              highlighted={study.highlighted}
              onHighlight={study.setHighlighted}
            />
          ) : (
            <p>
              Marked ground samples:{' '}
              {result.samples.filter((sample) => sample.visibility === 'visible').length} visible
              (mint), {result.samples.filter((sample) => sample.visibility === 'hidden').length}{' '}
              hidden (orange),{' '}
              {result.samples.filter((sample) => sample.visibility === 'unknown').length} unknown
              (grey).
            </p>
          )}
          <p>
            {result.samples.length} samples · source range{' '}
            {result.minimumM?.toFixed(0) ?? 'unknown'} to {result.maximumM?.toFixed(0) ?? 'unknown'}{' '}
            m.
          </p>
          {result.warnings.map((warning) => (
            <p key={warning} className="text-muted">
              {warning}
            </p>
          ))}
          <p className="text-muted">
            {result.provenance.provider} · nominal tile resolution{' '}
            {result.provenance.resolution_m.toFixed(0)} m. {result.provenance.limitations}
          </p>
          <a
            className="text-cyan underline"
            href={result.provenance.attribution_url}
            target="_blank"
            rel="noreferrer"
          >
            Terrain attribution
          </a>
          <p className="text-muted">{result.provenance.attribution}</p>
        </div>
      )}
    </section>
  );
}
