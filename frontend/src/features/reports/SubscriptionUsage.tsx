import { useCallback, useState } from 'react';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField } from '@/components/ui/Field';
import { describeError } from '@/lib/api/errors';
import {
  fetchOwnerMonthlyUsage,
  fetchSubscriptionMonthlyUsage,
  type MonthlyUsage,
} from '@/lib/api/subscriptionUsage';
import { formatUtc } from '@/lib/format';
import { useScopedResource } from '@/lib/hooks/useScopedResource';

interface SubscriptionChoice {
  id: string;
  name: string;
}

function UsageLine({ label, value }: { label: string; value: MonthlyUsage }) {
  const count = (number: number) => number.toLocaleString('en-GB');
  const reached =
    value.used.requests >= value.limit.requests ||
    value.used.output_tokens >= value.limit.output_tokens;
  return (
    <div className="rounded-lg border border-line/70 px-3 py-2 text-xs">
      <p className="font-semibold">{label}</p>
      <p className="mt-1 text-muted">
        {count(value.used.requests)} of {count(value.limit.requests)} model requests ·{' '}
        {count(value.used.output_tokens)} of {count(value.limit.output_tokens)} output tokens
        counted
      </p>
      {reached && <p className="mt-1 text-amber">This month's allowance has been reached.</p>}
    </div>
  );
}

function SelectedSubscriptionUsage({ id, name }: SubscriptionChoice) {
  const loader = useCallback(() => fetchSubscriptionMonthlyUsage(id), [id]);
  const usage = useScopedResource(loader);
  return (
    <div>
      {usage.loading && <LoadingNote label={`Loading usage for ${name}`} />}
      {usage.error && <Alert tone="warning">{describeError(usage.error)}</Alert>}
      {usage.data && <UsageLine label={`Usage for ${name}`} value={usage.data} />}
      <Button variant="secondary" onClick={() => void usage.reload()}>
        Refresh subscription usage
      </Button>
    </div>
  );
}

export function SubscriptionUsage({
  subscriptions,
}: {
  subscriptions: readonly SubscriptionChoice[];
}) {
  const owner = useScopedResource(fetchOwnerMonthlyUsage);
  const [selected, setSelected] = useState<string | null>(null);
  const choice = subscriptions.find((item) => item.id === selected) ?? subscriptions[0];
  return (
    <section
      aria-label="Monthly AI provider usage"
      className="rounded-xl border border-line/70 bg-surface/40 p-4"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold">Monthly AI provider budget</h3>
          <p className="mt-1 text-xs text-muted">
            Separate from your research run allowance. Resets each UTC calendar month. Unknown
            provider outcomes retain their full output reservation.
          </p>
        </div>
        <Button variant="secondary" onClick={() => void owner.reload()}>
          Refresh owner usage
        </Button>
      </div>
      <div className="mt-3 space-y-2">
        {owner.loading && <LoadingNote label="Loading monthly report usage" />}
        {owner.error && <Alert tone="warning">{describeError(owner.error)}</Alert>}
        {owner.data && (
          <>
            <UsageLine label="All your report work" value={owner.data} />
            <p className="text-xs text-muted">
              Resets {formatUtc(owner.data.month_end)}. These limits count model calls and tokens,
              not complete research runs or currency.
            </p>
          </>
        )}
        {choice && (
          <div className="space-y-2">
            <SelectField
              label="Subscription usage"
              value={choice.id}
              onChange={(event) => setSelected(event.target.value)}
              options={subscriptions.map((item) => ({
                value: item.id,
                label: `Usage for ${item.name}`,
              }))}
            />
            <SelectedSubscriptionUsage key={choice.id} id={choice.id} name={choice.name} />
          </div>
        )}
      </div>
    </section>
  );
}
