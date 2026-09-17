import type { ReportStatus } from '@/lib/api/reports';

/**
 * The saved automated-check status for one frozen version. The wording states what
 * the checks did and did not establish; it never implies analyst verification.
 */
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

const marks: Record<ReportStatus, string> = {
  ready: '✓',
  needs_review: '!',
  failed: '×',
};

/** Chrome tones follow the workspace theme; paper tones follow the document palette. */
const chromeTones: Record<ReportStatus, string> = {
  ready: 'border-line bg-surface text-text',
  needs_review: 'border-amber/60 bg-amber/10 text-text',
  failed: 'border-critical/60 bg-critical/10 text-text',
};

const chromeMarks: Record<ReportStatus, string> = {
  ready: 'bg-surface-2 text-muted',
  needs_review: 'bg-amber/25 text-amber',
  failed: 'bg-critical/25 text-critical',
};

const paperTones: Record<ReportStatus, string> = {
  ready:
    'border-[color:var(--paper-rule)] bg-[color:var(--paper-ground-2)] text-[color:var(--paper-ink)]',
  needs_review:
    'border-[color:var(--paper-caution-rule)] bg-[color:var(--paper-caution-ground)] text-[color:var(--paper-caution-ink)]',
  failed: 'border-[#b7554b] bg-[#fdefec] text-[#6f2b24]',
};

export function ReportReviewStatus({
  status,
  variant = 'chrome',
}: {
  status: ReportStatus;
  variant?: 'chrome' | 'paper';
}) {
  const [title, detail] = messages[status];
  const paper = variant === 'paper';
  const tone = paper ? paperTones[status] : chromeTones[status];
  return (
    <div
      aria-label="Review status"
      className={`flex items-start gap-3 rounded-md border border-l-[3px] px-3 py-2.5 ${tone}`}
    >
      <span
        aria-hidden="true"
        className={`mt-0.5 grid size-5 shrink-0 place-items-center rounded-full text-xs font-bold ${
          paper ? 'bg-black/8 text-current' : chromeMarks[status]
        }`}
      >
        {marks[status]}
      </span>
      <span className="min-w-0">
        <span className="block text-sm font-semibold">{title}</span>
        <span className={`mt-0.5 block text-xs leading-5 ${paper ? 'opacity-85' : 'text-muted'}`}>
          {detail}
        </span>
      </span>
    </div>
  );
}
