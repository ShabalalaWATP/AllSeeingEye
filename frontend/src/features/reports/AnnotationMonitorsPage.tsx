import { PageHeader } from '@/components/ui/PageHeader';
import { Link } from 'react-router';
import { AnnotationMonitorList } from './AnnotationMonitorList';
import { MonitorPrivacyBoundary } from './MonitorPrivacyBoundary';
export default function AnnotationMonitorsPage() {
  return (
    <MonitorPrivacyBoundary scope="monitor-list">
      <section className="space-y-6 overflow-y-auto p-6">
        <PageHeader type="record" title="Annotation monitors" />
        <p className="text-sm text-muted">
          Optional monitoring of selected annotations or the whole claim, identity review and
          organisation relationship inventory within an exact saved report version. Initial
          baselines are silent; future evidence collection remains separate.
        </p>
        <Link to="/reports" className="text-ember underline">
          Choose a report to create a monitor
        </Link>
        <AnnotationMonitorList />
      </section>
    </MonitorPrivacyBoundary>
  );
}
