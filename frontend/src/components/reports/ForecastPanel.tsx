import { useCallback, useState } from 'react';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import type { ClaimRevision } from '@/lib/api/claims';
import { createForecast, exportForecasts, listForecasts } from '@/lib/api/forecasts';
import { describeError } from '@/lib/api/errors';
import { saveTextFile } from '@/lib/download';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { ForecastCard } from './ForecastCard';
import { ForecastClaimPicker } from './ForecastClaimPicker';
import { ForecastForm } from './ForecastForm';

interface Props {
  reportId: string;
  version: number;
  canEdit: boolean;
}

function ForecastList(props: Props) {
  const [offset, setOffset] = useState(0);
  const request = useScopedRequest();
  const load = useCallback(
    () => listForecasts(props.reportId, props.version, offset, request()),
    [props.reportId, props.version, offset, request],
  );
  const resource = useScopedResource(load);
  return (
    <div className="mt-4 space-y-4">
      <p className="text-sm text-muted">
        Forecasts retain an exact reviewed claim revision and its citations. Later reviews and
        selected history exports leave the report's body, grades and confidence unchanged.
      </p>
      {resource.loading && <LoadingNote label="Loading forecasts" />}
      {resource.error && (
        <Alert tone="error">Forecasts unavailable: {describeError(resource.error)}</Alert>
      )}
      {resource.data && (
        <ForecastContent
          key={`${resource.key}:${offset}`}
          {...props}
          items={resource.data.items}
          reload={() => {
            void resource.reload();
          }}
        />
      )}
      {resource.data && resource.data.total > 20 && (
        <div className="flex gap-3">
          <Button
            variant="secondary"
            disabled={offset === 0}
            onClick={() => setOffset(offset - 20)}
          >
            Previous ledgers
          </Button>
          <Button
            variant="secondary"
            disabled={offset + 20 >= resource.data.total}
            onClick={() => setOffset(offset + 20)}
          >
            Next ledgers
          </Button>
        </div>
      )}
    </div>
  );
}

function ForecastContent({
  reportId,
  version,
  canEdit,
  items,
  reload,
}: Props & { items: Awaited<ReturnType<typeof listForecasts>>['items']; reload: () => void }) {
  const [creating, setCreating] = useState(false);
  const [claim, setClaim] = useState<ClaimRevision | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const request = useScopedRequest();
  const download = useAsyncAction(async () => {
    const signal = request();
    const histories = await exportForecasts(reportId, version, selected, signal);
    signal.throwIfAborted();
    saveTextFile(
      `forecast-history-version-${version}.json`,
      JSON.stringify(
        { report_id: reportId, report_version: version, forecasts: histories },
        null,
        2,
      ),
      'application/json',
    );
  });
  return (
    <>
      {canEdit && (
        <Button
          variant="secondary"
          onClick={() => {
            setCreating(!creating);
            setClaim(null);
          }}
        >
          Create forecast from a reviewed claim
        </Button>
      )}
      {creating && (
        <ForecastClaimPicker reportId={reportId} version={version} onChoose={setClaim} />
      )}
      {creating && claim && (
        <>
          <p>{claim.statement}</p>
          <ul>
            {claim.citations.map((row) => (
              <li key={`${row.label}:${row.excerpt.sha256}`}>
                {row.relation}: {row.label}, “{row.excerpt.text}”
              </li>
            ))}
          </ul>
          <ForecastForm
            key={claim.id}
            anchor={{
              claim_id: claim.claim_id,
              claim_revision_id: claim.id,
              supporting: claim.citations
                .filter((row) => row.relation === 'supporting')
                .map((row) => ({ evidence_label: row.label, excerpt_sha256: row.excerpt.sha256 })),
              contrary: claim.citations
                .filter((row) => row.relation === 'opposing')
                .map((row) => ({ evidence_label: row.label, excerpt_sha256: row.excerpt.sha256 })),
            }}
            onCancel={() => {
              setCreating(false);
              setClaim(null);
            }}
            onSave={async (body) => {
              const signal = request();
              await createForecast(reportId, version, body, signal);
              signal.throwIfAborted();
              setCreating(false);
              setClaim(null);
              reload();
            }}
          />
        </>
      )}
      {items.length === 0 && <p>No forecasts on this ledger page.</p>}
      {items.map((value) => (
        <article key={value.anchor.id} className="rounded border border-line p-4">
          <ForecastCard value={value} version={version} canEdit={canEdit} onSaved={reload} />
          <label className="mt-3 flex gap-2 text-sm">
            <input
              type="checkbox"
              checked={selected.includes(value.anchor.id)}
              onChange={(e) =>
                setSelected(
                  e.target.checked
                    ? [...selected, value.anchor.id]
                    : selected.filter((id) => id !== value.anchor.id),
                )
              }
            />
            Include this forecast history in a separate JSON export
          </label>
        </article>
      ))}
      {items.length > 0 && (
        <Button
          variant="secondary"
          disabled={selected.length === 0}
          busy={download.busy}
          onClick={() => void download.run()}
        >
          Export selected forecast histories
        </Button>
      )}
      {download.error && <Alert tone="error">{describeError(download.error)}</Alert>}
    </>
  );
}

export function ForecastPanel(props: Props) {
  const [open, setOpen] = useState(false);
  return (
    <section className="my-5 rounded border border-line p-4" aria-label="Forecasts">
      <Button variant="secondary" aria-expanded={open} onClick={() => setOpen(!open)}>
        Forecasts and review history
      </Button>
      {open && <ForecastList key={`${props.reportId}:${props.version}`} {...props} />}
    </section>
  );
}
