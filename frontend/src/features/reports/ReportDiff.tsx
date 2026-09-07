import { useCallback, useState, useSyncExternalStore } from 'react';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField } from '@/components/ui/Field';
import { AnnotationComparisonWorkspace } from './AnnotationComparisonWorkspace';
import { describeError } from '@/lib/api/errors';
import { fetchReportComparison } from '@/lib/api/reportDocuments';
import type { ReportChange } from '@/lib/api/reportDocuments';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useAuthStore } from '@/stores/auth';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';

function Change({ change }: { change: ReportChange }) {
  return (
    <li className="border-b border-line py-3">
      <h4 className="break-words text-sm font-medium">
        {change.kind.toUpperCase()} · {change.section} · {change.path}
      </h4>
      <dl className="mt-2 grid gap-3 text-sm md:grid-cols-2">
        {change.before === null ? null : (
          <div>
            <dt className="text-muted">Before</dt>
            <dd className="mt-1 whitespace-pre-wrap break-words">{change.before}</dd>
          </div>
        )}
        {change.after === null ? null : (
          <div>
            <dt className="text-muted">After</dt>
            <dd className="mt-1 whitespace-pre-wrap break-words">{change.after}</dd>
          </div>
        )}
      </dl>
    </li>
  );
}

function ComparisonResult({ id, from, to }: { id: string; from: number; to: number }) {
  const request = useScopedRequest();
  const loader = useCallback(
    () => fetchReportComparison(id, from, to, request()),
    [id, from, to, request],
  );
  const { data, error, loading, reload } = useScopedResource(loader);
  return (
    <section
      aria-label={`Version ${String(from)} to ${String(to)} comparison`}
      aria-busy={loading}
      className="mt-4"
    >
      <h3 className="font-medium">
        Version {from} to version {to}
      </h3>
      {loading ? <LoadingNote label="Comparing report versions" /> : null}
      {error === null ? null : (
        <div>
          <Alert tone="error">{describeError(error)}</Alert>
          <Button variant="secondary" onClick={() => void reload()}>
            Retry comparison
          </Button>
        </div>
      )}
      {data === null || loading || error !== null ? null : data.changes.length === 0 ? (
        <p role="status" className="mt-2 text-sm text-muted">
          No changes to content, validation or frozen evidence.
        </p>
      ) : (
        <>
          <p role="status" className="mt-2 text-sm text-muted">
            {data.changes.length} changed fields. Evidence is matched by event identity, including
            grades and provenance.
          </p>
          <ol>
            {data.changes.map((change) => (
              <Change key={`${change.section}:${change.path}`} change={change} />
            ))}
          </ol>
        </>
      )}
    </section>
  );
}

function ReportDiffBody({ id, current, latest }: { id: string; current: number; latest: number }) {
  const [advanced, setAdvanced] = useState(false);
  const [from, setFrom] = useState(Math.max(1, current - 1));
  const [to, setTo] = useState(current);
  const [pair, setPair] = useState<{ from: number; to: number } | null>(null);
  const options = Array.from({ length: latest }, (_, index) => ({
    value: String(index + 1),
    label: `Version ${String(index + 1)}`,
  }));
  return (
    <details className="rounded border border-line p-4">
      <summary className="cursor-pointer font-medium">Compare versions</summary>
      {latest < 2 ? (
        <p className="mt-3 text-sm text-muted">
          Regenerate this report to create a second version for comparison.
        </p>
      ) : (
        <>
          <form
            className="mt-4 flex flex-wrap items-end gap-3"
            onSubmit={(event) => {
              event.preventDefault();
              setPair({ from, to });
            }}
          >
            <SelectField
              label="From version"
              options={options}
              value={String(from)}
              onChange={(event) => {
                setFrom(Number(event.target.value));
                setPair(null);
              }}
            />
            <SelectField
              label="To version"
              options={options}
              value={String(to)}
              onChange={(event) => {
                setTo(Number(event.target.value));
                setPair(null);
              }}
            />
            <Button type="submit" variant="secondary">
              Compare selected versions
            </Button>
          </form>
          {pair === null ? null : (
            <ComparisonResult
              key={`${id}:${String(pair.from)}:${String(pair.to)}`}
              id={id}
              from={pair.from}
              to={pair.to}
            />
          )}
        </>
      )}
      <div className="mt-4 border-t border-line pt-4">
        <Button variant="secondary" aria-expanded={advanced} onClick={() => setAdvanced(!advanced)}>
          Compare annotations and confidence
        </Button>
        {advanced && <AnnotationComparisonWorkspace id={id} current={current} />}
      </div>
    </details>
  );
}

export function ReportDiff(props: { id: string; current: number; latest: number }) {
  const actor = useAuthStore(
    (state) => `${state.status}:${state.user?.id}:${state.user?.role}:${state.user?.is_active}`,
  );
  const access = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  return <ReportDiffBody key={`${actor}:${access}:${props.id}:${props.current}`} {...props} />;
}
