import { useCallback } from 'react';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { fetchPlan } from '@/lib/api/direction';
import type { CollectionPlan } from '@/lib/api/direction';
import { describeError } from '@/lib/api/errors';
import { useScopedResource } from '@/lib/hooks/useScopedResource';

/**
 * A stale save: show the newer saved plan beside the kept draft and let the editor choose.
 * Nothing is overwritten or discarded without an explicit choice.
 */
export function PlanConflict({
  planId,
  onUseLatest,
  onKeepMine,
}: {
  planId: string;
  onUseLatest: (latest: CollectionPlan) => void;
  onKeepMine: (latest: CollectionPlan) => void;
}) {
  const loader = useCallback(() => fetchPlan(planId), [planId]);
  const latest = useScopedResource(loader);
  const current = latest.data;
  return (
    <Alert tone="warning" title="This plan changed after you opened it">
      <div className="flex flex-col gap-3">
        <p>
          Someone saved a newer version, so your edits were not saved. Your draft is still in the
          form. Compare it with the latest version below, then choose how to continue.
        </p>
        {latest.loading && <LoadingNote label="Loading the latest version" />}
        {latest.error !== null && (
          <p>
            {describeError(latest.error)}{' '}
            <Button variant="secondary" onClick={() => void latest.reload()}>
              Retry loading the latest version
            </Button>
          </p>
        )}
        {current !== null && (
          <>
            <section aria-label="Latest saved version" className="text-sm">
              <p className="font-medium">
                {current.name} · saved {new Date(current.updated_at).toLocaleString()}
              </p>
              <ul className="mt-1 list-disc pl-5">
                {current.pirs.map((pir) => (
                  <li key={pir.code}>
                    <span className="font-mono text-xs">{pir.code}</span> {pir.text} (
                    {pir.sirs.length} specific)
                  </li>
                ))}
              </ul>
            </section>
            <div className="flex flex-wrap gap-2">
              <Button variant="secondary" onClick={() => onUseLatest(current)}>
                Load the latest version and discard my edits
              </Button>
              <Button onClick={() => onKeepMine(current)}>
                Keep my edits to save over the latest version
              </Button>
            </div>
          </>
        )}
      </div>
    </Alert>
  );
}
