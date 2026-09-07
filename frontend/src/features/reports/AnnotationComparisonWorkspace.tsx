import { useCallback, useState } from 'react';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField } from '@/components/ui/Field';
import { compareAnnotations, exportAnnotationComparison } from '@/lib/api/annotationComparisons';
import type {
  AnnotationComparison,
  AnnotationComparisonInput,
} from '@/lib/api/annotationComparisons';
import { fetchReport } from '@/lib/api/reports';
import type { ReportSummary } from '@/lib/api/reports';
import { describeError } from '@/lib/api/errors';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { saveBinaryFile } from '@/lib/downloadBinary';
import { annotationKind } from './comparisonSelection';
import type { ComparisonAnnotation } from './comparisonSelection';
import { ComparisonReportPicker } from './ComparisonReportPicker';
import { ComparisonRevisionPicker } from './ComparisonRevisionPicker';
import { ComparisonCorrespondences } from './ComparisonCorrespondences';
import { AnnotationComparisonResult } from './AnnotationComparisonResult';
interface SideSelection {
  reportId: string;
  version: number;
  annotations: ComparisonAnnotation[];
}
function selection(value: SideSelection): AnnotationComparisonInput['before'] {
  return {
    report_id: value.reportId,
    version_number: value.version,
    revisions: value.annotations.flatMap((item) =>
      'claim_id' in item ? [{ claim_id: item.claim_id, revision_id: item.id }] : [],
    ),
    identity_revisions: value.annotations.flatMap((item) =>
      'decision_id' in item ? [{ decision_id: item.decision_id, revision_id: item.id }] : [],
    ),
    relationship_revisions: value.annotations.flatMap((item) =>
      'relationship_id' in item
        ? [{ relationship_id: item.relationship_id, revision_id: item.id }]
        : [],
    ),
  };
}
function SideControls({
  name,
  value,
  report,
  onChange,
}: {
  name: string;
  value: SideSelection;
  report: ReportSummary;
  onChange: (side: SideSelection) => void;
}) {
  const latest = report.latest_version;
  return (
    <section aria-label={name} className="space-y-3 rounded border border-line p-4">
      <h3 className="font-medium">{name}</h3>
      <ComparisonReportPicker
        name={name}
        current={report}
        onSelect={(chosen) =>
          onChange({ reportId: chosen.id, version: chosen.latest_version, annotations: [] })
        }
      />
      <SelectField
        label={`${name}: version`}
        value={String(value.version)}
        options={Array.from({ length: latest }, (_, i) => ({
          value: String(i + 1),
          label: `Version ${i + 1}`,
        }))}
        onChange={(event) =>
          onChange({ ...value, version: Number(event.target.value), annotations: [] })
        }
      />
      <ComparisonRevisionPicker
        key={`${value.reportId}:${value.version}`}
        reportId={value.reportId}
        version={value.version}
        selected={value.annotations}
        onChange={(annotations) => onChange({ ...value, annotations })}
      />
    </section>
  );
}
export function AnnotationComparisonWorkspace({ id, current }: { id: string; current: number }) {
  const [before, setBefore] = useState<SideSelection>({
    reportId: id,
    version: Math.max(1, current - 1),
    annotations: [],
  });
  const [after, setAfter] = useState<SideSelection>({
    reportId: id,
    version: current,
    annotations: [],
  });
  const [correspondences, setCorrespondences] = useState<
    NonNullable<AnnotationComparisonInput['correspondences']>
  >([]);
  const [judgements, setJudgements] = useState<
    NonNullable<AnnotationComparisonInput['judgement_correspondences']>
  >([]);
  const [result, setResult] = useState<{
    body: AnnotationComparisonInput;
    value: AnnotationComparison;
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const read = useScopedRequest();
  const request = useScopedRequest();
  const loader = useCallback(async () => {
    const signal = read();
    const [left, right] = await Promise.all([
      fetchReport(before.reportId, before.version, signal),
      fetchReport(after.reportId, after.version, signal),
    ]);
    signal.throwIfAborted();
    return { left, right };
  }, [read, before.reportId, before.version, after.reportId, after.version]);
  const resource = useScopedResource(loader);
  const change = (side: 'before' | 'after', value: SideSelection) => {
    setResult(null);
    setError(null);
    setCorrespondences([]);
    setJudgements([]);
    if (side === 'before') setBefore(value);
    else setAfter(value);
  };
  const compare = async () => {
    if (busy || !resource.data) return;
    const signal = request();
    setBusy(true);
    setResult(null);
    setError(null);
    const body: AnnotationComparisonInput = {
      before: selection(before),
      after: selection(after),
      correspondences,
      judgement_correspondences: judgements,
    };
    try {
      const value = await compareAnnotations(body, signal);
      signal.throwIfAborted();
      setResult({ body, value });
    } catch (caught) {
      if (!signal.aborted) setError(caught);
    } finally {
      if (!signal.aborted) setBusy(false);
    }
  };
  const download = async () => {
    if (busy || !result) return;
    const signal = request();
    setBusy(true);
    setError(null);
    try {
      const blob = await exportAnnotationComparison(
        { ...result.body, expected_comparison_sha256: result.value.comparison_sha256 },
        signal,
      );
      signal.throwIfAborted();
      saveBinaryFile('frozen-annotation-comparison.json', blob);
    } catch (caught) {
      if (!signal.aborted) setError(caught);
    } finally {
      if (!signal.aborted) setBusy(false);
    }
  };
  return (
    <section aria-label="Annotation and confidence comparison" className="mt-4 space-y-4">
      <p className="text-sm text-muted">
        Compare exact annotation revisions and frozen confidence inputs. Choose direction
        explicitly, including two revisions within the same report version. Different reports must
        share an owner or team. This creates a reproducible preview and export; it does not enable
        monitoring.
      </p>
      {resource.loading && <LoadingNote label="Loading selected comparison reports" />}
      {resource.error && (
        <Alert tone="error">
          {describeError(resource.error)}{' '}
          <Button variant="secondary" onClick={() => void resource.reload()}>
            Retry comparison inputs
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              change('before', {
                reportId: id,
                version: Math.max(1, current - 1),
                annotations: [],
              });
              change('after', { reportId: id, version: current, annotations: [] });
            }}
          >
            Discard unavailable inputs and return to this report
          </Button>
        </Alert>
      )}
      {resource.data && (
        <fieldset disabled={busy} className="space-y-4">
          <div className="grid gap-4 xl:grid-cols-2">
            <SideControls
              name="Selected before"
              value={before}
              report={resource.data.left.report}
              onChange={(value) => change('before', value)}
            />
            <SideControls
              name="Selected after"
              value={after}
              report={resource.data.right.report}
              onChange={(value) => change('after', value)}
            />
          </div>
          <ComparisonCorrespondences
            key={`${before.annotations.map((item) => `${annotationKind(item)}:${item.id}`).join(',')}:${after.annotations.map((item) => `${annotationKind(item)}:${item.id}`).join(',')}`}
            before={before.annotations}
            after={after.annotations}
            beforeReport={resource.data.left}
            afterReport={resource.data.right}
            annotations={correspondences}
            judgements={judgements}
            onAnnotations={(value) => {
              setCorrespondences(value);
              setResult(null);
            }}
            onJudgements={(value) => {
              setJudgements(value);
              setResult(null);
            }}
          />
          <Button variant="secondary" onClick={() => void compare()}>
            {busy ? 'Working...' : 'Compare exact selected inputs'}
          </Button>
        </fieldset>
      )}
      {error !== null && <Alert tone="error">{describeError(error)}</Alert>}
      {result && (
        <>
          <AnnotationComparisonResult value={result.value} />
          <p className="text-xs text-muted">
            Export rechecks access and this comparison digest. Changed inputs or method require a
            new preview. JSON manifest is limited to 8 MiB.
          </p>
          <Button variant="secondary" disabled={busy} onClick={() => void download()}>
            Export frozen comparison
          </Button>
        </>
      )}
    </section>
  );
}
