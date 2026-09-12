import { SourceLink } from '@/components/ui/SourceLink';
import type { CyberItem } from '@/lib/api/cyber';

export function CyberVulnerabilities({ items }: { items: readonly CyberItem[] }) {
  const rows = items.filter(
    (item): item is CyberItem & { kev: NonNullable<CyberItem['kev']> } => item.kev !== null,
  );
  return (
    <section aria-label="Exploited vulnerabilities" className="space-y-5">
      <div>
        <h2 className="text-xl font-semibold">Exploitation to prioritise</h2>
        <p className="mt-2 max-w-4xl text-sm leading-6 text-muted">
          Recent additions to CISA’s Known Exploited Vulnerabilities catalogue. Match affected
          products to your own environment before prioritising action. Catalogue addition is not the
          date exploitation began.
        </p>
      </div>
      {!rows.length && (
        <p className="border-y border-line py-8 text-sm text-muted">
          No KEV additions match this period and search. This does not mean there are no exploited
          vulnerabilities.
        </p>
      )}
      <div className="divide-y divide-line">
        {rows.map((item) => {
          const kev = item.kev;
          return (
            <article key={item.id} className="grid gap-4 py-5 md:grid-cols-[13rem_1fr] md:gap-8">
              <div>
                <h3 className="font-mono text-base text-cyan">
                  <SourceLink url={item.url}>{kev.cve}</SourceLink>
                </h3>
                <p className="mt-2 text-xs text-muted">Added {kev.date_added}</p>
                <p className="mt-2 text-xs text-muted">
                  Ransomware use: {kev.ransomware_use || 'Not specified'}
                </p>
              </div>
              <div className="space-y-3">
                <p className="font-semibold">
                  {kev.vendor} · {kev.product}
                </p>
                {item.summary && <p className="max-w-4xl text-sm leading-7">{item.summary}</p>}
                <div className="border-l-2 border-cyan/60 pl-3">
                  <h4 className="text-xs font-semibold">CISA required action</h4>
                  <p className="mt-1 text-sm leading-6 text-text/90">
                    {kev.required_action ||
                      'Read the linked CISA record and vendor guidance for mitigation details.'}
                  </p>
                </div>
                {kev.due_date && (
                  <p className="text-xs leading-5 text-muted">
                    Catalogue due date: {kev.due_date}. This federal directive deadline is not a
                    universal deadline for every organisation.
                  </p>
                )}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
