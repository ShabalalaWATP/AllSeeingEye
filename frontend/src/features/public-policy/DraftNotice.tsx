import { noticeApproved } from './content';

export function DraftNotice() {
  if (noticeApproved) return null;
  return (
    <aside className="policy-draft" aria-label="Draft notice">
      <strong>Draft for review. Publication is blocked.</strong>
      <p>The installation operator must confirm the details and approve this wording.</p>
    </aside>
  );
}
