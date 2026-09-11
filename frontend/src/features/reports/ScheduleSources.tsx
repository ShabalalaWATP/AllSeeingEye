import { useCallback } from 'react';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { describeError } from '@/lib/api/errors';
import { previewResearchPlan } from '@/lib/api/researchPlan';
import type { ResearchPlanInput } from '@/lib/api/researchPlan';
import { useScopedResource } from '@/lib/hooks/useScopedResource';

/** Preview only: no source is queried and no model is charged to build this catalogue. */
export function ScheduleSources({
  scope,
  lookback,
  value,
  onChange,
}: {
  scope: Omit<ResearchPlanInput, 'since' | 'until'>;
  lookback: number;
  value: string[] | null;
  onChange: (sources: string[] | null) => void;
}) {
  const encoded = JSON.stringify(scope);
  const load = useCallback(() => {
    const until = new Date();
    return previewResearchPlan(
      {
        ...(JSON.parse(encoded) as typeof scope),
        since: new Date(until.getTime() - lookback * 86_400_000).toISOString(),
        until: until.toISOString(),
      },
      new AbortController().signal,
    );
  }, [encoded, lookback]);
  const sources = useScopedResource(load);
  const tasks = [
    ...new Map(sources.data?.tasks.map((task) => [task.source_id, task]) ?? []).values(),
  ];
  const supported = tasks.filter((task) => task.supported).map((task) => task.source_id);
  return (
    <div className="space-y-3 rounded-md border border-line bg-ground p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-medium">
          {value === null ? 'All supported sources' : `${value.length} selected sources`}
        </p>
        <Button variant="secondary" onClick={() => onChange(null)}>
          Use all supported
        </Button>
      </div>
      <p className="text-xs text-muted">
        Availability is checked again at each run. A longer lookback does not create an archive for
        live-only feeds.
      </p>
      {sources.loading && <LoadingNote label="Checking research sources" />}
      {sources.error && <Alert tone="error">{describeError(sources.error)}</Alert>}
      {sources.data && (
        <div className="max-h-64 space-y-1 overflow-y-auto">
          {tasks.map((task) => (
            <label
              key={task.source_id}
              className="flex gap-3 rounded p-2 text-sm hover:bg-surface has-disabled:opacity-60"
            >
              <input
                type="checkbox"
                className="mt-1 h-4 w-4 accent-ember"
                disabled={!task.supported}
                checked={value === null ? task.supported : value.includes(task.source_id)}
                onChange={(event) => {
                  const current = value ?? supported;
                  onChange(
                    event.target.checked
                      ? [...current, task.source_id]
                      : current.filter((id) => id !== task.source_id),
                  );
                }}
              />
              <span>
                {task.source_name}
                <span className="mt-1 block text-xs text-muted">
                  {task.temporal_scope}
                  {!task.supported ? ' Unavailable for this scope.' : ''}
                </span>
              </span>
            </label>
          ))}
          {tasks.length === 0 && (
            <p className="text-xs text-muted">No source capabilities returned for this scope.</p>
          )}
        </div>
      )}
    </div>
  );
}
