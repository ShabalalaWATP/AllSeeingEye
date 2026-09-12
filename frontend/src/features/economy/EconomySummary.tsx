import { IntelligenceSummary } from '@/components/research/IntelligenceSummary';
import type { Report } from '@/lib/api/reports';

export function EconomySummary({ report }: { report: Report }) {
  return <IntelligenceSummary report={report} subject="Economic" />;
}
