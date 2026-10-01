import { useCallback } from 'react';
import { Link } from 'react-router';

import { getReportDiscussion } from '@/lib/api/teamBoard';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { startTeamThreadPath, teamThreadPath } from '@/lib/teamBoardLinks';

const action =
  'rounded-md border border-line px-3 py-2 text-sm font-medium text-text transition-colors hover:bg-surface-2 motion-reduce:transition-none';

/**
 * "Team discussion (n)" for a team report, linking to its newest board thread, and a
 * way to start one about this exact version. Personal or unreadable reports show nothing.
 */
export function ReportTeamDiscussion({ reportId, version }: { reportId: string; version: number }) {
  const load = useCallback(() => getReportDiscussion(reportId), [reportId]);
  const discussion = useScopedResource(load).data;
  if (!discussion?.team_id) return null;
  const label = `Team discussion (${String(discussion.count)})`;
  return (
    <div className="flex flex-wrap items-center gap-2">
      {discussion.latest_post_id ? (
        <Link to={teamThreadPath(discussion.team_id, discussion.latest_post_id)} className={action}>
          {label}
        </Link>
      ) : (
        <span className="px-1 text-xs text-muted">{label}</span>
      )}
      {discussion.can_post ? (
        <Link
          to={startTeamThreadPath(discussion.team_id, {
            kind: 'report_version',
            id: reportId,
            version,
          })}
          className={action}
        >
          Discuss this version
        </Link>
      ) : null}
    </div>
  );
}
