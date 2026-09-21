import { useEffect, useState } from 'react';

import { AllowanceCard, ObservedTotals } from '@/components/aiUsage/AllowanceCards';
import { ResearchAllowanceSummary } from '@/components/research/ResearchAllowanceSummary';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { asApiError, describeError } from '@/lib/api/errors';
import { getMyAiUsage, type AiUsagePage } from '@/lib/api/aiUsage';

export function AiUsageSummary() {
  const [page, setPage] = useState<AiUsagePage | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setError(null);
    try {
      setPage(await getMyAiUsage());
    } catch (caught) {
      setError(describeError(asApiError(caught)));
    }
  }

  useEffect(() => {
    // This page owns the request lifecycle, so changing settings never causes
    // a background usage poll across the rest of the application.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, []);

  return (
    <section aria-label="AI usage" className="flex max-w-2xl flex-col gap-6">
      <header>
        <p className="font-mono text-xs uppercase tracking-widest text-cyan">Usage awareness</p>
        <h2 className="mt-2 text-xl font-semibold">AI usage and research allowance</h2>
        <p className="mt-2 text-sm leading-6 text-muted">
          Your research level sets the allowance for complete research runs. AI provider budgets
          separately limit the model calls and tokens used inside those runs. Team and site budgets
          also apply.
        </p>
      </header>
      <ResearchAllowanceSummary />
      <h3 className="font-semibold">AI provider usage</h3>
      {error ? (
        <Alert tone="error">
          {error}{' '}
          <Button variant="ghost" onClick={() => void load()}>
            Retry
          </Button>
        </Alert>
      ) : null}
      {page === null && error === null ? <LoadingNote label="Loading AI allowance" /> : null}
      {page ? (
        <ObservedTotals
          label="Your recorded provider usage"
          totals={page.observed}
          prices={page.prices}
        />
      ) : null}
      {page?.items.length === 0 ? (
        <p className="text-sm text-muted">
          No additional AI provider policy is configured. Your research level and existing app
          budgets still apply.
        </p>
      ) : null}
      {page && page.items.length > 0 ? (
        <div className="flex flex-col gap-4">
          {page.items.map((item) => (
            <AllowanceCard key={item.policy.id} item={item} />
          ))}
        </div>
      ) : null}
    </section>
  );
}
