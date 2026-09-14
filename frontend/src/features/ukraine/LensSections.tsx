import { StackedColumns, type ColumnSeries } from '@/components/charts/StackedColumns';
import { BasisBadge, type Basis } from '@/components/ui/BasisBadge';
import { Table, Td, Th } from '@/components/ui/Table';
import {
  GROUP_LABELS,
  LENS_LABELS,
  type Lens,
  type UkraineBoard,
  type UpdateGroup,
} from '@/lib/api/ukraine';

import { UpdateRow } from './UpdateRow';

const LENSES: readonly Lens[] = ['equipment', 'workforce', 'casualties'];
const GROUP_SLOTS: Record<UpdateGroup, ColumnSeries['slot']> = {
  assessments: 1,
  ukrainian: 2,
  russian: 3,
  international: 4,
};
const BLURBS: Record<Lens, string> = {
  equipment: 'Deliveries, new systems, losses and industry, matched on vocabulary alone.',
  workforce: 'Mobilisation, recruitment, contract service, desertion and foreign personnel.',
  casualties: 'Killed, wounded, prisoners and the counts published about them.',
  strikes: '',
  diplomacy: '',
};
const BASES: Record<string, Basis> = {
  claimed: 'claimed',
  assessed: 'assessed',
  visually_confirmed: 'visually_confirmed',
  documented: 'documented',
  reported: 'reported',
};

function LensChart({ board, lens }: { board: UkraineBoard; lens: Lens }) {
  const series = board.lens_series.find((item) => item.lens === lens);
  if (!series) return null;
  const columns: ColumnSeries[] = (Object.keys(GROUP_LABELS) as UpdateGroup[]).map((group) => ({
    key: group,
    label: GROUP_LABELS[group],
    slot: GROUP_SLOTS[group],
    values: series.groups[group] ?? [],
  }));
  return (
    <StackedColumns
      days={series.days}
      series={columns}
      label={`${LENS_LABELS[lens]} items per day by reporting group`}
      unit="items"
    />
  );
}

/** The HRMMU months, the Oryx month and the curated references, each with its basis. */
function CasualtyDetails({ board }: { board: UkraineBoard }) {
  const harm = board.civilian_harm;
  if (!harm) return null;
  return (
    <div className="flex flex-col gap-3">
      <Table caption="Civilian casualties verified by the UN monitoring mission, by month">
        <thead>
          <tr>
            <Th>Month</Th>
            <Th className="text-right">Killed</Th>
            <Th className="text-right">Injured</Th>
            <Th>Published</Th>
          </tr>
        </thead>
        <tbody>
          {harm.months.map((month) => (
            <tr key={month.month}>
              <Td>
                <a
                  href={month.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-ember hover:underline"
                >
                  {month.month.slice(0, 7)}
                </a>
              </Td>
              <Td className="text-right tabular-nums">
                {month.killed === null ? 'not stated' : month.killed.toLocaleString('en-GB')}
              </Td>
              <Td className="text-right tabular-nums">
                {month.injured === null ? 'not stated' : month.injured.toLocaleString('en-GB')}
              </Td>
              <Td>{month.published_on ?? 'unknown'}</Td>
            </tr>
          ))}
        </tbody>
      </Table>
      <ul aria-label="Casualty references" className="grid gap-2 md:grid-cols-2">
        {harm.references.map((reference) => (
          <li key={reference.id} className="rounded-card border border-line bg-surface p-3 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <a
                href={reference.url}
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium text-text hover:underline"
              >
                {reference.label}
              </a>
              <BasisBadge basis={BASES[reference.basis] ?? 'reported'} />
            </div>
            <p className="mt-1 text-xs text-muted">{reference.text}</p>
            <p className="mt-1 font-mono text-[10px] text-muted">as of {reference.as_of}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Equipment, workforce and casualty news: a chart of items per day and the matching items. */
export function LensSections({ board }: { board: UkraineBoard }) {
  return (
    <section id="lenses" aria-labelledby="ukraine-lenses-heading" className="flex flex-col gap-6">
      <h2 id="ukraine-lenses-heading" className="text-base font-semibold">
        Equipment, workforce and casualty news
      </h2>
      {LENSES.map((lens) => {
        const items = board.updates.filter((update) => update.lenses.includes(lens));
        return (
          <section
            key={lens}
            aria-label={`${LENS_LABELS[lens]} news`}
            className="flex flex-col gap-3"
          >
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h3 className="text-sm font-semibold text-text">{LENS_LABELS[lens]} news</h3>
              <span className="text-xs text-muted">{BLURBS[lens]}</span>
            </div>
            <LensChart board={board} lens={lens} />
            {lens === 'casualties' ? <CasualtyDetails board={board} /> : null}
            {items.length === 0 ? (
              <p className="text-sm text-muted">
                No retained item matches this lens in the window.
              </p>
            ) : (
              <ul aria-label={`${LENS_LABELS[lens]} items`}>
                {items.map((update) => (
                  <UpdateRow key={update.event.id} update={update} />
                ))}
              </ul>
            )}
          </section>
        );
      })}
    </section>
  );
}
