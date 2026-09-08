import type { AnnotationMonitor, MonitorTransition } from '@/lib/api/annotationMonitors';
import { plainUser, report } from './fixtures';
import { annotationComparison, comparisonClaimAfter } from './fixtures.comparisons';
export const annotationMonitor: AnnotationMonitor = {
  mode: 'selected_roots',
  id: 'monitor-1',
  created_by: plainUser.id,
  team_id: null,
  report_id: report.report.id,
  version_number: 1,
  name: 'Company review corrections',
  categories: ['claim'],
  notify_on_change: false,
  status: 'active',
  unavailable_reason: null,
  revision: 1,
  checkpoint_id: 'checkpoint-1',
  checkpoint_number: 1,
  selection: {
    report_id: report.report.id,
    version_number: 1,
    revisions: [{ claim_id: comparisonClaimAfter.claim_id, revision_id: comparisonClaimAfter.id }],
    identity_revisions: [],
    relationship_revisions: [],
  },
  created_at: '2026-09-07T12:00:00Z',
  updated_at: '2026-09-07T12:00:00Z',
};
export const monitorTransition: MonitorTransition = {
  id: 'transition-old',
  monitor_id: annotationMonitor.id,
  checkpoint_before: 'checkpoint-1',
  checkpoint_after: 'checkpoint-2',
  sequence: 1,
  kind: 'revision',
  recorded_at: '2026-09-07T13:00:00Z',
  changed_categories: ['claim'],
  alert_id: null,
  comparison_sha256: annotationComparison.comparison_sha256,
  configuration_revision: 1,
  notification_categories: ['claim'],
  notify_on_change: false,
};
export const monitorDetail = { transition: monitorTransition, comparison: annotationComparison };
