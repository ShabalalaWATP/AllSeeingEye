import { useCallback } from 'react';
import { fetchIndicatorBaseline } from '@/lib/api/warning';
import { describeError } from '@/lib/api/errors';
import { useScopedResource } from '@/lib/hooks/useScopedResource';

export function RuleBaseline({ ruleId }: { ruleId: string }) {
  const load = useCallback(() => fetchIndicatorBaseline(ruleId), [ruleId]);
  const baseline = useScopedResource(load);
  if (baseline.error) return <p role="alert">{describeError(baseline.error)}</p>;
  if (!baseline.data) return <p role="status">Loading baseline status…</p>;
  return (
    <p>
      {baseline.data.reason} {baseline.data.sample_hours} sampled hours.
    </p>
  );
}
