import type { ReportStatus } from '@/lib/api/reports';

const messages: Record<ReportStatus, [string, string]> = {
  ready: [
    'Automated checks passed',
    'This does not establish factual accuracy or analyst verification.',
  ],
  needs_review: [
    'Review required',
    'Some checks found unresolved evidence or coverage issues. Treat the affected findings with caution.',
  ],
  failed: [
    'Generation failed',
    'This version is not a completed assessment. Inspect the findings before generating another version.',
  ],
};

const tones: Record<ReportStatus, string> = {
  ready: 'border-[#a9a397] bg-[#f1ede4] text-[#49453f]',
  needs_review: 'border-[#c58a24] bg-[#fff7e6] text-[#62440e]',
  failed: 'border-[#b7554b] bg-[#fff0ed] text-[#702b25]',
};

export function ReportReviewStatus({ status }: { status: ReportStatus }) {
  const [title, detail] = messages[status];
  return (
    <div aria-label="Review status" className={`border-l-2 px-3 py-2 text-sm ${tones[status]}`}>
      <p className="font-semibold">{title}</p>
      <p className="mt-0.5 text-xs leading-5 opacity-80">{detail}</p>
    </div>
  );
}
