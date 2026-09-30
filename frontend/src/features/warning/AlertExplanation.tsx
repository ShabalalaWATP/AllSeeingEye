import { useCallback, useEffect, useRef, useState } from 'react';

import { EyeAnswer } from '@/components/assistant/EyeAnswer';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { askAssistant } from '@/lib/api/assistant';
import { describeError } from '@/lib/api/errors';
import { useScopedResource } from '@/lib/hooks/useScopedResource';

function Explanation({ alertId }: { alertId: string }) {
  const controller = useRef<AbortController | null>(null);
  const load = useCallback(() => {
    controller.current?.abort();
    controller.current = new AbortController();
    return askAssistant(
      {
        scope: 'alert',
        alert_id: alertId,
        question: 'Explain the available evidence for this alert and its gaps.',
      },
      controller.current.signal,
    );
  }, [alertId]);
  useEffect(() => () => controller.current?.abort(), []);
  const result = useScopedResource(load);
  return (
    <div>
      {result.loading && <LoadingNote label="Preparing alert explanation" />}
      {result.error && <Alert tone="error">{describeError(result.error)}</Alert>}
      {result.data && <EyeAnswer answer={result.data} />}
    </div>
  );
}

export function AlertExplanation({ alertId }: { alertId: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <Button variant="secondary" aria-expanded={open} onClick={() => setOpen(!open)}>
        {open ? 'Close explanation' : 'Explain with Ask Eye'}
      </Button>
      {open && <Explanation alertId={alertId} />}
    </div>
  );
}
