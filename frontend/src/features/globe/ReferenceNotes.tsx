import { useEffect, useState } from 'react';

import type { LiveEvent } from '@/lib/api/eventSchemas';
import { fetchReference, type ReferenceEntry, type ReferenceKind } from '@/lib/api/reference';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';

const KIND_LABELS: Record<ReferenceKind, string> = {
  vessel: 'Vessel on record',
  aircraft: 'Aircraft on record',
  aircraft_type: 'Aircraft type',
};

function text(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}

/** Which reference tables an observed event can be checked against, by broadcast identifier. */
export function referenceQueries(event: LiveEvent): { kind: ReferenceKind; keys: string[] }[] {
  const queries: { kind: ReferenceKind; keys: string[] }[] = [];
  if (event.category === 'maritime') {
    const mmsi = text(event.attributes.mmsi);
    if (mmsi) queries.push({ kind: 'vessel', keys: [mmsi] });
  }
  if (event.category === 'aviation') {
    const registration = text(event.attributes.registration);
    const type = text(event.attributes.aircraft_type);
    if (registration) queries.push({ kind: 'aircraft', keys: [registration] });
    if (type) queries.push({ kind: 'aircraft_type', keys: [type] });
  }
  return queries;
}

/** Public background for the identifier an aircraft or vessel broadcast, if it is on record. */
export function ReferenceNotes({ event }: { event: LiveEvent }) {
  const request = useScopedRequest();
  const queries = referenceQueries(event);
  const wanted = JSON.stringify(queries);
  const [state, setState] = useState<{ wanted: string; items: ReferenceEntry[] } | null>(null);
  useEffect(() => {
    if (wanted === '[]') return;
    const signal = request();
    let current = true;
    const parsed = JSON.parse(wanted) as { kind: ReferenceKind; keys: string[] }[];
    void Promise.allSettled(parsed.map((q) => fetchReference(q.kind, q.keys, signal))).then(
      (results) => {
        if (!current || signal.aborted) return;
        setState({
          wanted,
          items: results.flatMap((r) => (r.status === 'fulfilled' ? r.value.items : [])),
        });
      },
    );
    return () => {
      current = false;
      request();
    };
  }, [wanted, request]);
  const items = state?.wanted === wanted ? state.items : [];
  if (!items.length) return null;
  return (
    <section aria-label="Reference notes" className="mt-3 rounded border border-line p-3 text-xs">
      {items.map((item) => (
        <div key={`${item.kind}:${item.key}`} className="mb-2 last:mb-0">
          <p className="text-[10px] uppercase tracking-wider text-cyan">
            {KIND_LABELS[item.kind]} · {item.key}
          </p>
          <p className="mt-0.5 font-medium text-text">{item.name}</p>
          {item.description && <p className="text-muted">{item.description}</p>}
          {item.detail && <p className="text-muted">{item.detail}</p>}
          {item.links.length > 0 && (
            <p className="mt-1 flex flex-wrap gap-3">
              {item.links.map((link) => (
                <a
                  key={link.url}
                  href={link.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-cyan underline"
                >
                  {link.label}
                </a>
              ))}
            </p>
          )}
        </div>
      ))}
      <p className="mt-2 text-[11px] leading-relaxed text-muted">
        Background for the broadcast identifier, not confirmation that this is the object on record.
        Identifiers are reused, mistyped and spoofed.
      </p>
    </section>
  );
}
