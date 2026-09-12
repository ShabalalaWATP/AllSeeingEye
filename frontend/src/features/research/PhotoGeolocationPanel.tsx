import { useState, type SyntheticEvent } from 'react';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { TextAreaField } from '@/components/ui/Field';
import { WorkspaceField } from '@/components/ui/WorkspaceField';
import { describeError } from '@/lib/api/errors';
import { useWorkspaceSelection, type Workspaces } from '@/lib/hooks/useWorkspaces';

import { PhotoGeolocationResult } from './PhotoGeolocationResult';
import { PhotoGeolocationUpload } from './PhotoGeolocationUpload';
import { ResearchProgress } from './ResearchProgress';
import { usePhotoGeolocation } from './usePhotoGeolocation';
import { usePhotoInputs } from './usePhotoInputs';
import { useResearchRun } from './useResearchRun';
import { holdPhotoReceipt } from './photoReceiptRegistry';

export function PhotoGeolocationPanel({ workspaces }: { workspaces: Workspaces }) {
  const scope = useWorkspaceSelection(workspaces);
  return (
    <section aria-label="Geolocate a photo" className="min-w-0 space-y-6">
      {!scope.valid && (
        <Alert tone="error">
          This team is no longer available. Choose Personal or another team.
        </Alert>
      )}
      <PhotoGeolocationForm
        key={`${workspaces.key}:${scope.teamId}`}
        teamId={scope.teamId}
        ready={scope.ready}
        workspaceLabel={workspaces.label(scope.teamId)}
        workspaces={workspaces}
        selectTeam={scope.select}
      />
    </section>
  );
}

