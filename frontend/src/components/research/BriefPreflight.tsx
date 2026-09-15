import { useEffect, useRef, useState } from 'react';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { describeError } from '@/lib/api/errors';
import { fetchBriefPreflight, type ResearchPreflight } from '@/lib/api/researchPreflight';
import type { ResearchBrief } from '@/lib/api/researchBriefSchema';

import { BriefPreflightResult } from './BriefPreflightResult';

export function BriefPreflight({
  brief,
  dirty,
  editorBusy,
}: {
  brief: ResearchBrief | null;
  dirty: boolean;
  editorBusy: boolean;
}) {
  const [preview, setPreview] = useState<ResearchPreflight | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const request = useRef<AbortController | null>(null);
  useEffect(() => () => request.current?.abort(), []);
  const load = async () => {
    if (!brief || dirty || editorBusy || busy) return;
    const controller = new AbortController();
    request.current?.abort();
    request.current = controller;
    setBusy(true);
    setError(null);
    setPreview(null);
    try {
      setPreview(await fetchBriefPreflight(brief, controller.signal));
    } catch (caught) {
      if (!controller.signal.aborted) setError(describeError(caught));
    } finally {
      if (!controller.signal.aborted) setBusy(false);
      request.current = null;
    }
  };
  return (
    <section className="space-y-3 border-t border-line pt-4" aria-label="Research preflight">
      <div className="flex flex-wrap items-center gap-3">
        <Button
          variant="secondary"
          busy={busy}
          disabled={!brief || dirty || editorBusy || busy}
          onClick={() => void load()}
        >
          {error ? 'Retry preview' : 'Preview saved brief'}
        </Button>
        <p className="text-xs text-muted">
          {!brief
            ? 'Save a brief to preview an exact revision.'
            : dirty
              ? 'Save a new revision to preview these edits.'
              : `Read-only preview of revision ${brief.identity.revision}.`}
        </p>
      </div>
      {busy && <LoadingNote label="Checking saved brief" />}
      {error && <Alert tone="error">{error}</Alert>}
      {!dirty && preview && <BriefPreflightResult preview={preview} />}
    </section>
  );
}
