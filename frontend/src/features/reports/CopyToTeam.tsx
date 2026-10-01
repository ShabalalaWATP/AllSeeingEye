/**
 * Copy this finished personal version into a team as a new team report. No model runs;
 * the reader reviews what is shared, confirms any private inputs, then copies once.
 */
import { useEffect, useId, useState } from 'react';
import { Link } from 'react-router';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField } from '@/components/ui/Field';
import { describeError } from '@/lib/api/errors';
import type { ReportSummary } from '@/lib/api/reports';
import {
  copyReportToTeam,
  fetchTeamCopyPreview,
  type TeamCopyPreview,
  type TeamCopyResult,
} from '@/lib/api/reportTeamCopies';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import type { Workspaces } from '@/lib/hooks/useWorkspaces';
import { useAuthStore } from '@/stores/auth';

import { TeamCopyDisclosure } from './TeamCopyDisclosure';

export function CopyToTeam({
  report,
  version,
  status,
  workspaces,
}: {
  report: ReportSummary;
  version: number;
  status: string;
  workspaces: Workspaces;
}) {
  const actor = useAuthStore((state) => state.user);
  const panelId = useId();
  const begin = useScopedRequest();
  const [open, setOpen] = useState(false);
  const [teamId, setTeamId] = useState('');
  const [preview, setPreview] = useState<TeamCopyPreview | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [result, setResult] = useState<TeamCopyResult | null>(null);
  const toggleId = useId();
  useEffect(() => {
    if (!open) return undefined;
    const close = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      setOpen(false);
      document.getElementById(toggleId)?.focus();
    };
    document.addEventListener('keydown', close);
    return () => document.removeEventListener('keydown', close);
  }, [open, toggleId]);
  const teams = workspaces.teams.filter(
    ({ team, members }) =>
      team.is_active && members.some((member) => member.user_id === actor?.id && member.is_active),
  );
  const review = useAsyncAction(async (chosen: string) => {
    setPreview(await fetchTeamCopyPreview(report.id, version, chosen, begin()));
  });
  const copy = useAsyncAction(async (chosen: TeamCopyPreview) => {
    setResult(
      await copyReportToTeam(
        report.id,
        version,
        {
          team_id: chosen.team_id,
          disclosed_evidence_labels: chosen.private_inputs.map((row) => row.label),
        },
        begin(),
      ),
    );
  });
  if (
    !actor ||
    report.team_id !== null ||
    report.created_by !== actor.id ||
    status === 'failed' ||
    teams.length === 0
  )
    return null;
  const choose = (value: string) => {
    setTeamId(value);
    setPreview(null);
    setConfirmed(false);
    setResult(null);
    review.clearError();
    copy.clearError();
  };
  const error = review.error ?? copy.error;
  const ready =
    preview !== null &&
    !preview.existing_report_id &&
    (preview.private_inputs.length === 0 || confirmed);
  return (
    <div className="relative">
      <Button
        id={toggleId}
        variant="secondary"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen(!open)}
      >
        Copy to team
      </Button>
      {open && (
        <div
          id={panelId}
          role="region"
          aria-label={`Copy version ${version} to a team`}
          className="absolute right-0 top-full z-20 mt-2 w-[min(28rem,calc(100vw-2rem))] space-y-3 rounded-md border border-line bg-surface p-4 shadow-lg"
        >
          <p className="text-sm text-muted">
            Copies version {version} as a new team report. No model runs and no research allowance
            is used. Your personal report and its other versions stay private.
          </p>
          <SelectField
            label="Team"
            value={teamId}
            options={[
              { value: '', label: 'Choose a team' },
              ...teams.map(({ team }) => ({ value: team.id, label: team.name })),
            ]}
            onChange={(event) => choose(event.target.value)}
          />
          <Button
            variant="ghost"
            disabled={!teamId}
            busy={review.busy}
            onClick={() => void review.run(teamId)}
          >
            Review what is shared
          </Button>
          {preview && !result && (
            <TeamCopyDisclosure preview={preview} confirmed={confirmed} onConfirm={setConfirmed} />
          )}
          {error && <Alert tone="error">{describeError(error)}</Alert>}
          {result ? (
            <Alert tone="success" title={result.created ? 'Copied to the team' : 'Already copied'}>
              <Link className="text-ember underline" to={`/reports/${result.report_id}`}>
                Open the team copy
              </Link>
            </Alert>
          ) : (
            preview &&
            !preview.existing_report_id && (
              <Button disabled={!ready} busy={copy.busy} onClick={() => void copy.run(preview)}>
                Copy to {preview.team_name}
              </Button>
            )
          )}
        </div>
      )}
    </div>
  );
}
