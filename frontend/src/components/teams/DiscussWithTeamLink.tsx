import { Link } from 'react-router';

import type { BoardSubjectInput } from '@/lib/api/teamBoard';
import { startTeamThreadPath } from '@/lib/teamBoardLinks';

/**
 * Starts a team board thread about a saved team record. Personal records show nothing.
 * The link only opens the composer; the server re-checks membership and the subject.
 */
export function DiscussWithTeamLink({
  teamId,
  subject,
  className,
}: {
  teamId: string | null;
  subject: BoardSubjectInput;
  className: string;
}) {
  if (!teamId) return null;
  return (
    <Link to={startTeamThreadPath(teamId, subject)} className={className}>
      Discuss with team
    </Link>
  );
}
