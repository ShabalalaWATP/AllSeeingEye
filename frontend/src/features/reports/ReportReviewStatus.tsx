import type { ReportStatus } from '@/lib/api/reports';

const messages: Record<ReportStatus, [string, string]> = {
  ready: [
    'Automated checks passed',
    'This does not establish factual accuracy or analyst verification.',
  ],
  needs_review: [
    'Review required',
    'Required automated checks found unresolved issues. Inspect the findings and cited evidence.',
  ],
  failed: [
    'Generation failed',
    'This version is not a completed assessment. Inspect the findings before generating another version.',
  ],
};

export function ReportReviewStatus({ status }: { status: ReportStatus }) {
  const [title, detail] = messages[status];
  return (
    <div aria-label="Review status" className="border-l-2 border-ember/60 py-1 pl-3 text-sm">
      <p className="font-medium">{title}</p>
      <p className="mt-1 text-xs text-muted">{detail}</p>
    </div>
  );
}
