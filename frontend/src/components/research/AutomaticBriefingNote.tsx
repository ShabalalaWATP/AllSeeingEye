import { Link } from 'react-router';

/**
 * Daily, economy and cyber briefings share one server admission rule
 * (DailyBriefingService): a personal briefing started in the previous 24 hours for the
 * same workspace and period is reused, and a paused or failed one is returned unchanged
 * rather than retried. Keep this copy in step with that rule.
 */
export function AutomaticBriefingNote({
  subject,
  className = 'max-w-3xl text-xs leading-5 text-muted',
}: {
  /** What starts the work, for example "Opening this page" or "Choosing a period". */
  subject: string;
  className?: string;
}) {
  return (
    <p className={className}>
      {subject} can start a personal AI briefing straight away. If you started one for the same
      period in the last 24 hours, that briefing is reused instead; a paused or failed briefing is
      shown as it is and is not retried automatically. Automatic briefings stay out of Saved
      research and the notification bell.{' '}
      <Link to="/research/jobs?briefings=1" className="text-ember underline underline-offset-4">
        Find them in Research progress
      </Link>
      .
    </p>
  );
}
