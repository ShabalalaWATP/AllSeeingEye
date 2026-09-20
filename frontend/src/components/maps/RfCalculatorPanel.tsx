import type { RfCalculatorPanelProps } from './rfCalculatorTypes';
import { RfStudyLibrary } from './RfStudyLibrary';
import { snapshotRfStudy } from '@/lib/map/rfStudy';
import { rfPlannerInputs } from '@/lib/map/rfPlannerInputs';
import { RfAntennaControls } from './RfAntennaControls';
import { useState } from 'react';
import { calculateRf, type RfInputs } from '@/lib/map/rfPlanning';
import { RF_PRESETS } from '@/lib/map/rfPresets';
import { rfMapEstimate } from '@/lib/map/rfMap';
import type { RfMapEstimate } from '@/lib/map/rfMap';
import { RfResults } from './RfResults';
import { RfCoverageControls } from './RfCoverageControls';
import { RfReferenceControls } from './RfReferenceControls';
import { RfRadioFields } from './RfRadioFields';
import { RfPowerInput } from './RfPowerInput';
import { RfPlannerTabs } from './RfPlannerTabs';
import { RfAnalysisAction } from './RfAnalysisAction';
import { RfPositions } from './RfPositions';
import { rfEnvironmentValid } from './RfModelControls';
import { RfReferences } from './RfReferences';
import { RfPresetControls } from './RfPresetControls';
import { useRfAnalysis } from './useRfAnalysis';
import { RfAnalysisResults } from './RfAnalysisResults';
import type { RfAnalysis } from '@/lib/map/rfAnalysis';
import { createRfDraft, type RfDraft } from '@/lib/map/rfDraft';
import { parseRfEngineering } from '@/lib/map/rfEngineering';
import { resolveRfMode } from '@/lib/map/rfAutomation';
import { useRfAutoUpdate } from './useRfAutoUpdate';
import './rfPlanner.css';
import './rfPlannerFields.css';
import './rfPlannerResults.css';

export type { RfCalculatorPanelProps } from './rfCalculatorTypes';

