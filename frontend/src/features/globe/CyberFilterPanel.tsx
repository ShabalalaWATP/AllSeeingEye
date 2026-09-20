import { useState, type ComponentProps } from 'react';
import { Link } from 'react-router';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { CYBER_KIND_LABELS, cyberKind, type CyberKindFilter } from '@/lib/cyber';
import { useCyberFiltersStore } from '@/stores/cyberFilters';
import { useEventsStore } from '@/stores/events';
import { MapToolIntro } from '@/components/maps/MapToolIntro';
import type { useCyberCountryContext } from './useCyberCountryContext';
import { isMappedEvent, precisionLabel } from './geographicPrecision';
import { utcDate } from './context/contextPresentation';
import { ContextTabs } from './context/ContextTabs';
import { CyberLayerSwitches } from './CyberLayerSwitches';
import { GnssPanel } from './GnssPanel';
import { RadarAttackResults } from '@/components/cyber/RadarAttackResults';
import type { useRadarAttackMap } from './useRadarAttackMap';

interface CyberRecordsProps {
  cyber: ReturnType<typeof useCyberCountryContext>;
  onSelect: (event: LiveEvent) => void;
  picking: boolean;
  radar?: ReturnType<typeof useRadarAttackMap>;
}

/** Cyber incidents and GPS interference share one control; each keeps its own filters. */
export function CyberFilterPanel({
  gnss,
  ...records
}: CyberRecordsProps & { gnss?: ComponentProps<typeof GnssPanel> }) {
  if (!gnss) return <CyberRecords {...records} />;
  return (
    <>
      <CyberLayerSwitches
        recordCount={records.cyber.events.length}
        interferenceCount={gnss.filters.filtered.length}
      />
      <ContextTabs
        label="Cyber view"
        primaryLabel="Cyber records"
        secondaryLabel="GPS interference"
        primary={<CyberRecords {...records} />}
        secondary={<GnssPanel {...gnss} />}
      />
    </>
  );
}

