import { useState, useSyncExternalStore } from 'react';
import { Button } from '@/components/ui/Button';
import { useAuthStore } from '@/stores/auth';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import { ResearchInput } from './ResearchInput';
import type { ResearchInputProps } from './ResearchInput';
import { SecFilingPicker } from './SecFilingPicker';
function Choice(props: ResearchInputProps) {
  const [method, setMethod] = useState<'upload' | 'sec'>('upload');
  return (
    <section aria-label="Document research input" className="space-y-3">
      <div className="flex flex-wrap gap-2">
        <Button
          variant={method === 'upload' ? 'primary' : 'secondary'}
          aria-pressed={method === 'upload'}
          disabled={props.disabled}
          onClick={() => {
            if (method === 'upload') return;
            props.onChange(null);
            props.onBusyChange?.(false);
            setMethod('upload');
          }}
        >
          Upload a document
        </Button>
        <Button
          variant={method === 'sec' ? 'primary' : 'secondary'}
          aria-pressed={method === 'sec'}
          disabled={props.disabled}
          onClick={() => {
            if (method === 'sec') return;
            props.onChange(null);
            props.onBusyChange?.(false);
            setMethod('sec');
          }}
        >
          Find an SEC filing
        </Button>
      </div>
      {method === 'upload' ? <ResearchInput {...props} /> : <SecFilingPicker {...props} />}
    </section>
  );
}
export function DocumentResearchInput(props: ResearchInputProps) {
  const actor = useAuthStore(
    (state) => `${state.status}:${state.user?.id}:${state.user?.role}:${state.user?.is_active}`,
  );
  const access = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  return <Choice key={`${actor}:${access}`} {...props} />;
}
