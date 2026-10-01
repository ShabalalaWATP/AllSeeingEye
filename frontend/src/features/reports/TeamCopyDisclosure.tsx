import { Link } from 'react-router';

import { Alert } from '@/components/ui/Alert';
import type { TeamCopyPreview } from '@/lib/api/reportTeamCopies';

import { COPIED_CONTENT, notCopiedLines, OMISSION_TEXT } from './teamCopyText';

/** What the copy will show the team, what stays personal, and any private inputs. */
export function TeamCopyDisclosure({
  preview,
  confirmed,
  onConfirm,
}: {
  preview: TeamCopyPreview;
  confirmed: boolean;
  onConfirm: (value: boolean) => void;
}) {
  const omitted = [
    ...preview.omissions.map((code) => OMISSION_TEXT[code]),
    ...notCopiedLines(preview.not_copied),
  ];
  if (preview.existing_report_id) {
    return (
      <Alert tone="info" title={`Already copied to ${preview.team_name}`}>
        <Link className="text-ember underline" to={`/reports/${preview.existing_report_id}`}>
          Open the team copy
        </Link>
      </Alert>
    );
  }
  return (
    <div className="space-y-3 text-sm">
      <div>
        <p className="font-medium text-text">Copied to {preview.team_name}</p>
        <p className="text-muted">{COPIED_CONTENT}</p>
      </div>
      {omitted.length > 0 && (
        <div>
          <p className="font-medium text-text">Not copied</p>
          <ul className="list-disc space-y-1 pl-5 text-muted">
            {omitted.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </div>
      )}
      {preview.private_inputs.length > 0 && (
        <Alert tone="warning" title="Private inputs will be visible to the team">
          <ul className="my-2 list-disc space-y-1 pl-5">
            {preview.private_inputs.map((row) => (
              <li key={row.label}>
                <span className="font-mono">{row.label}</span> {row.title}
              </li>
            ))}
          </ul>
          <label className="flex items-start gap-2">
            <input
              type="checkbox"
              className="mt-1"
              checked={confirmed}
              onChange={(event) => onConfirm(event.target.checked)}
            />
            <span>Share these private inputs with current members of {preview.team_name}</span>
          </label>
        </Alert>
      )}
    </div>
  );
}
