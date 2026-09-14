import { Alert, LoadingNote } from '@/components/ui/Alert';
import { BasisBadge } from '@/components/ui/BasisBadge';
import { Button } from '@/components/ui/Button';
import { Table, Td, Th } from '@/components/ui/Table';
import { describeError } from '@/lib/api/errors';
import { STATUS_LABELS, type ControlStatus, type ControlSummary } from '@/lib/api/ukraine';
import {
  FRONTLINE_KIND_LABELS,
  type UkraineFrontline,
  type UkraineSpotted,
} from '@/lib/api/ukraineMap';
import { formatUtc } from '@/lib/format';

import { STATUS_RGB } from './controlLayers';
import { FRONTLINE_RGB, SPOTTED_RGB } from './providerLayers';
import { useUkraineMap, type Hover, type MapLoaders } from './useUkraineMap';

const LEGEND: readonly ControlStatus[] = ['ru', 'contested', 'ua'];

function rgb([r, g, b]: readonly [number, number, number]) {
  return { backgroundColor: `rgb(${r} ${g} ${b})` };
}

function Tooltip({ hover }: { hover: Hover }) {
  if (hover.kind === 'loss') {
    const { loss } = hover;
    return (
      <div
        role="tooltip"
        className="pointer-events-none absolute z-20 max-w-64 rounded border border-line bg-ground/95 p-2 text-xs shadow-lg"
        style={{ left: hover.x + 12, top: hover.y + 12 }}
      >
        <p className="font-medium text-text">{loss.model}</p>
        <p className="text-muted">
          {loss.equipment_type}, {loss.status.toLowerCase()} {loss.on}
        </p>
        <p className="text-muted">{loss.place} · photographed loss, WarSpotting</p>
      </div>
    );
  }
  const { settlement } = hover;
  const [wiki, boosted, deepstate] = settlement.votes;
  return (
    <div
      role="tooltip"
      className="pointer-events-none absolute z-20 max-w-64 rounded border border-line bg-ground/95 p-2 text-xs shadow-lg"
      style={{ left: hover.x + 12, top: hover.y + 12 }}
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

function describeFrontline(frontline: UkraineFrontline): string {
  if (frontline.status === 'disabled') return `off. ${frontline.reason}`;
  const name = frontline.attribution ?? frontline.provider ?? 'provider';
  const assessed = frontline.assessed_at ? `, assessed ${frontline.assessed_at}` : '';
  return `${name} (${frontline.status}${assessed}). ${frontline.terms ?? ''}`;
}

/** Which provider layers are drawn, or why none is; never a silent substitution. */
function ProviderNote({
  frontline,
  spotted,
}: {
  frontline: UkraineFrontline | null;
  spotted: UkraineSpotted | null;
}) {
  return (
    <ul aria-label="Provider layers" className="flex flex-col gap-1 text-xs text-muted">
      <li>Frontline provider: {frontline ? describeFrontline(frontline) : 'loading'}</li>
      <li>
        Spotted losses:{' '}
        {spotted
          ? spotted.status === 'disabled'
            ? `off. ${spotted.reason}`
            : `${spotted.attribution} (${spotted.status}, ${spotted.losses.length} markers)`
          : 'loading'}
      </li>
    </ul>
  );
}

export function UkraineMap({ loaders }: { loaders?: MapLoaders }) {
  const { container, supported, failed, hover, control, frontline, spotted, refit } =
    useUkraineMap(loaders);
  const summary = control.data?.summary ?? null;
  const kinds = [...new Set((frontline.data?.features ?? []).map((feature) => feature.kind))];
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
            <span
              aria-hidden="true"
              className="size-3 rounded-sm"
              style={rgb(STATUS_RGB[status])}
            />
            {STATUS_LABELS[status]}
          </li>
        ))}
        <li className="flex items-center gap-1.5">
          <span aria-hidden="true" className="size-3 rounded-full border border-line" />
          Settlements near the reported line
        </li>
        {kinds.map((kind) => (
          <li key={kind} className="flex items-center gap-1.5">
            <span
              aria-hidden="true"
              className="size-3 rounded-sm"
              style={rgb(FRONTLINE_RGB[kind])}
            />
            {FRONTLINE_KIND_LABELS[kind]}
          </li>
        ))}
        {spotted.data && spotted.data.losses.length > 0 ? (
          <li className="flex items-center gap-1.5">
            <span aria-hidden="true" className="size-3 rounded-full" style={rgb(SPOTTED_RGB)} />
            Photographed losses (WarSpotting)
          </li>
        ) : null}
      </ul>
      <ProviderNote frontline={frontline.data} spotted={spotted.data} />
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
