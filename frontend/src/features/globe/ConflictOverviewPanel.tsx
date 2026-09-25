import { useState } from 'react';
import { ConflictFilterPanel } from './ConflictFilterPanel';
import { FrontlineSourcesPanel } from './FrontlineSourcesPanel';
import type { useConflictFilters } from './useConflictFilters';
import type { useConflictRegions } from './useConflictRegions';
import { regionLabel, type ConflictRegion, type RegionStatus } from './conflictRegions';

export function ConflictOverviewPanel({
  regions,
  reports,
  onSelect,
}: {
  regions: ReturnType<typeof useConflictRegions>;
  reports: ReturnType<typeof useConflictFilters>;
  onSelect: (region: ConflictRegion) => void;
}) {
  const [tab, setTab] = useState<'regions' | 'reports' | 'frontlines'>('regions');
  return (
    <section aria-label="Conflict map controls">
      <div
        className="grid grid-cols-3 gap-1 border-b border-line p-2"
        role="group"
        aria-label="Conflict view"
      >
        {(['regions', 'reports', 'frontlines'] as const).map((value) => (
          <button
            key={value}
            type="button"
            aria-pressed={tab === value}
            onClick={() => setTab(value)}
            className="min-h-10 rounded px-1 text-xs text-muted aria-pressed:bg-cyan/10 aria-pressed:text-cyan"
          >
            {value === 'regions'
              ? 'Region overview'
              : value === 'reports'
                ? 'Report filters'
                : 'Frontlines'}
          </button>
        ))}
      </div>
      {tab === 'frontlines' ? (
        <FrontlineSourcesPanel />
      ) : tab === 'reports' ? (
        <ConflictFilterPanel {...reports} />
      ) : (
        <div className="space-y-3 p-3 text-xs">
          <p className="text-muted">
            Curated research regions, with a seven-day snapshot of retained tracker evidence. Select
            a region to locate it and inspect its reporting.
          </p>
          {!regions.enabled && (
            <p className="text-cyan">
              Switch on Conflict &amp; unrest in the left toolbar to display regions and reports.
            </p>
          )}
          <label className="flex min-h-10 items-center gap-2">
            <input
              type="checkbox"
              checked={regions.showRegions}
              onChange={(event) => regions.setShowRegions(event.target.checked)}
              className="accent-cyan"
            />
            Show regional overview markers
          </label>
          <label className="block text-muted">
            Find a conflict region
            <input
              type="search"
              maxLength={160}
              value={regions.query}
              onChange={(event) => regions.setQuery(event.target.value)}
              placeholder="Region, country code or party"
              className="mt-1 min-h-10 w-full rounded border border-line bg-ground px-2 text-text"
            />
          </label>
          <label className="block text-muted">
            Region classification
            <select
              value={regions.status}
              onChange={(event) => regions.setStatus(event.target.value as RegionStatus)}
              className="mt-1 min-h-10 w-full rounded border border-line bg-ground px-2 text-text"
            >
              <option value="all">All research regions</option>
              <option value="war">War regions (curated)</option>
              <option value="tension">Tension areas (curated)</option>
            </select>
          </label>
          <p className="text-[11px] text-muted">
            Red: curated war region. Amber: tension area. These are regional locators, not live
            incident positions or frontline boundaries.
          </p>
          {regions.loading && <p role="status">Loading region overview…</p>}
          {regions.error && (
            <p role="alert">
              Region overview unavailable. Individual report layers remain available.
            </p>
          )}
          <ul className="max-h-72 divide-y divide-line overflow-y-auto">
            {regions.filtered.map((region) => (
              <li key={region.card.conflict.id}>
                <button
                  type="button"
                  aria-pressed={regions.selected?.card.conflict.id === region.card.conflict.id}
                  disabled={!regions.enabled || !regions.showRegions}
                  onClick={() => onSelect(region)}
                  className="w-full rounded px-2 py-3 text-left hover:bg-white/5 aria-pressed:bg-cyan/10 disabled:opacity-40"
                >
                  <span className="block font-medium">{region.card.conflict.name}</span>
                  <span className="mt-1 block text-2xs text-muted">{regionLabel(region)}</span>
                  <span className="mt-2 block font-mono text-2xs text-cyan">
                    {region.card.activity.last_7d} violence groups · {region.card.reporting_7d}{' '}
                    related items / 7 d
                  </span>
                </button>
              </li>
            ))}
          </ul>
          {!regions.loading && !regions.error && regions.filtered.length === 0 && (
            <p>No regions match this search and nation filter.</p>
          )}
          <button
            type="button"
            onClick={regions.retry}
            disabled={regions.loading}
            className="min-h-9 text-cyan underline disabled:opacity-40"
          >
            Refresh region overview
          </button>
          {regions.fetchedAt && (
            <p className="text-2xs text-muted">
              Snapshot received{' '}
              {new Date(regions.fetchedAt).toLocaleTimeString('en-GB', { hour12: false })}. Region
              summaries use seven days of tracker evidence. Report filters apply to individual
              points.
            </p>
          )}
        </div>
      )}
    </section>
  );
}
