import { useState } from 'react';
import { useAccountRequest } from '@/components/account/useAccountRequest';
import { Button } from '@/components/ui/Button';
import { resetSource } from '@/lib/api/events';
import type { Source, SourceHealth } from '@/lib/api/eventSchemas';
import { activateSource, testSource } from '@/lib/api/sourceControls';
import { describeError } from '@/lib/api/errors';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';

export function SourceActions({
  source,
  onReset,
  onActivation,
}: {
  source: Source;
  onReset: (health: SourceHealth) => void;
  onActivation: (id: string, enabled: boolean) => void;
}) {
  const [confirm, setConfirm] = useState(false);
  const [notice, setNotice] = useState('');
  const begin = useAccountRequest();
  const enabled = source.enabled !== false;
  const action = useAsyncAction(async (operation: 'activation' | 'test' | 'reset') => {
    const signal = begin();
    setNotice('');
    if (operation === 'activation') {
      await activateSource(source.id, !enabled, signal);
      if (signal.aborted) return;
      onActivation(source.id, !enabled);
      setConfirm(false);
      setNotice(
        enabled
          ? 'Source disabled for future collection. Existing evidence remains available.'
          : 'Source enabled for collection.',
      );
    } else if (operation === 'reset') {
      const health = await resetSource(source.id, signal);
      if (!signal.aborted) onReset(health);
    } else {
      const result = await testSource(source.id, signal);
      if (!signal.aborted)
        setNotice(
          `${result.ok ? 'Test completed' : 'Test failed'}: ${result.message}${result.ok ? ` ${result.fetched}${result.capped ? '+' : ''} records received.` : ''}`,
        );
    }
  });
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        <Button
          variant="secondary"
          disabled={action.busy || source.environment_disabled === true}
          onClick={() => {
            setConfirm(true);
            action.clearError();
          }}
          aria-label={`${enabled ? 'Disable' : 'Enable'} ${source.name}`}
        >
          {enabled ? 'Disable' : 'Enable'}
        </Button>
        {source.test_available !== false && (
          <>
            <Button
              variant="secondary"
              disabled={action.busy}
              onClick={() => void action.run('test')}
              aria-label={`Test ${source.name}`}
            >
              Test connection
            </Button>
            <Button
              variant="secondary"
              disabled={action.busy}
              onClick={() => void action.run('reset')}
              aria-label={`Reset ${source.name}`}
            >
              Reset
            </Button>
          </>
        )}
      </div>
      {source.test_available === false && (
        <p className="text-xs text-muted">
          On-demand source. Test through a scoped research query.
        </p>
      )}
      {source.environment_disabled === true && (
        <p className="text-xs text-muted">Disabled in operator configuration.</p>
      )}
      {confirm && (
        <div className="space-y-2 text-xs">
          <p>
            {enabled
              ? 'Disable future collection from this source? Existing live records and saved reports are retained.'
              : 'Enable this source for collection?'}
          </p>
          <Button
            variant="secondary"
            busy={action.busy}
            onClick={() => void action.run('activation')}
          >
            Confirm {enabled ? 'disable' : 'enable'}
          </Button>
          <Button variant="ghost" disabled={action.busy} onClick={() => setConfirm(false)}>
            Cancel
          </Button>
        </div>
      )}
      {action.busy && (
        <p role="status" className="text-xs text-muted">
          Working... Connection tests allow up to 20 seconds.
        </p>
      )}
      {notice && (
        <p role="status" className="text-xs text-muted">
          {notice}
        </p>
      )}
      {action.error && (
        <p role="alert" className="text-xs text-critical">
          {describeError(action.error)}
        </p>
      )}
    </div>
  );
}
