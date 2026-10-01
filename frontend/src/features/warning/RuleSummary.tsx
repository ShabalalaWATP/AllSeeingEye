import { useId } from 'react';

import type { SummaryRow } from '@/lib/alertRules';

/** The rule in plain words, read before saving. Problems are listed separately. */
export function RuleSummary({ rows, status }: { rows: readonly SummaryRow[]; status: string }) {
  const headingId = useId();
  return (
    <section
      aria-labelledby={headingId}
      className="rounded border border-line bg-ground/40 p-3 text-sm"
    >
      <h3 id={headingId} className="font-medium">
        Before you save: this alert rule will
      </h3>
      <dl className="mt-2 grid gap-x-4 gap-y-1 sm:grid-cols-[10rem_1fr]">
        {rows.map((row) => (
          <div key={row.label} className="contents">
            <dt className="text-muted">{row.label}</dt>
            <dd>{row.text}</dd>
          </div>
        ))}
        <div className="contents">
          <dt className="text-muted">Status</dt>
          <dd>{status}</dd>
        </div>
      </dl>
      <p className="mt-2 text-xs text-muted">
        Alert rules count matching items in connected feeds. They do not interpret meaning, so an
        alert is a prompt to check the evidence, not confirmation.
      </p>
    </section>
  );
}
