import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { describeError } from '@/lib/api/errors';
import { createBrief, reviseBrief } from '@/lib/api/researchBriefs';
import type { BriefDraft, ResearchBrief } from '@/lib/api/researchBriefSchema';
import { briefCanRun, draftFromBrief } from '@/lib/researchBriefDraft';

import { BriefOptionsEditor } from './BriefOptionsEditor';
import { BriefPreflight } from './BriefPreflight';
import { BriefQuestionEditor } from './BriefQuestionEditor';
import { BriefScopeEditor } from './BriefScopeEditor';
import { BriefSubscriptionActions } from './BriefSubscriptionActions';
import { PresetPicker } from './PresetPicker';
import { BriefJourney, BriefRunSummary, BRIEF_STEPS, type BriefStep } from './BriefJourney';
import { BriefPerspectiveEditor } from './BriefPerspectiveEditor';
import { ResearchDepth } from './ResearchDepth';
import { useBriefJourney } from './useBriefJourney';
import { useBriefRun } from './useBriefRun';

export interface InitialBrief {
  brief: ResearchBrief | null;
  draft: BriefDraft;
  copy: boolean;
  mapTitle: string | null;
}
export function BriefEditor({
  initial,
  fromReportId,
  fromReportVersion,
  intent,
  initialStep,
  onSaved,
}: {
  initial: InitialBrief;
  fromReportId?: string | undefined;
  fromReportVersion?: number | undefined;
  intent?: 'subscribe' | undefined;
  initialStep?: BriefStep | undefined;
  onSaved: (brief: ResearchBrief) => void;
}) {
  const [draft, setDraft] = useState(() => structuredClone(initial.draft));
  const currentDraft = useRef(draft);
  useEffect(() => {
    currentDraft.current = draft;
  }, [draft]);
  const [saved, setSaved] = useState(initial.copy ? null : initial.brief);
  const [baseline, setBaseline] = useState(() => structuredClone(initial.draft));
  const [saving, setBusy] = useState(false);
  const execution = useBriefRun(saved);
  const busy = saving || execution.busy;
  const [saveProblem, setProblem] = useState<string | null>(null);
  const problem = saveProblem ?? execution.error;
  const [notice, setNotice] = useState<string | null>(null);
  const jobId = execution.jobId;
  const [showPresets, setShowPresets] = useState(false);
  const { step, setStep, root, heading, errorSummary, validate, reviewField } = useBriefJourney(
    draft,
    initialStep ?? (intent === 'subscribe' ? 'run' : 'brief'),
    problem,
    setProblem,
  );
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  const dirty = useMemo(
    () => JSON.stringify(draft) !== JSON.stringify(baseline),
    [draft, baseline],
  );
  const runReason = briefCanRun(draft);
  const stepIndex = BRIEF_STEPS.findIndex((entry) => entry.id === step);
  const previous = BRIEF_STEPS[stepIndex - 1];
  const next = BRIEF_STEPS[stepIndex + 1];
  const save = async () => {
    if (busy || controller.current || !validate()) return;
    setBusy(true);
    setProblem(null);
    setNotice(null);
    const pending = new AbortController();
    controller.current = pending;
    try {
      const result = saved
        ? await reviseBrief(saved, draft, pending.signal)
        : await createBrief(draft, pending.signal);
      if (pending.signal.aborted) return;
      setSaved(result);
      const canonical = draftFromBrief(result);
      setDraft(canonical);
      setBaseline(structuredClone(canonical));
      setNotice(`Saved revision ${result.identity.revision}.`);
      setStep('run');
      onSaved(result);
    } catch (caught) {
      if (!pending.signal.aborted) setProblem(describeError(caught));
    } finally {
      if (!pending.signal.aborted) setBusy(false);
      if (controller.current === pending) controller.current = null;
    }
  };
  const run = async () => {
    if (!saved || dirty || busy || controller.current || runReason || !validate()) return;
    setProblem(null);
    setNotice(null);
    const job = await execution.run();
    if (job) setNotice(`Research started from brief revision ${saved.identity.revision}.`);
  };
  const cancel = () => {
    if (busy) return;
    setDraft(structuredClone(baseline));
    setProblem(null);
    setNotice('Unsaved changes discarded.');
  };
  return (
    <section
      ref={root}
      className="min-w-0 space-y-5 border-t border-line pt-5"
      aria-label="Research Brief editor"
    >
      <header>
        <h2 className="text-xl font-semibold">
          {initial.copy ? 'Use this brief' : saved ? 'Edit Research Brief' : 'New Research Brief'}
        </h2>
        {fromReportId && fromReportVersion && (
          <p className="mt-2 text-sm text-muted">
            Based on selected report {fromReportId}, version {fromReportVersion}. Choose a future
            period before subscribing.
          </p>
        )}
        {initial.mapTitle && (
          <p className="mt-2 text-sm text-muted">From saved map: {initial.mapTitle}.</p>
        )}
        {saved && (
          <p className="mt-2 text-sm text-muted">
            Exact saved revision {saved.identity.revision}. Changes require a new revision before
            running or subscribing.
          </p>
        )}
      </header>
      <BriefJourney step={step} change={setStep} busy={busy} headingRef={heading} />
      <fieldset disabled={busy} className="min-w-0 disabled:opacity-70">
        <div
          id="brief-stage-brief"
          data-brief-stage="brief"
          hidden={step !== 'brief'}
          className="min-w-0 space-y-5"
        >
          <Link
            to="/research?brief=library"
            className="inline-flex min-h-10 items-center text-sm text-ember underline"
          >
            Choose a saved brief
          </Link>
          {!initial.copy &&
            !initial.brief &&
            (showPresets ? (
              <PresetPicker
                draft={draft}
                onApply={(next) => {
                  if (currentDraft.current !== draft) {
                    setProblem(
                      'The draft changed while the preset was loading. Your edits are preserved; review the preset before applying it again.',
                    );
                    return false;
                  }
                  setDraft(next);
                  setProblem(null);
                  return true;
                }}
              />
            ) : (
              <Button variant="secondary" onClick={() => setShowPresets(true)}>
                Browse presets
              </Button>
            ))}
          <div data-brief-fields>
            <BriefQuestionEditor draft={draft} change={setDraft} />
          </div>
        </div>
        <div
          id="brief-stage-scope"
          data-brief-stage="scope"
          data-brief-fields
          hidden={step !== 'scope'}
          className="min-w-0 space-y-6"
        >
          <BriefScopeEditor draft={draft} change={setDraft} />
          <BriefPerspectiveEditor draft={draft} change={setDraft} />
        </div>
        <div
          id="brief-stage-depth"
          data-brief-stage="depth"
          data-brief-fields
          hidden={step !== 'depth'}
          className="min-w-0 space-y-5"
        >
          <ResearchDepth
            value={draft.output.depth}
            onChange={(depth) => setDraft({ ...draft, output: { ...draft.output, depth } })}
          />
          <p className="text-sm text-muted">
            {draft.question.requirements.filter((row) => row.required).length} required questions
            selected. Nothing is removed when you change depth.
          </p>
          <details className="border-t border-line pt-4">
            <summary className="cursor-pointer font-medium">
              Advanced sources, limits and monitoring
            </summary>
            <div className="mt-4">
              <BriefOptionsEditor draft={draft} change={setDraft} />
            </div>
          </details>
          <BriefPreflight brief={saved} dirty={dirty} editorBusy={busy} />
        </div>
        <div
          id="brief-stage-run"
          data-brief-stage="run"
          hidden={step !== 'run'}
          className="min-w-0 space-y-5"
        >
          <BriefRunSummary draft={draft} />
        </div>
      </fieldset>
      {problem && (
        <div ref={errorSummary} tabIndex={-1} className="outline-offset-4">
          <Alert tone="error" title="Review this brief">
            {problem}
            <Button variant="ghost" onClick={reviewField}>
              Review field
            </Button>
          </Alert>
        </div>
      )}
      {notice && (
        <p role="status" className="text-sm text-ember">
          {notice}
        </p>
      )}
      {jobId && (
        <Link className="text-sm text-text underline" to={`/research/jobs/${jobId}`}>
          Open research job
        </Link>
      )}
      <div className="flex flex-wrap gap-2 border-t border-line pt-4">
        {previous && (
          <Button variant="ghost" disabled={busy} onClick={() => setStep(previous.id)}>
            Back
          </Button>
        )}
        {next && (
          <Button disabled={busy} onClick={() => setStep(next.id)}>
            Continue to {next.label}
          </Button>
        )}
        <Button
          variant="secondary"
          onClick={() => void save()}
          busy={busy}
          disabled={!dirty && !!saved}
        >
          Save brief
        </Button>
        {step === 'run' && (
          <Button onClick={() => void run()} disabled={!saved || dirty || !!runReason || busy}>
            {execution.error ? 'Retry research run' : 'Run once'}
          </Button>
        )}
        <Button variant="ghost" onClick={cancel} disabled={!dirty || busy}>
          Cancel changes
        </Button>
      </div>
      <div hidden={step !== 'run'}>
        <BriefSubscriptionActions
          brief={saved}
          draft={draft}
          dirty={dirty}
          editorBusy={busy}
          initialOpen={intent === 'subscribe'}
        />
      </div>
      {dirty && saved && (
        <p className="text-xs text-muted">
          Save a new revision to run or subscribe with these edits.
        </p>
      )}
      {runReason && (
        <p className="text-xs text-muted">
          Run unavailable: {runReason}{' '}
          <Link to="/research" className="underline">
            Open Research
          </Link>
        </p>
      )}
    </section>
  );
}
