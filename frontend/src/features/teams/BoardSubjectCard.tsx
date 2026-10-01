import { Link } from 'react-router';

import type { BoardSubjectInput, BoardSubjectKind, TeamBoardSubject } from '@/lib/api/teamBoard';

const KIND_NAMES: Record<BoardSubjectKind, string> = {
  report_version: 'report version',
  saved_area: 'saved area',
  drawing_collection: 'drawing collection',
};

/** "Report version 2", "Saved area" or "Drawing collection". */
export function subjectLabel(subject: Pick<BoardSubjectInput, 'kind' | 'version'>): string {
  const name = KIND_NAMES[subject.kind];
  const label = name.charAt(0).toUpperCase() + name.slice(1);
  return subject.kind === 'report_version' && subject.version != null
    ? `${label} ${String(subject.version)}`
    : label;
}

/**
 * The team work a thread discusses, as the reader may see it now. Titles render as
 * text nodes; an unavailable subject shows no title, identifier or link.
 */
export function BoardSubjectCard({ subject }: { subject: TeamBoardSubject }) {
  const label = subjectLabel(subject);
  const reportLink =
    subject.available && subject.kind === 'report_version' && subject.id && subject.version
      ? `/reports/${encodeURIComponent(subject.id)}?version=${String(subject.version)}`
      : null;
  return (
    <div
      role="group"
      aria-label={`Linked ${KIND_NAMES[subject.kind]}`}
      className="mt-3 border-l-2 border-cyan/60 bg-surface-2/50 px-3 py-2"
    >
      <p className="font-mono text-2xs uppercase tracking-[0.18em] text-muted">{label}</p>
      {subject.available && subject.title !== null ? (
        reportLink ? (
          <Link
            to={reportLink}
            className="mt-1 block break-words text-sm font-medium text-text underline-offset-4 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan"
          >
            {subject.title}
          </Link>
        ) : (
          <p className="mt-1 break-words text-sm font-medium text-text">{subject.title}</p>
        )
      ) : (
        <>
          <p className="mt-1 text-sm font-medium text-muted">Linked item unavailable</p>
          <p className="mt-0.5 text-xs text-muted">
            You can no longer open this item, or it has moved or been deleted.
          </p>
        </>
      )}
    </div>
  );
}
