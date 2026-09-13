import { Sparkline } from '@/components/charts/Sparkline';
import { BasisBadge } from '@/components/ui/BasisBadge';
import { Table, Td, Th } from '@/components/ui/Table';
import type { ClaimedLosses, ControlSummary, UkraineBoard } from '@/lib/api/ukraine';

const SPARK_DAYS = 30;

function ClaimCard({
  label,
  category,
  claims,
}: {
  label: string;
  category: string;
  claims: readonly ClaimedLosses[];
}) {
  const latest = claims.at(-1);
  const total = latest?.totals[category];
  if (latest === undefined || total === undefined) return null;
  const increase = latest.increase[category] ?? 0;
  const series = claims.slice(-SPARK_DAYS).map((claim) => claim.increase[category] ?? 0);
  return (
    <li className="flex flex-col gap-1 rounded-card border border-line bg-surface p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-[11px] uppercase tracking-wide text-muted">{label}</span>
        <BasisBadge basis="claimed" />
      </div>
      <span className="text-xl font-semibold tabular-nums">{total.toLocaleString('en-GB')}</span>
      <span className="text-xs text-muted">
        +{increase.toLocaleString('en-GB')} claimed on {latest.reported_on}
      </span>
      <Sparkline values={series} slot={2} label={`Daily claimed ${label.toLowerCase()}`} />
    </li>
  );
}

function ControlCard({ summary }: { summary: ControlSummary }) {
  const recent = summary.changes.length;
  return (
    <li className="flex flex-col gap-1 rounded-card border border-line bg-surface p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-[11px] uppercase tracking-wide text-muted">
          Russian-held places
        </span>
        <BasisBadge basis="reported" />
      </div>
      <span className="text-xl font-semibold tabular-nums">
        {(summary.counts.ru ?? 0).toLocaleString('en-GB')}
      </span>
      <span className="text-xs text-muted">
        {(summary.counts.contested ?? 0).toLocaleString('en-GB')} contested ·{' '}
        {recent.toLocaleString('en-GB')} status changes in 30 days
      </span>
      <span className="text-xs text-muted">of {summary.places_total.toLocaleString('en-GB')}</span>
    </li>
  );
}

/** The claimed running totals side by side with the reported control count, each badged. */
export function FiguresStrip({ board }: { board: UkraineBoard }) {
  const latest = board.claims.at(-1);
  return (
    <section id="figures" aria-labelledby="ukraine-figures-heading" className="flex flex-col gap-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 id="ukraine-figures-heading" className="text-base font-semibold">
          Headline figures
        </h2>
        {latest ? (
          <span className="text-xs text-muted">
            Claims are the General Staff of Ukraine&apos;s own cumulative figures for Russian
            losses, day {latest.day}.{' '}
            {latest.source_url ? (
              <a
                href={latest.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-ember hover:underline"
              >
                Original post
              </a>
            ) : null}
          </span>
        ) : (
          <span className="text-xs text-muted">No claim has been collected yet.</span>
        )}
      </div>
      <ul aria-label="Headline figures" className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
        {board.headline_categories.map((category) => (
          <ClaimCard
            key={category}
            label={board.categories[category] ?? category}
            category={category}
            claims={board.claims}
          />
        ))}
        {board.control ? <ControlCard summary={board.control} /> : null}
      </ul>
      {latest ? (
        <details className="text-sm">
          <summary className="cursor-pointer text-muted">All claimed categories as a table</summary>
          <div className="mt-2">
            <Table caption={`Claimed cumulative Russian losses, ${latest.reported_on}`}>
              <thead>
                <tr>
                  <Th>Category</Th>
                  <Th className="text-right">Total</Th>
                  <Th className="text-right">Daily increase</Th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(latest.totals).map(([key, value]) => (
                  <tr key={key}>
                    <Td>{board.categories[key] ?? key}</Td>
                    <Td className="text-right tabular-nums">{value.toLocaleString('en-GB')}</Td>
                    <Td className="text-right tabular-nums">
                      {(latest.increase[key] ?? 0).toLocaleString('en-GB')}
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </div>
        </details>
      ) : null}
    </section>
  );
}
