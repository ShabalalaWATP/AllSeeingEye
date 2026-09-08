import { useState } from 'react';
import { Link } from 'react-router';
import { Button } from '@/components/ui/Button';
import { AnnotationMonitorCreate } from './AnnotationMonitorCreate';
import { AnnotationMonitorList } from './AnnotationMonitorList';
import { MonitorPrivacyBoundary } from './MonitorPrivacyBoundary';
function Contents({
  reportId,
  version,
  canCreate,
}: {
  reportId: string;
  version: number;
  canCreate: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [refresh, setRefresh] = useState(0);
  return (
    <section className="space-y-3 border-t border-line pt-4">
      <Button variant="secondary" aria-expanded={open} onClick={() => setOpen(!open)}>
        Monitor annotations
      </Button>
      {open && (
        <>
          <p className="text-sm text-muted">
            Watch corrections without regenerating this report. Choose selected annotations or the
            whole inventory of this saved version. Monitoring stays pinned to this version.
          </p>
          <Link to="/annotation-monitors" className="text-sm text-ember underline">
            All annotation monitors
          </Link>
          <AnnotationMonitorList key={refresh} scope={{ reportId, version }} />
          {canCreate && (
            <Button variant="secondary" onClick={() => setCreating(!creating)}>
              {creating ? 'Cancel monitor creation' : 'Create an annotation monitor'}
            </Button>
          )}
          {canCreate && creating && (
            <AnnotationMonitorCreate
              reportId={reportId}
              version={version}
              onCreated={() => {
                setCreating(false);
                setRefresh((value) => value + 1);
              }}
            />
          )}
        </>
      )}
    </section>
  );
}
export function AnnotationMonitorsSection(props: {
  reportId: string;
  version: number;
  canCreate: boolean;
}) {
  return (
    <MonitorPrivacyBoundary scope={`${props.reportId}:${props.version}`}>
      <Contents {...props} />
    </MonitorPrivacyBoundary>
  );
}
