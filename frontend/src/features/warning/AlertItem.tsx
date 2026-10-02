import { useId, useState } from 'react';

import { Button } from '@/components/ui/Button';
import type { Alert, AlertAcknowledgementRequest } from '@/lib/api/warning';
import { formatAgo } from '@/lib/format';
import { useNow } from '@/lib/hooks/useNow';

import { AlertDestination } from './AlertDestination';
import { AlertExplanation } from './AlertExplanation';

export function AlertItem({
  alert,
  onAcknowledge,
  workspace,
  canAcknowledge,
  confirms = false,
}: {
  alert: Alert;
  onAcknowledge: (feedback: AlertAcknowledgementRequest) => void;
  workspace: string;
  canAcknowledge: boolean;
  confirms?: boolean;
}) {
  const now = useNow();
  const dispositionId = useId();
  const noteId = useId();
  const [disposition, setDisposition] = useState('');
  const [note, setNote] = useState('');
  return (
    <li className="flex flex-col gap-2 rounded-card border border-line bg-surface p-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <span className="font-medium">
          {alert.title}
          <span className="ml-2 text-xs text-muted">{workspace}</span>
        </span>
        <span className="font-mono text-xs text-muted">{formatAgo(alert.fired_at, now)}</span>
      </div>
      {alert.summary !== '' && <p className="text-xs text-muted">{alert.summary}</p>}
      {alert.baseline_mean !== null && alert.baseline_mean !== undefined && (
        <p className="text-xs">
          Current count {alert.count}; sampled hourly mean {alert.baseline_mean.toFixed(2)}; ratio{' '}
          {alert.baseline_ratio?.toFixed(2)}.
        </p>
      )}
      {alert.countries.length > 0 && (
        <span className="text-xs text-muted">{alert.countries.join(', ')}</span>
      )}
      <AlertDestination
        monitorId={alert.annotation_monitor_id}
        transitionId={alert.annotation_transition_id}
        reportId={alert.report_id}
      />
      {alert.acknowledged_at === null ? (
        <div className="flex flex-wrap items-end gap-2 text-xs">
          <label htmlFor={dispositionId}>
            Disposition (optional)
            <select
              id={dispositionId}
              disabled={!canAcknowledge}
              value={disposition}
              onChange={(event) => setDisposition(event.target.value)}
            >
              <option value="">No disposition</option>
              <option value="useful">Useful</option>
              <option value="noise">Noise</option>
              <option value="duplicate">Duplicate</option>
            </select>
          </label>
          <label htmlFor={noteId}>
            Note (optional)
            <input
              id={noteId}
              disabled={!canAcknowledge}
              maxLength={200}
              value={note}
              onChange={(event) => setNote(event.target.value)}
            />
          </label>
          <Button
            variant="secondary"
            disabled={!canAcknowledge}
            aria-haspopup={confirms ? 'dialog' : undefined}
            onClick={() =>
              onAcknowledge({
                disposition:
                  disposition === 'useful' || disposition === 'noise' || disposition === 'duplicate'
                    ? disposition
                    : null,
                note: note || null,
              })
            }
          >
            Acknowledge
          </Button>
        </div>
      ) : (
        <p className="text-xs text-muted">
          <span>acknowledged</span>
          {alert.disposition ? ` · ${alert.disposition}` : ''}
          {alert.disposition_note ? ` · ${alert.disposition_note}` : ''}
          {
            ' · Shared first acknowledgement is retained; further acknowledgements do not replace it.'
          }
        </p>
      )}
      <AlertExplanation alertId={alert.id} />
    </li>
  );
}
