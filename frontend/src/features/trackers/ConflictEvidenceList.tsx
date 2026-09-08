import type { ConflictDetail } from '@/lib/api/trackers';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { ConflictEvidenceRow } from './ConflictEvidenceRow';

export function ConflictEvidenceList({
  events,
  groups,
}: {
  events: LiveEvent[];
  groups: ConflictDetail['evidence_groups'];
}) {
  const byId = new Map(events.map((event) => [event.id, event]));
  const seen = new Set<string>();
  const bundles: { representative: LiveEvent; linked: LiveEvent[]; reportCount: number }[] = [];
  for (const group of groups) {
    const ids = [...new Set([group.representative_id, ...group.report_ids])];
    const loaded = ids.flatMap((id) => {
      const event = byId.get(id);
      return event && !seen.has(id) ? [event] : [];
    });
    const representative = loaded[0];
    if (!representative) continue;
    loaded.forEach((event) => seen.add(event.id));
    bundles.push({ representative, linked: loaded.slice(1), reportCount: group.report_count });
  }
  for (const event of events)
    if (!seen.has(event.id)) {
      seen.add(event.id);
      bundles.push({ representative: event, linked: [], reportCount: 1 });
    }
  return (
    <ul className="divide-y divide-line" aria-label="Collected evidence">
      {bundles.map(({ representative, linked, reportCount }) => (
        <li key={representative.id}>
          <ConflictEvidenceRow event={representative} />
          {reportCount > 1 && (
            <p className="text-[11px] text-muted">
              {reportCount} related reports grouped; independence not established.
            </p>
          )}
          {linked.length > 0 && (
            <details className="mb-3 rounded-md border border-line px-3">
              <summary className="cursor-pointer py-2 text-xs text-cyan">
                View {linked.length} additional loaded reports
              </summary>
              <ul className="divide-y divide-line">
                {linked.map((event) => (
                  <li key={event.id}>
                    <ConflictEvidenceRow event={event} />
                  </li>
                ))}
              </ul>
            </details>
          )}
        </li>
      ))}
    </ul>
  );
}