function CyberRecords({ cyber, onSelect, picking, radar }: CyberRecordsProps) {
  const [showRadar, setShowRadar] = useState(false);
  const { kind, query, countryContext, setKind, setQuery, setCountryContext } =
    useCyberFiltersStore();
  const hidden = useEventsStore((state) => state.hidden.includes('cyber'));
  const country = useEventsStore((state) => state.country);
  const locatedCount = cyber.events.filter(isMappedEvent).length;
  return (
    <section aria-label="Cyber threat intelligence filters" className="map-tool-workspace">
      <MapToolIntro
        title="Cyber threat intelligence"
        description="Filter collected cyber records on the map and globe. Claims, signals and advisories retain their source meaning."
      />
      <Link to="/cyber" className="map-tool-text-button">
        Open Cyber Threat Intelligence
      </Link>
      <div className="rounded-lg border border-line/70 bg-surface/50 p-3">
        {radar && (
          <label className="mb-3 flex min-h-11 items-center gap-2 text-xs">
            <input type="checkbox" checked={radar.enabled} onChange={radar.toggle} />
            Show Cloudflare observed traffic on map
          </label>
        )}
        {radar?.active && (
          <p role="status" className="mb-3 text-[11px] leading-5 text-muted">
            <span className="inline-block h-2 w-2 rounded-sm bg-violet-400" aria-hidden="true" />{' '}
            Purple CF labels: Cloudflare-observed mitigated traffic shares by target billing
            country. L3/4 is bytes; L7 is requests.{' '}
            {radar.loading ? 'Loading…' : `${radar.rows.length} countries mapped.`}
            {radar.error && ' Radar could not be loaded.'}
            {radar.data && radar.data.status !== 'ready' && ` Source status: ${radar.data.status}.`}
          </p>
        )}
        <button
          type="button"
          className="flex w-full items-center justify-between gap-2 text-left text-xs font-medium"
          aria-expanded={showRadar}
          onClick={() => setShowRadar((value) => !value)}
        >
          <span>Cloudflare Radar attack trends</span>
          <span aria-hidden="true">{showRadar ? '−' : '+'}</span>
        </button>
        {showRadar && (
          <div className="mt-3 space-y-3 border-t border-line/60 pt-3">
            {radar?.data ? (
              <RadarAttackResults data={radar.data} compact />
            ) : (
              <p className="text-[11px] text-muted">
                {radar?.loading
                  ? 'Loading Cloudflare Radar…'
                  : 'Enable Cyber and the map layer to load the current distribution.'}
              </p>
            )}
            {radar?.error && (
              <button type="button" className="text-xs text-cyan underline" onClick={radar.reload}>
                Retry Cloudflare Radar
              </button>
            )}
            <p className="text-[11px] leading-5 text-muted">
              Provider-wide shares by billing country, not map incidents or attacker locations.
            </p>
          </div>
        )}
      </div>
      <label className="map-tool-field">
        Record type
        <select
          className="map-tool-input"
          value={kind}
          onChange={(event) => setKind(event.target.value as CyberKindFilter)}
        >
          <option value="all">All cyber records</option>
          {Object.entries(CYBER_KIND_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <label className="map-tool-field">
        Search cyber records
        <input
          type="search"
          className="map-tool-input"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Victim, group, CVE, source…"
        />
      </label>
      <label className="flex min-h-11 items-center gap-2 text-xs">
        <input
          type="checkbox"
          checked={countryContext}
          onChange={(event) => setCountryContext(event.target.checked)}
        />
        Show approximate country context
      </label>
      <p className="map-tool-help">
        Country context uses source-attributed victim or outage countries. Labelled reference
        markers show collected record counts at country centres, not incident coordinates, attackers
        or attack paths. Country-only records remain under Not plotted in location quality.
      </p>
      <p className="map-tool-help">
        Ransomware entries are unverified claims. Connectivity signals do not establish a
        cyberattack or a continuing outage. Advisories and KEV entries are not located incidents.
      </p>
      <p className="map-tool-help">
        {country ? `Nation: ${country}.` : 'Worldwide context.'} The shared time and
        location-quality filters also apply. Context is a separate bounded snapshot, independent of
        the visible map extent.
      </p>
      {hidden && (
        <p className="map-tool-notice">
          The Cyber layer is off. Enable its switch to load records and show eligible markers.
        </p>
      )}
      <div className="flex items-center justify-between gap-2 border-t border-line pt-2">
        <p className="text-xs text-muted">{cyber.events.length} matching collected records</p>
        <button
          type="button"
          className="map-tool-text-button"
          disabled={hidden || cyber.loading}
          onClick={cyber.refresh}
        >
          Refresh cyber records
        </button>
      </div>
      {cyber.loading && (
        <p role="status" className="map-tool-help">
          Loading cyber records…
        </p>
      )}
      {cyber.error && (
        <p role="alert" className="map-tool-notice">
          {cyber.error}
        </p>
      )}
      {!hidden && !cyber.loading && !cyber.error && (
        <div role="status" className="map-tool-notice">
          <p>
            {cyber.groups.length} country reference markers · {locatedCount} reported locations
          </p>
          {!cyber.events.length ? (
            <p>
              No matching records in this collected snapshot. Try a wider Event time or Location
              quality selection. New feed records are checked every minute while Cyber is visible.
            </p>
          ) : !cyber.groups.length && !locatedCount ? (
            <p>
              {countryContext
                ? 'These records have no usable incident or victim/outage country location. Read them below or open Cyber Threat Intelligence.'
                : 'Country reference markers are hidden. Enable approximate country context to show eligible victim and outage countries.'}
            </p>
          ) : null}
        </div>
      )}
      <ul className="map-tool-list">
        {cyber.events.slice(0, 25).map((event) => (
          <li key={event.id}>
            <button
              type="button"
              disabled={picking}
              onClick={() => onSelect(event)}
              className="map-tool-list-button w-full text-left"
            >
              <span className="block text-xs font-medium">{event.title}</span>{' '}
              <span className="mt-1 block text-[10px] text-muted">
                {CYBER_KIND_LABELS[cyberKind(event)]} · {precisionLabel(event)}
              </span>
            </button>
          </li>
        ))}
      </ul>
      <p className="map-tool-help">
        Snapshot: {utcDate(cyber.fetchedAt)}. Refreshes every minute while Cyber is visible. Up to
        500 collected records and 25 list entries.{' '}
        {cyber.limited ? 'The snapshot reached its limit. ' : ''}Counts are not unique verified
        incidents or complete coverage.
      </p>
    </section>
  );
}
