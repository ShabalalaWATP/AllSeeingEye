import { SourceLink } from '@/components/ui/SourceLink';
import type { CyberItem } from '@/lib/api/cyber';

export function CyberVulnerabilities({ items }: { items: readonly CyberItem[] }) {
  const rows = items.filter(
    (item): item is CyberItem & { kev: NonNullable<CyberItem['kev']> } => item.kev !== null,
  );
  const ransomware = rows.filter((row) => row.kev.ransomware_use.toLowerCase() === 'known').length;
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap gap-3 text-xs">
        <span className="rounded-full border border-line/70 px-3 py-1 text-muted">
          <span className="font-semibold text-text">{rows.length}</span> catalogue additions
        </span>
        <span className="rounded-full border border-line/70 px-3 py-1 text-muted">
          <span className="font-semibold text-text">{ransomware}</span> with known ransomware use
        </span>
      </div>
      {!rows.length && (
        <p className="rounded-xl border border-dashed border-line/70 px-4 py-8 text-center text-sm text-muted">
          No KEV additions match this period and search. This does not mean there are no exploited
          vulnerabilities.
        </p>
      )}
      <div className="grid gap-3 xl:grid-cols-2">
        {rows.map((item) => {
          const kev = item.kev;
          return (
            <article
              key={item.id}
              className="rounded-xl border border-line/60 bg-surface/50 p-4 sm:p-5"
            >
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h3 className="font-mono text-base text-cyan">
                  <SourceLink url={item.url}>{kev.cve}</SourceLink>
                </h3>
                <p className="text-xs text-muted">Added {kev.date_added}</p>
              </div>
              <p className="mt-2 font-semibold">
                {kev.vendor} · {kev.product}
              </p>
              {item.summary && (
                <p className="mt-2 max-w-4xl text-sm leading-6 text-text/90">{item.summary}</p>
              )}
              <div className="mt-3 border-l-2 border-cyan/60 pl-3">
                <h4 className="text-xs font-semibold">CISA required action</h4>
                <p className="mt-1 text-sm leading-6 text-text/90">
                  {kev.required_action ||
                    'Read the linked CISA record and vendor guidance for mitigation details.'}
                </p>
              </div>
              <dl className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted">
                <div>
                  <dt className="sr-only">Ransomware use</dt>
                  <dd>Ransomware use: {kev.ransomware_use || 'Not specified'}</dd>
                </div>
                {kev.cwes && (
                  <div>
                    <dt className="sr-only">Weakness</dt>
                    <dd className="font-mono">{kev.cwes}</dd>
                  </div>
                )}
              </dl>
              {kev.due_date && (
                <p className="mt-2 text-xs leading-5 text-muted">
                  Catalogue due date: {kev.due_date}. This federal directive deadline is not a
                  universal deadline for every organisation.
                </p>
              )}
            </article>
          );
        })}
      </div>
    </div>
  );
}
