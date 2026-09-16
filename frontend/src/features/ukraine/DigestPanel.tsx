import { useMemo, useState } from 'react';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { describeError } from '@/lib/api/errors';
import {
  refreshUkraineDigest,
  type UkraineDigestEntry,
  type UkraineDigestView,
} from '@/lib/api/ukraineDigest';
import { formatUtc } from '@/lib/format';
import { useAuthStore, selectIsAdmin } from '@/stores/auth';

import { DigestStrandView, formatDay } from './DigestStrandView';
import { useUkraineDigest } from './useUkraineDigest';

const WRITTEN_BY =
  'Written by the model from the sources listed. Nothing in it is verified by this application.';

function Provenance({ entry, intervalDays }: { entry: UkraineDigestEntry; intervalDays: number }) {
  const tokens =
    entry.prompt_tokens === null && entry.completion_tokens === null
      ? 'not reported'
      : `${entry.prompt_tokens ?? 0} in, ${entry.completion_tokens ?? 0} out`;
  const rows: readonly (readonly [string, string])[] = [
    ['Model', entry.model],
    ['Written', formatUtc(entry.generated_at)],
    ['Evidence window', `${formatDay(entry.period_start)} to ${formatDay(entry.period_end)}`],
    ['Evidence items', `${entry.evidence_items} trimmed items from the collected sources`],
    ['Tokens', tokens],
    ['Cadence', `One digest every ${intervalDays} days, unless an administrator asks sooner`],
    ['Sources', entry.source_ids.join(', ') || 'none recorded'],
  ];
  return (
    <details className="rounded-md border border-line bg-surface p-3">
      <summary className="cursor-pointer text-xs font-semibold text-text">
        How this digest was made
      </summary>
      <dl className="mt-3 grid grid-cols-1 gap-x-4 gap-y-2 text-xs sm:grid-cols-[10rem_1fr]">
        {rows.map(([label, value]) => (
          <div key={label} className="contents">
            <dt className="text-muted">{label}</dt>
            <dd className="break-words font-mono text-[11px] text-text">{value}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-3 text-xs text-muted">
        The model was shown only trimmed, dated items from these sources. Its answer was checked
        mechanically before it was stored: every evidence id, number and date had to come from that
        evidence.
      </p>
    </details>
  );
}

function Notes({ title, items, label }: { title: string; items: string[]; label: string }) {
  if (items.length === 0) return null;
  return (
    <section className="flex flex-col gap-2">
      <h3 className="text-sm font-semibold text-text">{title}</h3>
      <ul aria-label={label} className="flex list-disc flex-col gap-1 pl-5 text-sm text-muted">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

function Digest({ entry, intervalDays }: { entry: UkraineDigestEntry; intervalDays: number }) {
  const citations = useMemo(
    () => new Map(entry.citations.map((item) => [item.id, item])),
    [entry.citations],
  );
  return (
    <div className="flex flex-col gap-5">
      <DigestStrandView
        id="ukraine-digest-battlefield"
        title="Battlefield"
        strand={entry.battlefield}
        citations={citations}
      />
      <DigestStrandView
        id="ukraine-digest-political"
        title="Political"
        strand={entry.political}
        citations={citations}
      />
      <Notes title="What to watch" items={entry.watch} label="What to watch" />
      <Notes title="Caveats" items={entry.caveats} label="Caveats" />
      <Provenance entry={entry} intervalDays={intervalDays} />
    </div>
  );
}

function EmptyState({ view }: { view: UkraineDigestView }) {
  if (view.generating)
    return (
      <LoadingNote label="A digest is being written from the last fortnight of sources. This takes a minute." />
    );
  if (view.status === 'validation_failed')
    return (
      <Alert tone="warning" title="The last attempt was not stored">
        {view.reason ??
          'The model answer failed the checks run before storing a digest, so nothing was saved.'}
      </Alert>
    );
  if (view.status === 'unavailable')
    return (
      <Alert tone="warning" title="No digest is available">
        {view.reason ?? 'The digest could not be written.'}
      </Alert>
    );
  return (
    <p className="text-sm text-muted">
      No digest has been written yet. One is written every {view.interval_days} days from the
      sources on this page.
    </p>
  );
}

/** Loader and refresh are injectable so the DEV preview can frame the panel with fixture data. */
export function DigestPanel({
  load,
  refresh = refreshUkraineDigest,
}: {
  load?: (() => Promise<UkraineDigestView>) | undefined;
  refresh?: () => Promise<UkraineDigestView>;
}) {
  const { data, error, loading, setData } = useUkraineDigest(load);
  const isAdmin = useAuthStore(selectIsAdmin);
  const [selected, setSelected] = useState<string>('');
  const [busy, setBusy] = useState(false);
  const [refreshError, setRefreshError] = useState<string | null>(null);

  const entries = data?.latest ? [data.latest, ...data.previous] : [];
  const entry = entries.find((item) => item.generated_at === selected) ?? entries[0];

  const onRefresh = async () => {
    setBusy(true);
    setRefreshError(null);
    try {
      setData(await refresh());
      setSelected('');
    } catch (caught) {
      setRefreshError(describeError(caught));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section
      id="digest"
      aria-labelledby="ukraine-digest-heading"
      className="flex flex-col gap-4 rounded-lg border border-line bg-surface p-4"
    >
      <header className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-baseline gap-3">
            <h2 id="ukraine-digest-heading" className="text-base font-semibold">
              AI digest
            </h2>
            {entry ? (
              <span className="rounded bg-surface-2 px-2 py-0.5 font-mono text-xs text-text">
                Fortnight to {formatDay(entry.period_end)}
              </span>
            ) : null}
          </div>
          {isAdmin ? (
            <Button variant="secondary" busy={busy} onClick={() => void onRefresh()}>
              {busy ? 'Asking for a digest' : 'Write a new digest'}
            </Button>
          ) : null}
        </div>
        <p className="max-w-3xl text-sm text-muted">{WRITTEN_BY}</p>
        {entries.length > 1 ? (
          <label className="flex min-w-0 flex-wrap items-center gap-2 text-xs text-muted">
            <span>Earlier digests</span>
            <select
              className="min-h-9 min-w-0 max-w-full rounded border border-line bg-surface-2 px-2 py-1 text-xs text-text"
              value={entry ? entry.generated_at : ''}
              onChange={(event) => setSelected(event.target.value)}
            >
              {entries.map((item, index) => (
                <option key={item.generated_at} value={item.generated_at}>
                  {`Fortnight to ${formatDay(item.period_end)}${index === 0 ? ' (latest)' : ''}`}
                </option>
              ))}
            </select>
          </label>
        ) : null}
      </header>
      {error ? <Alert tone="error">{describeError(error)}</Alert> : null}
      {refreshError ? <Alert tone="error">{refreshError}</Alert> : null}
      {loading && !data ? <LoadingNote label="Loading the digest" /> : null}
      {data && entry && data.stale ? (
        <Alert tone="warning">
          This digest covers a fortnight that has already ended. A new one is written when the page
          is next read.
        </Alert>
      ) : null}
      {data && entry && data.reason ? <Alert tone="warning">{data.reason}</Alert> : null}
      {data && !entry ? <EmptyState view={data} /> : null}
      {entry ? <Digest entry={entry} intervalDays={data?.interval_days ?? 14} /> : null}
    </section>
  );
}
