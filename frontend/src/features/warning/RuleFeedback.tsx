import { useCallback, useState } from 'react';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { fetchAlertFeedback } from '@/lib/api/warning';
import { describeError } from '@/lib/api/errors';
import { useScopedResource } from '@/lib/hooks/useScopedResource';

function Counts({ ruleId }: { ruleId: string }) {
  const load = useCallback(() => fetchAlertFeedback(ruleId), [ruleId]);
  const feedback = useScopedResource(load);
  if (feedback.error) return <Alert tone="error">{describeError(feedback.error)}</Alert>;
  if (!feedback.data) return <LoadingNote label="Loading feedback" />;
  const value = feedback.data;
  return (
    <div>
      <p>
        Useful {value.useful} · Noise {value.noise} · Duplicate {value.duplicate}
      </p>
      <p>30-day window: {value.time_basis}. One disposition per alert.</p>
      {value.useful + value.noise + value.duplicate === 0 && <p>No dispositions in this window.</p>}
    </div>
  );
}

export function RuleFeedback({ ruleId }: { ruleId: string }) {
  const [open, setOpen] = useState(false);
  return (
    <details onToggle={(event) => setOpen(event.currentTarget.open)}>
      <summary>Recent feedback</summary>
      {open && <Counts ruleId={ruleId} />}
    </details>
  );
}
