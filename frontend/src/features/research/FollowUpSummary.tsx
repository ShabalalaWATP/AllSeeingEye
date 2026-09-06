import type { Report, ReportRequest } from '@/lib/api/reports';
import type { Workspaces } from '@/lib/hooks/useWorkspaces';

export function FollowUpSummary({
  parent,
  request,
  workspaces,
}: {
  parent: Report;
  request: ReportRequest;
  workspaces: Workspaces;
}) {
  return (
    <section
      aria-label="Follow-up scope"
      className="space-y-2 border-y border-line py-4 text-xs text-muted [overflow-wrap:anywhere]"
    >
      <h2 className="text-sm font-medium text-text">Follow-up to {parent.report.title}</h2>
      <p>
        {workspaces.label(parent.report.team_id)} · {request.research_focus} ·{' '}
        {request.research_subject ?? request.country ?? 'Original scope'} ·{' '}
        {request.research_languages?.join(', ')}
      </p>
      <p>
        The original workspace, focus and collection scope are fixed. The server binds the latest
        parent version when this run starts and saves that version reference with the new report.
      </p>
      {(request.research_focus === 'document' || request.research_focus === 'media') && (
        <p>
          Uses the parent report’s saved private evidence. No public search is started from that
          content.
        </p>
      )}
    </section>
  );
}
