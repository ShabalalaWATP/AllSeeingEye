import type { LiveEvent } from '@/lib/api/eventSchemas';

/** Keep the provider credit visible whenever its vessel observations are displayed. */
export function MaritimeAttribution({
  events,
  hidden,
}: {
  events: readonly LiveEvent[];
  hidden: boolean;
}) {
  if (hidden || !events.some((event) => event.source_id === 'barentswatch_ais')) return null;
  return (
    <p className="pointer-events-none absolute top-12 right-20 left-20 z-10 text-right text-[10px] text-muted">
      <a
        className="pointer-events-auto rounded bg-black/80 px-2 py-1 underline decoration-white/30 underline-offset-2 focus-visible:outline-2 focus-visible:outline-cyan"
        href="https://www.barentswatch.no/en/articles/api-terms-and-conditions/"
        target="_blank"
        rel="noreferrer"
      >
        Data delivered by BarentsWatch · Norwegian Coastal Administration
      </a>
    </p>
  );
}