function PhotoGeolocationForm({
  teamId,
  ready,
  workspaceLabel,
  workspaces,
  selectTeam,
}: {
  teamId: string;
  ready: boolean;
  workspaceLabel: string;
  workspaces: Workspaces;
  selectTeam: (teamId: string) => void;
}) {
  const input = usePhotoInputs();
  const analysis = usePhotoGeolocation(input.receipts, input.key, teamId);
  const report = useResearchRun();
  const [question, setQuestion] = useState('');
  const [hints, setHints] = useState('');
  const [consentKey, setConsentKey] = useState('');
  const [validation, setValidation] = useState<string | null>(null);
  const receiptKey = `${input.key}:${input.receipts.map((item) => item.id).join(',')}`;
  const consent = input.receipts.length > 0 && consentKey === receiptKey;
  const busy = analysis.busy || report.busy;
  const result = analysis.result;
  const upload = (files: readonly File[]) => {
    analysis.clear();
    report.clearError();
    setConsentKey('');
    setValidation(null);
    void input.replace(files);
  };
  const submit = (event: SyntheticEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!ready || busy || input.busy || !consent) return;
    void analysis.analyse(question, hints, consent);
  };
  const save = () => {
    if (!result || !ready || busy || !input.receipts.length) return;
    if (Date.parse(result.input.expires_at) <= Date.now()) {
      analysis.clear();
      setValidation('The analysis has expired. Upload the photo again before saving a report.');
      return;
    }
    const releases = input.receipts.map((receipt) => holdPhotoReceipt(input.key, receipt));
    void report
      .run({
        template: 'ask',
        question:
          analysis.question.trim() ||
          (input.receipts.length > 1
            ? 'Where might these photographs have been taken? Assess the unverified candidates, compare the photos and explain how to verify them.'
            : 'Where might this photograph have been taken? Assess the unverified candidates and explain how to verify them.'),
        research_focus: 'media',
        research_input_id: result.input.id,
        research_mode: 'quick',
        research_web_search: false,
        research_languages: ['en'],
        report_language: 'en',
        report_style: 'assessment',
        devils_advocacy: false,
        window_hours: 24,
        team_id: teamId || null,
        disclose_area_to_provider: false,
      })
      .finally(() => releases.forEach((release) => release()));
  };
  const changeDestination = async (nextTeam: string) => {
    if (busy || nextTeam === teamId) return;
    analysis.clear();
    setConsentKey('');
    if (await input.replace()) selectTeam(nextTeam);
  };
  return (
    <div className="min-w-0 space-y-6">
      <div className="max-w-xl">
        <WorkspaceField
          workspaces={workspaces}
          value={teamId}
          disabled={busy || input.busy}
          onChange={(value) => {
            void changeDestination(value);
          }}
        />
        <p className="mt-2 text-xs text-muted">
          This selects the analysis model and report destination. Changing it clears all photos.
        </p>
      </div>
      <form aria-label="Analyse a photograph" onSubmit={submit} className="min-w-0">
        <div className="grid min-w-0 gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <PhotoGeolocationUpload
            input={input}
            disabled={busy}
            onUpload={upload}
            validation={validation}
            onRemove={(id) => {
              analysis.clear();
              setConsentKey('');
              void input.remove(id);
            }}
          />
          <fieldset disabled={busy} className="min-w-0 space-y-5 disabled:opacity-70">
            <TextAreaField
              label={
                input.receipts.length === 1
                  ? 'Question about the photo'
                  : 'Question about the photos'
              }
              value={question}
              maxLength={1000}
              rows={3}
              hint="Optional. One question is applied to the whole photo set."
              placeholder="Where were these photos taken, and do they show the same location?"
              onChange={(event) => {
                setQuestion(event.target.value);
                analysis.clear();
              }}
            />
            <TextAreaField
              label="Context or location hints"
              value={hints}
              maxLength={1000}
              rows={3}
              hint="Label hints by Photo 1, Photo 2, etc. Hints are claims to test, not confirmed facts."
              placeholder="Possible country, approximate date, or where the photo came from."
              onChange={(event) => {
                setHints(event.target.value);
                analysis.clear();
              }}
            />
            <label className="flex cursor-pointer items-start gap-3 border-t border-line pt-5">
              <input
                type="checkbox"
                checked={consent}
                disabled={!input.receipts.length || input.busy}
                onChange={(event) => setConsentKey(event.target.checked ? receiptKey : '')}
                className="mt-1 h-4 w-4 shrink-0 accent-ember"
              />
              <span className="text-sm leading-relaxed">
                Send{' '}
                {input.receipts.length === 1
                  ? 'this photo preview'
                  : input.receipts.length > 1
                    ? `these ${input.receipts.length} photo previews`
                    : 'the selected photo previews'}{' '}
                and context to the configured model for {workspaceLabel}.
                <span className="mt-1 block text-xs text-muted">
                  This does not upload your photo to a public search engine.
                </span>
              </span>
            </label>
            <Button
              type="submit"
              className="min-h-11 px-5"
              busy={analysis.busy}
              disabled={
                !ready ||
                !consent ||
                input.receipts.some((item) => !item.previews?.length) ||
                input.busy
              }
            >
              {input.receipts.length > 1
                ? `Analyse ${input.receipts.length} photos together`
                : input.receipts.length === 1
                  ? 'Analyse photo'
                  : 'Analyse photos'}
            </Button>
          </fieldset>
        </div>
      </form>
      {analysis.busy && (
        <div className="flex flex-wrap items-center gap-3 border-t border-line pt-4">
          <p role="status" className="text-sm">
            Comparing visual clues, possible locations and contradictions across your evidence…
          </p>
          <Button variant="secondary" onClick={() => analysis.clear('cancelled')}>
            Cancel analysis
          </Button>
        </div>
      )}
      {analysis.status === 'cancelled' && (
        <p role="status" className="text-sm text-muted">
          Analysis cancelled. A request already received by the model provider may still be charged.
        </p>
      )}
      {analysis.error && <Alert tone="error">{analysis.error}</Alert>}
      {result && (
        <>
          <PhotoGeolocationResult result={result} />
          <div className="flex flex-wrap items-start gap-4 border-t border-line pt-5">
            <Button onClick={save} busy={report.busy} disabled={!ready}>
              Create saved report
            </Button>
            <p className="max-w-md text-xs leading-relaxed text-muted">
              Save to {workspaceLabel}. The report preserves selected extracted text and visual
              findings from the whole set, including uncertainty. Photos are not stored in the
              report.
            </p>
          </div>
        </>
      )}
      {report.error && <Alert tone="error">{describeError(report.error)}</Alert>}
      <ResearchProgress
        snapshot={report.progress.snapshot}
        active={report.progress.active}
        onCancel={report.progress.cancel}
        onRetry={() => void report.retry()}
      />
    </div>
  );
}