export function RfCalculatorPanel({
  siteNames = { origin: '', receiver: '' },
  interaction = 'click',
  onDragSite,
  onSetSite,
  onSwapSites,
  onProfilePoint,
  studyWorkspace,
  measuredDistanceKm,
  origin = null,
  receiver = null,
  picking = null,
  onPick,
  onOverlayChange,
  overlayVisible = false,
  coverageBubble,
  onCoverageBubbleChange,
  draft,
  onDraftChange,
  onClearReceiver,
  analysis,
  onAnalysisChange,
}: RfCalculatorPanelProps) {
  const [localDraft, setLocalDraft] = useState(() => createRfDraft());
  const currentDraft = draft ?? localDraft;
  const { values, presetId } = currentDraft;
  const mode = resolveRfMode(currentDraft);
  const supportsArea = mode !== 'hf-skywave';
  const target = supportsArea && currentDraft.study === 'area' ? null : receiver;
  const needsReceiver = supportsArea && currentDraft.study === 'link' && !receiver;
  const [localBubble, setLocalBubble] = useState(false);
  const [localAnalysis, setLocalAnalysis] = useState<RfAnalysis | null>(null);
  const [selectedView, setSelectedView] = useState<'configure' | 'results' | null>(null);
  const changeAnalysis = onAnalysisChange ?? setLocalAnalysis;
  const currentAnalysis = analysis === undefined ? localAnalysis : analysis;
  const setDraft = onDraftChange ?? setLocalDraft;
  const preset = RF_PRESETS.find((item) => item.id === presetId) ?? RF_PRESETS[0];
  const { input, error: antennaError } = rfPlannerInputs(currentDraft, origin, target);
  const worker = useRfAnalysis(input, currentDraft, origin, receiver, changeAnalysis);
  const update = (next: RfDraft) => {
    setSelectedView('configure');
    setDraft(next);
    onOverlayChange?.(null);
    changeAnalysis(null);
  };
  let result: ReturnType<typeof calculateRf> | null = null;
  let estimate: RfMapEstimate | null = null;
  let error: string | null = antennaError;
  let mapError: string | null = null;
  try {
    if (antennaError) throw new Error(antennaError);
    if (mode !== 'hf-skywave')
      result = calculateRf(
        mode === 'free-space' ? input : { ...input, distanceKm: 1 },
        parseRfEngineering(currentDraft.engineering, mode),
      );
    else if (
      !Number.isFinite(input.frequencyMHz) ||
      input.frequencyMHz < 1.6 ||
      input.frequencyMHz > 30
    )
      throw new Error('HF frequency: enter a value from 1.6 to 30 MHz.');
    if (origin && mode === 'free-space' && !needsReceiver) {
      try {
        estimate = rfMapEstimate(
          input,
          origin,
          target,
          parseRfEngineering(currentDraft.engineering, mode),
        );
      } catch (caught) {
        mapError = caught instanceof Error ? caught.message : 'Check the map position.';
      }
    }
  } catch (caught) {
    error = caught instanceof Error ? caught.message : 'Check the inputs.';
  }
  const change = (key: keyof RfInputs, value: string) => {
    update({
      ...currentDraft,
      values: { ...values, [key]: value },
      presetId: 'custom',
      ...(currentDraft.propagation === 'automatic' && mode === 'hf-skywave'
        ? { automaticHfMode: 'hf-skywave' as const }
        : {}),
    });
  };
  const view = currentAnalysis ? (selectedView ?? 'results') : 'configure';
  const validEnvironment = rfEnvironmentValid(currentDraft, !!receiver);
  const invalidBand = mode === 'terrain' ? input.frequencyMHz < 30 : input.frequencyMHz > 30;
  const ready =
    !!origin &&
    !needsReceiver &&
    (mode === 'hf-skywave' ? !error : !!result) &&
    validEnvironment &&
    !invalidBand &&
    !picking;
  const readiness = !origin
    ? 'Place a transmitter before analysis.'
    : needsReceiver
      ? 'Place a receiver to analyse a point-to-point link.'
      : picking
        ? 'Finish placing the site on the map.'
        : !ready
          ? 'Review the inputs before analysis.'
          : 'Ready to analyse. Settings remain editable.';
  const automation = useRfAutoUpdate({
    identity: JSON.stringify([currentDraft, origin, receiver]),
    ready: ready && mode !== 'free-space',
    busy: worker.busy,
    picking: !!picking,
    run: worker.analyse,
    cancel: worker.cancel,
  });
  return (
    <section aria-label="RF planning calculator" className="rf-planner">
      <header className="rf-planner-header">
        <div>
          <p className="rf-eyebrow">RF workspace</p>
          <h2>Radio link planner</h2>
        </div>
        <span className="rf-planner-state">
          {worker.busy ? 'Analysing' : currentAnalysis ? 'Analysed' : 'Planning'}
        </span>
      </header>
      {studyWorkspace && (
        <RfStudyLibrary
          workspace={{
            ...studyWorkspace,
            restoreStudy: (value) => {
              automation.disarm();
              studyWorkspace.restoreStudy(value);
            },
          }}
          draft={currentDraft}
          snapshot={() =>
            snapshotRfStudy(currentDraft, origin, receiver, siteNames, currentAnalysis)
          }
        />
      )}
      <RfPlannerTabs view={view} onChange={setSelectedView} hasResults={!!currentAnalysis}>
        {view === 'configure' ? (
          <>
            <div className="rf-configure-grid">
              <section className="rf-configure-section" aria-label="Radio and propagation settings">
                <h3 className="rf-section-label">Radio &amp; propagation</h3>
                <RfPowerInput
                  dbm={values.transmitDbm}
                  onChange={(value) => change('transmitDbm', value)}
                  disabled={mode === 'hf-skywave'}
                />
                <RfPresetControls currentDraft={currentDraft} update={update} />
                <RfRadioFields
                  draft={currentDraft}
                  mode={mode}
                  input={input}
                  linked={!!origin && !!target}
                  onChange={change}
                  onDraftChange={update}
                />
              </section>
              <section
                className="rf-configure-section rf-site-section"
                aria-label="Map sites and study area"
              >
                <h3 className="rf-section-label">Map sites &amp; study</h3>
                {supportsArea && (
                  <RfCoverageControls
                    draft={currentDraft}
                    hasReceiver={!!receiver}
                    onChange={(next) => {
                      onPick?.(null);
                      update(next);
                    }}
                    bubble={coverageBubble ?? localBubble}
                    onBubbleChange={onCoverageBubbleChange ?? setLocalBubble}
                    input={input}
                  />
                )}
                <RfPositions
                  interaction={interaction}
                  onDragSite={onDragSite}
                  siteNames={siteNames}
                  onSetSite={onSetSite}
                  onSwapSites={onSwapSites}
                  pathActive={target !== null}
                  origin={origin}
                  receiver={receiver}
                  picking={picking}
                  onPick={
                    onPick
                      ? (point) => {
                          if (point === 'receiver' && supportsArea)
                            update({ ...currentDraft, study: 'link' });
                          onPick(point);
                        }
                      : undefined
                  }
                  onClearReceiver={onClearReceiver}
                />
                {supportsArea && currentDraft.study === 'area' && receiver && (
                  <p className="rf-help">
                    The saved receiver is excluded from this 360° study. Switch to the receiver link
                    to use it.
                  </p>
                )}
                {mode === 'free-space' &&
                  measuredDistanceKm !== undefined &&
                  Number.isFinite(measuredDistanceKm) &&
                  measuredDistanceKm > 0 &&
                  !(origin && target) && (
                    <button
                      type="button"
                      className="rf-secondary-button"
                      onClick={() => change('distanceKm', measuredDistanceKm.toFixed(3))}
                    >
                      Use measured path ({measuredDistanceKm.toFixed(3)} km)
                    </button>
                  )}
                <RfAntennaControls draft={currentDraft} onChange={update} />
                <RfReferences preset={preset} />
              </section>
            </div>
            {error && (
              <p role="alert" className="rf-notice rf-notice-warning">
                {error}
              </p>
            )}
            {mode === 'free-space' && result && <RfResults result={result} />}
            {mode !== 'free-space' && (
              <RfAnalysisAction
                mode={mode}
                frequencyMHz={input.frequencyMHz}
                validEnvironment={validEnvironment}
                ready={ready}
                readiness={readiness}
                busy={worker.busy}
                error={worker.error}
                progress={worker.progress}
                automation={automation}
                onAnalyse={() => {
                  setSelectedView(null);
                  automation.manuallyAnalyse();
                }}
              />
            )}
            {onOverlayChange && mode === 'free-space' && (
              <RfReferenceControls
                originPlaced={!!origin}
                estimate={estimate}
                error={mapError}
                visible={overlayVisible}
                onChange={(value) => {
                  if (!value) automation.disarm();
                  onOverlayChange(value);
                }}
              />
            )}
          </>
        ) : (
          currentAnalysis && (
            <div className="rf-completed-results">
              <p className="rf-result-intro" aria-live="polite">
                Analysis complete. Review the path, limits and source quality below.
              </p>
              <RfAnalysisResults
                onProfilePoint={onProfilePoint}
                analysis={currentAnalysis}
                bubble={coverageBubble ?? localBubble}
              />
              <div className="rf-result-actions">
                <button
                  type="button"
                  className="rf-secondary-button"
                  onClick={() => setSelectedView('configure')}
                >
                  Edit study
                </button>
                <button
                  type="button"
                  className="rf-text-button"
                  onClick={() => {
                    automation.disarm();
                    changeAnalysis(null);
                    setSelectedView('configure');
                  }}
                >
                  Clear analysis
                </button>
              </div>
              <RfReferences preset={preset} />
            </div>
          )
        )}
      </RfPlannerTabs>
    </section>
  );
}
