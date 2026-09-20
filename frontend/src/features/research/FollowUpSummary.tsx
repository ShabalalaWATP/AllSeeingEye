import type { Report } from '@/lib/api/reports';
import type { Workspaces } from '@/lib/hooks/useWorkspaces';
import type { FollowUpRequest } from '@/lib/followUpScope';

export function FollowUpSummary({
  parent,
  request,
  workspaces,
}: {
  parent: Report;
  request: FollowUpRequest;
  workspaces: Workspaces;
}) {
  return (
    <section
      aria-label="Follow-up scope"
      className="space-y-2 border-y border-line py-4 text-xs text-muted [overflow-wrap:anywhere]"
    >
      <h2 className="text-sm font-medium text-text">
        Follow-up to {parent.report.title}, edition {request.parent_version}
      </h2>
      <p>
        Parent observation period:{' '}
        {parent.version.period_from && parent.version.period_to
          ? `${parent.version.period_from} to ${parent.version.period_to} (end excluded).`
          : 'Not recorded for this edition.'}
      </p>
      <p>
        {workspaces.label(parent.report.team_id)} · {request.research_focus} ·{' '}
        {request.research_subject ??
          (request.countries?.length
            ? request.countries.join(', ')
            : (request.country ?? 'Worldwide'))}{' '}
        · {request.research_languages?.join(', ')}
      </p>
      <p>
        {request.research_since && request.research_until
          ? `${request.research_time_basis === 'recorded_time' ? 'Recorded-time' : 'Fixed'} period: ${request.research_since} to ${request.research_until} (end excluded).`
          : `Rolling period: ${request.window_hours ?? 'original'} hours.`}{' '}
        Fresh web search{' '}
        {request.research_web_search ? 'enabled, with the original provider disclosure' : 'off'}.
      </p>
      {!!request.research_planned_tasks?.length && (
        <p>
          Retains {request.research_planned_tasks.length} explicit challenge or identity searches
          and {request.research_candidate_hypotheses?.length ?? 0} candidate hypotheses. These
          remain unverified research inputs and share the normal collection budget.
        </p>
      )}
      {request.research_area && (
        <p>Uses the exact saved area geometry and its original provider disclosure.</p>
      )}
      <p>
        The original workspace, focus, period and collection scope are fixed. The server checks
        access to edition {request.parent_version} and records that exact parent reference with the
        new report.
      </p>
      {(request.research_source_ids !== undefined ||
        request.research_terms !== undefined ||
        Boolean(request.research_query_variants?.length)) && (
        <p>
          Saved collection settings are retained:{' '}
          {request.research_source_ids === null || request.research_source_ids === undefined
            ? 'default sources'
            : `${request.research_source_ids.length} selected sources`}
          ,{' '}
          {request.research_terms === null || request.research_terms === undefined
            ? 'run-time query planning'
            : 'exact original terms'}
          , and {request.research_query_variants?.length ?? 0} language-specific term sets.
        </p>
      )}
      {(request.research_focus === 'document' || request.research_focus === 'media') && (
        <p>
          Uses the parent report’s saved private evidence. No public search is started from that
          content.
        </p>
      )}
    </section>
  );
}
