import { Link } from 'react-router';
import { AnnotationMonitorList } from './AnnotationMonitorList';
import { MonitorPrivacyBoundary } from './MonitorPrivacyBoundary';
export default function AnnotationMonitorsPage() {
  return (
    <MonitorPrivacyBoundary scope="monitor-list">
      <main className="space-y-6 overflow-y-auto p-6">
        <h1 className="text-xl font-semibold">Annotation monitoring</h1>
        <p className="text-sm text-muted">
          Optional monitoring of selected claims, identity reviews and organisation relationships
          within an exact report version. Initial baselines are silent; future evidence collection
          remains separate.
        </p>
        <Link to="/reports" className="text-ember underline">
          Choose a report to create a monitor
        </Link>
        <AnnotationMonitorList />
      </main>
    </MonitorPrivacyBoundary>
  );
}
