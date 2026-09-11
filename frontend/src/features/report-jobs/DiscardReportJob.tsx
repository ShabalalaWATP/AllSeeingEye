import { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/Button';

export function DiscardReportJob({ busy, onDiscard }: { busy: boolean; onDiscard: () => void }) {
  const [confirming, setConfirming] = useState(false);
  const region = useRef<HTMLElement>(null);
  useEffect(() => {
    if (!confirming) return;
    region.current?.querySelector('button')?.focus({ preventScroll: true });
    if (typeof region.current?.scrollIntoView === 'function')
      region.current.scrollIntoView({ block: 'nearest' });
  }, [confirming]);
  return (
    <section ref={region} className="job-discard" aria-label="Discard unfinished job">
      {!confirming ? (
        <Button variant="ghost" onClick={() => setConfirming(true)}>
          Discard job
        </Button>
      ) : (
        <>
          <p>
            Discard this unfinished research job? Saved draft sections will be deleted. Published
            reports are kept.
          </p>
          <div>
            <Button variant="secondary" disabled={busy} onClick={() => setConfirming(false)}>
              Keep job
            </Button>
            <Button variant="danger" busy={busy} onClick={onDiscard}>
              {busy ? 'Discarding…' : 'Discard job permanently'}
            </Button>
          </div>
        </>
      )}
    </section>
  );
}
