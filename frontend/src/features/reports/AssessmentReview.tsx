import { useCallback } from 'react';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import {
  fetchCitationVerdictExport,
  fetchCitationVerdicts,
  recordCitationVerdict,
  type CitationVerdictInput,
} from '@/lib/api/citationVerdicts';
import { describeError } from '@/lib/api/errors';
import type { ReportVersion } from '@/lib/api/reports';
import type { TeamDetail } from '@/lib/api/teams';
import { saveBinaryFile } from '@/lib/downloadBinary';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { useAuthStore } from '@/stores/auth';

import { CitationCheckMethod, JudgementCitationChecks } from './CitationChecks';
import { CitationVerdictControls } from './CitationVerdictControls';
import { JudgementEvidence } from './JudgementEvidence';
import { reviewerName } from './reviewerNames';

/**
 * Per-judgement technical review: frozen evidence contribution, literal citation checks
 * and human citation verdicts. Verdicts are opinions and never change the frozen report.
 */
export function AssessmentReview({
  reportId,
  version,
  teams,
}: {
  reportId: string;
  version: ReportVersion;
  teams: readonly TeamDetail[];
}) {
  const actorId = useAuthStore((state) => state.user?.id);
  const loader = useCallback(
    () => fetchCitationVerdicts(reportId, version.number),
    [reportId, version.number],
  );
  const verdicts = useScopedResource(loader);
  const { refresh } = verdicts;
  const reviewer = (id: string) => reviewerName(id, actorId, teams);
  const record = async (body: CitationVerdictInput) => {
    const saved = await recordCitationVerdict(reportId, version.number, body);
    await refresh();
    return saved;
  };
  const download = useAsyncAction(async () => {
    const file = await fetchCitationVerdictExport(reportId, version.number);
    saveBinaryFile(
      file.filename ?? `citation-verdicts-${reportId}-v${String(version.number)}.jsonl`,
      file.blob,
    );
  });
  const list = verdicts.data;
  return (
    <>
      {version.body.key_judgements.map((judgement) => {
        const assessment = version.assessment?.judgements.find(
          (item) => item.judgement_id === judgement.id,
        );
        const citationCheck = version.citation_checks?.judgements.find(
          (item) => item.judgement_id === judgement.id,
        );
        if (!assessment && !citationCheck) return null;
        return (
          <section key={judgement.id} aria-label={`Technical review for ${judgement.id}`}>
            <h2 className="text-sm font-semibold">{judgement.id}</h2>
            <p className="mt-1 text-xs leading-5 text-muted">{judgement.statement}</p>
            {assessment && <JudgementEvidence assessment={assessment} />}
            <JudgementCitationChecks
              check={citationCheck}
              renderCitation={(citation) =>
                list ? (
                  <CitationVerdictControls
                    anchor={{
                      judgementId: judgement.id,
                      label: citation.label,
                      relation: citation.relation,
                    }}
                    list={list}
                    reviewer={reviewer}
                    onRecord={record}
                  />
                ) : null
              }
            />
          </section>
        );
      })}
      <CitationCheckMethod checks={version.citation_checks} />
      <section aria-label="Human citation verdicts" className="space-y-2 text-xs text-muted">
        <h2 className="text-sm font-semibold text-text">Human citation verdicts</h2>
        {list ? (
          <p>{list.notice}</p>
        ) : verdicts.loading ? (
          <LoadingNote label="Loading citation verdicts" />
        ) : (
          <Alert tone="warning">
            Citation verdicts are unavailable: {describeError(verdicts.error)}
          </Alert>
        )}
        <p>
          The export lists this version&apos;s verdicts with the frozen judgement text and cited
          excerpt, for the evaluation harness reader. Counts are reported with their denominators.
        </p>
        {download.error && <Alert tone="error">{describeError(download.error)}</Alert>}
        <Button variant="secondary" busy={download.busy} onClick={() => void download.run()}>
          Download citation verdicts (JSONL)
        </Button>
      </section>
    </>
  );
}
