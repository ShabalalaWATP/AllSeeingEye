import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField } from '@/components/ui/Field';
import { fetchPlans } from '@/lib/api/direction';
import { describeError } from '@/lib/api/errors';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { usePlanMapFilterStore } from '@/stores/planMapFilter';

const number = new Intl.NumberFormat('en-GB');

/** Choose one readable collection plan and see how its bounded match sample was drawn. */
export function PlanFilterPanel({ shown }: { shown: number }) {
  const plans = useScopedResource(fetchPlans);
  const { planId, status, result, fetchedAt, message, select, refresh } = usePlanMapFilterStore();
  const options = plans.data ?? [];
  return (
    <div className="flex flex-col gap-3 text-sm">
      <p className="text-xs text-muted">
        Shows only events matching a plan&apos;s requirements, within the time, nation, layer and
        other filters already applied. Matches are worked out for you alone and never shared.
      </p>
      {plans.loading && plans.data === null && <LoadingNote label="Loading your plans" />}
      {plans.error !== null && (
        <Alert tone="error">
          {describeError(plans.error)}{' '}
          <Button variant="secondary" onClick={() => void plans.reload()}>
            Retry plans
          </Button>
        </Alert>
      )}
      {plans.data !== null && (
        <SelectField
          label="Collection plan"
          value={planId ?? ''}
          onChange={(event) => select(event.target.value || null)}
          options={[
            { value: '', label: options.length === 0 ? 'No readable plans' : 'No plan filter' },
            ...options.map((plan) => ({
              value: plan.id,
              label: plan.enabled ? plan.name : `${plan.name} (disabled)`,
            })),
          ]}
        />
      )}
      <div role="status" aria-live="polite" className="flex flex-col gap-2">
        {status === 'lost' && <Alert tone="warning">{message}</Alert>}
        {planId !== null && status === 'loading' && <LoadingNote label="Finding plan matches" />}
        {planId !== null && (status === 'unavailable' || status === 'failed') && (
          <Alert tone={status === 'failed' ? 'error' : 'warning'}>
            {status === 'failed'
              ? 'Plan matches could not be loaded. '
              : 'Plan matches are unavailable. '}
            {message}
            {result !== null && ' The map keeps the last matches until a refresh succeeds.'}
          </Alert>
        )}
        {planId !== null && result !== null && (
          <>
            <p>
              {result.matches.length === 0
                ? `No events from the last ${result.window_hours} hours match ${result.plan.name}.`
                : `${number.format(result.matches.length)} events match ${result.plan.name}; ${number.format(shown)} pass the other map filters.`}
            </p>
            <p className="text-xs text-muted">
              Sample: the last {result.window_hours} hours, {number.format(result.considered)}{' '}
              events considered, up to {number.format(result.pool_limit)} per query and{' '}
              {result.per_requirement_limit} per requirement.
              {fetchedAt !== null &&
                ` Matched at ${new Date(fetchedAt).toLocaleTimeString('en-GB')}; refreshed each minute while the map is open.`}
            </p>
            {result.truncated && (
              <Alert tone="warning">
                The sample reached its limit, so some matching events are not shown.
              </Alert>
            )}
          </>
        )}
      </div>
      {planId !== null && (
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" busy={status === 'loading'} onClick={refresh}>
            Refresh matches
          </Button>
          <Button variant="ghost" onClick={() => select(null)}>
            Clear plan filter
          </Button>
        </div>
      )}
    </div>
  );
}
