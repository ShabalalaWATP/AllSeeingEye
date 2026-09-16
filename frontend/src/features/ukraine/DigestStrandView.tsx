import { SourceLink } from '@/components/ui/SourceLink';
import type { UkraineDigestCitation, UkraineDigestStrand } from '@/lib/api/ukraineDigest';

export function formatDay(iso: string): string {
  const parsed = new Date(iso.length === 10 ? `${iso}T00:00:00Z` : iso);
  if (Number.isNaN(parsed.getTime())) return iso;
  return new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(parsed);
}

/** One piece of evidence a change names: its id, its headline and, when known, its link. */
function Citation({ citation }: { citation: UkraineDigestCitation }) {
  const dated = citation.dated_on ? `, ${formatDay(citation.dated_on)}` : '';
  const label = `${citation.label}${dated}`;
  return (
    <li className="flex min-w-0 max-w-full items-baseline gap-1.5 rounded border border-line bg-surface px-2 py-1 sm:max-w-[22rem]">
      <span className="shrink-0 font-mono text-[10px] text-muted" aria-hidden="true">
        {citation.id}
      </span>
      <span
        className="min-w-0 truncate text-[11px] text-muted"
        title={`${citation.source_id}: ${label}`}
      >
        {citation.url ? <SourceLink url={citation.url}>{label}</SourceLink> : label}
      </span>
    </li>
  );
}

/**
 * A summary and the changes behind it. Each change lists only the evidence the model cited,
 * so a reader can check the wording against the item it rests on.
 */
export function DigestStrandView({
  id,
  title,
  strand,
  citations,
}: {
  id: string;
  title: string;
  strand: UkraineDigestStrand;
  citations: Map<string, UkraineDigestCitation>;
}) {
  return (
    <section aria-labelledby={id} className="flex flex-col gap-3">
      <h3 id={id} className="text-sm font-semibold text-text">
        {title}
      </h3>
      <p className="max-w-3xl text-sm text-muted">{strand.summary}</p>
      <ul aria-label={`${title} changes`} className="flex flex-col gap-3">
        {strand.changes.map((change) => (
          <li
            key={change.text}
            className="flex flex-col gap-2 rounded-md border border-line bg-surface-2 p-3"
          >
            <p className="text-sm text-text">{change.text}</p>
            <ul aria-label="Sources for this change" className="flex flex-wrap gap-1.5">
              {change.source_ids.map((sourceId) => {
                const citation = citations.get(sourceId);
                return citation ? <Citation key={sourceId} citation={citation} /> : null;
              })}
            </ul>
          </li>
        ))}
      </ul>
    </section>
  );
}
