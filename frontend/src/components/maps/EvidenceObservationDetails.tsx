import type { EvidenceItem } from '@/lib/api/reports';
import { formatUtc } from '@/lib/format';

export function EvidenceObservationDetails({ item }: { item: EvidenceItem }) {
  const { observation, geometry } = item;
  if (!observation && !geometry) return null;
  const title = observation ? 'Source observation' : 'Source geometry';
  const rows = [
    ...(observation
      ? [
          ['Acquired', formatUtc(observation.acquired_at)],
          ['Processed', formatUtc(observation.processed_at)],
          ['Collection', observation.collection_id],
          ['Scene / record', observation.item_id],
          [
            'Scene cloud cover',
            observation.scene_cloud_cover === null
              ? 'Unknown'
              : `${observation.scene_cloud_cover}%`,
          ],
        ]
      : []),
    ...(geometry
      ? [
          ['Location role', geometry.location_role.replace(/_/g, ' ')],
          ['Source geometry', geometry.geometry.type],
          ['Precision', geometry.precision],
          ['Method', geometry.method],
          ['Attribution', geometry.attribution],
        ]
      : []),
  ];
  return (
    <section aria-label={title} className="min-w-0 border-l-2 border-line pl-4">
      <h3 className="text-sm font-medium">{title}</h3>
      <dl className="mt-3 grid gap-x-8 gap-y-3 sm:grid-cols-2">
        {rows.map(([label, value]) => (
          <div key={label} className="min-w-0">
            <dt className="text-xs text-muted">{label}</dt>
            <dd className="mt-1 text-sm [overflow-wrap:anywhere]">{value}</dd>
          </div>
        ))}
      </dl>
      {observation && (
        <p className="mt-3 text-xs text-muted [overflow-wrap:anywhere]">
          {observation.limitations}
        </p>
      )}
      {geometry?.location_role === 'observation_footprint' && (
        <p className="mt-2 text-xs text-muted">
          The footprint describes scene coverage. It does not establish an event location or usable
          imagery.
        </p>
      )}
    </section>
  );
}
