import { Alert, LoadingNote } from '@/components/ui/Alert';
import { BasisBadge } from '@/components/ui/BasisBadge';
import { Button } from '@/components/ui/Button';
import { Table, Td, Th } from '@/components/ui/Table';
import { describeError } from '@/lib/api/errors';
import {
  STATUS_LABELS,
  fetchUkraineControl,
  type ControlStatus,
  type ControlSummary,
  type UkraineControl,
} from '@/lib/api/ukraine';
import { formatUtc } from '@/lib/format';

import { STATUS_RGB } from './controlLayers';
import { useUkraineMap, type Hover } from './useUkraineMap';

const LEGEND: readonly ControlStatus[] = ['ru', 'contested', 'ua'];

function swatch(status: ControlStatus) {
  const [r, g, b] = STATUS_RGB[status];
  return { backgroundColor: `rgb(${r} ${g} ${b})` };
}

function Tooltip({ hover }: { hover: Hover }) {
  const { settlement, x, y } = hover;
  const [wiki, boosted, deepstate] = settlement.votes;
  return (
    <div
      role="tooltip"
      className="pointer-events-none absolute z-20 max-w-64 rounded border border-line bg-ground/95 p-2 text-xs shadow-lg"
      style={{ left: x + 12, top: y + 12 }}
    >
      <p className="font-medium text-text">{settlement.name}</p>
      <p className="text-muted">
        {settlement.oblast} · {STATUS_LABELS[settlement.status]}
      </p>
      <p className="text-muted">
        Votes: Wikipedia {wiki}, boosted {boosted}, DeepState {deepstate}
        {settlement.since ? ` · since ${settlement.since}` : ''}
      </p>
    </div>
  );
}

/** Oblast counts are the accessible reading of the map and the fallback without WebGL. */
export function ControlTable({ summary }: { summary: ControlSummary }) {
  const rows = summary.oblasts.filter((row) => row.ru + row.contested > 0);
  return (
    <Table caption="Reported control by oblast (populated places)">
      <thead>
        <tr>
          <Th>Oblast</Th>
          <Th className="text-right">Ukrainian-held</Th>
          <Th className="text-right">Russian-held</Th>
          <Th className="text-right">Contested</Th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.name}>
            <Td>{row.name}</Td>
            <Td className="text-right tabular-nums">{row.ua.toLocaleString('en-GB')}</Td>
            <Td className="text-right tabular-nums">{row.ru.toLocaleString('en-GB')}</Td>
            <Td className="text-right tabular-nums">{row.contested.toLocaleString('en-GB')}</Td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

export function UkraineMap({
  load = fetchUkraineControl,
}: {
  load?: () => Promise<UkraineControl>;
}) {
  const { container, supported, failed, hover, control, refit } = useUkraineMap(load);
  const summary = control.data?.summary ?? null;
  return (
    <section id="map" aria-labelledby="ukraine-map-heading" className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="ukraine-map-heading" className="text-base font-semibold">
          Reported control and the frontline
        </h2>
        <div className="flex items-center gap-2">
          <BasisBadge basis="reported" />
          {summary ? (
            <span className="font-mono text-xs text-muted">assessed {summary.assessment_date}</span>
          ) : null}
          {supported ? (
            <Button variant="secondary" onClick={refit}>
              Fit to Ukraine
            </Button>
          ) : null}
        </div>
      </div>
      {control.error ? <Alert tone="error">{describeError(control.error)}</Alert> : null}
      {control.loading && !control.data ? <LoadingNote label="Loading control snapshot" /> : null}
      {supported ? (
        <div className="relative h-[28rem] overflow-hidden rounded-card border border-line bg-surface">
          <div
            ref={container}
            role="region"
            aria-label="Reported control map"
            className="h-full w-full"
          />
          {hover ? <Tooltip hover={hover} /> : null}
          {failed ? (
            <p className="absolute inset-x-0 bottom-0 bg-ground/90 p-2 text-xs text-muted">
              The map renderer reported an error; the table below carries the same numbers.
            </p>
          ) : null}
        </div>
      ) : (
        <Alert tone="info">
          This browser cannot draw the map. The table below carries the same reported figures.
        </Alert>
      )}
      <ul aria-label="Map legend" className="flex flex-wrap gap-3 text-xs text-muted">
        {LEGEND.map((status) => (
          <li key={status} className="flex items-center gap-1.5">
            <span aria-hidden="true" className="size-3 rounded-sm" style={swatch(status)} />
            {STATUS_LABELS[status]}
          </li>
        ))}
        <li className="flex items-center gap-1.5">
          <span aria-hidden="true" className="size-3 rounded-full border border-line" />
          Settlements near the reported line
        </li>
      </ul>
      {summary ? (
        <>
          <p className="text-xs text-muted">{summary.method_note}</p>
          <details className="text-sm">
            <summary className="cursor-pointer text-muted">
              Oblast table, {summary.places_total.toLocaleString('en-GB')} populated places, release{' '}
              {summary.release_stamp.slice(0, 8)}, retrieved {formatUtc(summary.retrieved_at)}
            </summary>
            <div className="mt-2">
              <ControlTable summary={summary} />
            </div>
          </details>
        </>
      ) : null}
    </section>
  );
}
