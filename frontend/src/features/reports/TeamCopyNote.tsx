/** Provenance of a team report copied from a personal version, for its current readers. */
import { useCallback } from 'react';
import { Link } from 'react-router';

import { fetchTeamCopyProvenance } from '@/lib/api/reportTeamCopies';
import { formatPersonalDate } from '@/lib/format';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { useProfile } from '@/stores/profile';

export function TeamCopyNote({ reportId }: { reportId: string }) {
  const preferences = useProfile();
  const begin = useScopedRequest();
  const loader = useCallback(
    // Most team reports are not copies; a missing provenance record shows nothing.
    () => fetchTeamCopyProvenance(reportId, begin()).catch(() => null),
    [begin, reportId],
  );
  const { data } = useScopedResource(loader);
  if (!data) return null;
  const who = data.copied_by_name ?? 'a former member';
  return (
    <p className="report-reader-print-hide mb-4 rounded-md border border-line bg-surface px-3 py-2 text-sm text-muted">
      Copied from a personal report (version {data.source_version_number}) by {who} on{' '}
      {formatPersonalDate(data.copied_at, preferences.profile)}, without another model run.
      {data.disclosed_private_inputs > 0 &&
        ` It includes ${data.disclosed_private_inputs} private ${
          data.disclosed_private_inputs === 1 ? 'input' : 'inputs'
        } its owner chose to share.`}{' '}
      {data.source_report_id && (
        <Link
          className="text-ember underline"
          to={`/reports/${data.source_report_id}?version=${data.source_version_number}`}
        >
          Open your personal original
        </Link>
      )}
    </p>
  );
}
