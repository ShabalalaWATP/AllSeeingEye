import { useEffect, useId, useRef } from 'react';
import type { SyntheticEvent } from 'react';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { ModelSetupAudience } from './ModelSetupAudience';
import { ModelSetupKey, ModelSetupName, ModelSetupReasoning } from './ModelSetupFields';
import { ModelSetupModel } from './ModelSetupModel';
import { useModelSetupState } from './ModelSetupState';
import { MODEL_SETUP_MAX_TARGETS, MODEL_SETUP_STEPS } from './ModelSetupTypes';
import type { ModelSetupProps } from './ModelSetupTypes';

export type { ModelSetupAudience, ModelSetupProps } from './ModelSetupTypes';

const TITLES = [
  'Name your connection',
  'Connect your account',
  'Choose your model',
  'Choose a reasoning level',
  'Test your connection',
  'Who should use this model?',
];

function trapFocus(event: KeyboardEvent, modal: HTMLDialogElement, heading: HTMLElement | null) {
  if (event.key !== 'Tab') return;
  const controls = [...modal.querySelectorAll<HTMLElement>('*')].filter(
    (element) =>
      element.matches(
        'button:not(:disabled), input:not(:disabled), select:not(:disabled), summary, [tabindex="0"]',
      ) &&
      (!element.closest('details:not([open])') || element.tagName === 'SUMMARY'),
  );
  const first = controls[0];
  const last = controls.at(-1);
  if (event.shiftKey && (document.activeElement === first || document.activeElement === heading)) {
    event.preventDefault();
    last?.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first?.focus();
  }
}

/** Native modal keeps setup focused; the current tested revision is the only assignable profile. */
export function ModelSetupWizard(props: ModelSetupProps) {
  const state = useModelSetupState(props);
  const dialog = useRef<HTMLDialogElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const titleId = useId();
  const stepId = useId();
  useEffect(() => {
    const opener = document.activeElement;
    const modal = dialog.current;
    const keydown = (event: KeyboardEvent) => {
      if (modal) trapFocus(event, modal, heading.current);
    };
    modal?.addEventListener('keydown', keydown);
    modal?.showModal();
    return () => {
      modal?.removeEventListener('keydown', keydown);
      modal?.close();
      if (opener instanceof HTMLElement && opener.isConnected) opener.focus();
    };
  }, []);
  useEffect(() => {
    heading.current?.focus();
  }, [state.step]);
  const duplicate = props.profiles.some(
    (profile) => profile.id !== state.draft?.id && profile.name === state.fields.name.trim(),
  );
  const hasDefault = props.connections.some(
    (connection) => !connection.team_id && !connection.user_id,
  );
  const valid =
    state.step === 0
      ? !!state.fields.name.trim() && !!state.fields.baseUrl.trim() && !duplicate
      : state.step === 1
        ? state.fields.provider === 'custom' || state.storedKey || !!state.fields.apiKey.trim()
        : state.step === 2
          ? !!state.fields.model.trim()
          : state.step === 5
            ? !!state.tested &&
              (state.audience.scope === 'global' ||
                (hasDefault &&
                  state.audience.targetIds.length > 0 &&
                  state.audience.targetIds.length <= MODEL_SETUP_MAX_TARGETS))
            : true;
  const next = (event: SyntheticEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (state.busy || !valid) return;
    if (state.step === 4 && !state.tested) void state.test();
    else if (state.step === 5) void state.apply();
    else state.setStep(state.step + 1);
  };
  return (
    <dialog
      ref={dialog}
      aria-labelledby={titleId}
      aria-describedby={stepId}
      onCancel={(event) => {
        event.preventDefault();
        if (!state.busy) props.onClose();
      }}
      className="m-auto w-[min(42rem,calc(100vw-2rem))] max-w-none overflow-hidden rounded-2xl border border-line bg-ground p-0 text-text shadow-2xl backdrop:bg-black/75"
    >
      <form
        onSubmit={next}
        className="flex max-h-[calc(100dvh-2rem)] min-h-[min(30rem,calc(100dvh-2rem))] flex-col"
      >
        <header className="shrink-0 border-b border-line px-5 pt-5 pb-4 sm:px-7">
          <div className="flex items-center justify-between gap-3">
            <h2 id={titleId} className="text-sm font-semibold">
              {props.initial ? 'Finish model setup' : 'New model connection'}
            </h2>
            <Button
              variant="ghost"
              aria-label="Close model setup"
              disabled={!!state.busy}
              onClick={props.onClose}
            >
              ×
            </Button>
          </div>
          <ol aria-label="Setup progress" className="mt-4 grid grid-cols-6 gap-2">
            {MODEL_SETUP_STEPS.map((label, index) => (
              <li
                key={label}
                aria-current={state.step === index ? 'step' : undefined}
                className={`border-t-2 pt-2 text-2xs sm:text-xs ${index <= state.step ? 'border-ember text-text' : 'border-line text-muted'}`}
              >
                <span className="font-mono">{index + 1}</span>
                <span className="ml-1 hidden sm:inline">{label}</span>
              </li>
            ))}
          </ol>
        </header>
        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-6 sm:px-7">
          <p id={stepId} className="text-xs text-muted">
            Step {state.step + 1} of 6 · {MODEL_SETUP_STEPS[state.step]}
          </p>
          <h3
            ref={heading}
            tabIndex={-1}
            className="mt-2 mb-6 text-xl font-semibold tracking-tight"
          >
            {TITLES[state.step]}
          </h3>
          <fieldset disabled={!!state.busy} className="space-y-5">
            {state.step === 0 && <ModelSetupName state={state} duplicate={duplicate} />}
            {state.step === 1 && <ModelSetupKey state={state} />}
            {state.step === 2 && <ModelSetupModel state={state} />}
            {state.step === 3 && <ModelSetupReasoning state={state} />}
            {state.step === 4 && (
              <div className="space-y-5">
                <dl className="grid grid-cols-[auto_1fr] gap-x-5 gap-y-3 text-sm">
                  <dt className="text-muted">Connection</dt>
                  <dd className="break-words font-medium">{state.fields.name}</dd>
                  <dt className="text-muted">Model</dt>
                  <dd className="break-all font-mono">{state.fields.model}</dd>
                  <dt className="text-muted">Reasoning</dt>
                  <dd className="capitalize">{state.fields.effort || 'Provider default'}</dd>
                </dl>
                <p className="break-all text-xs text-muted">{state.fields.baseUrl}</p>
                {state.busy && (
                  <p
                    role="status"
                    className="rounded-lg border border-ember/30 bg-ember/5 p-4 text-sm"
                  >
                    {state.busy === 'save'
                      ? 'Saving the encrypted connection draft…'
                      : 'Checking this model and reasoning level with your provider…'}
                  </p>
                )}
                {state.tested ? (
                  <p
                    role="status"
                    className="rounded-lg border border-good/30 bg-good/5 p-4 text-sm"
                  >
                    Connection test passed{state.testMs !== null ? ` in ${state.testMs} ms` : ''}.
                    Choose an audience to finish.
                  </p>
                ) : (
                  <p className="text-sm leading-6 text-muted">
                    This saves a draft and sends a short compatibility request. Provider usage
                    charges may apply. Your active connections stay unchanged.
                  </p>
                )}
              </div>
            )}
            {state.step === 5 && (
              <>
                <p className="text-sm">
                  <strong>{state.fields.name}</strong>
                  <span className="ml-2 text-xs text-muted">
                    {state.fields.model} · {state.fields.effort || 'Provider default'}
                  </span>
                </p>
                <ModelSetupAudience
                  value={state.audience}
                  onChange={state.setAudience}
                  teams={props.teams}
                  users={props.users}
                  connections={props.connections}
                />
              </>
            )}
          </fieldset>
          {state.error && (
            <div className="mt-5">
              <Alert tone="error">{state.error}</Alert>
            </div>
          )}
        </div>
        <footer className="shrink-0 border-t border-line bg-surface px-5 py-4 sm:px-7">
          {state.draft && (
            <p className="mb-3 text-xs text-muted">
              A draft is saved. Closing keeps it available to finish later.
            </p>
          )}
          <div className="flex items-center justify-between gap-3">
            <Button
              variant="ghost"
              disabled={!!state.busy}
              onClick={() => (state.step > 0 ? state.setStep(state.step - 1) : props.onClose())}
            >
              {state.step > 0 ? 'Back' : 'Cancel'}
            </Button>
            <div className="flex gap-2">
              {state.step === 4 && state.tested && (
                <Button variant="ghost" disabled={!!state.busy} onClick={() => void state.test()}>
                  Test again
                </Button>
              )}
              <Button type="submit" busy={!!state.busy} disabled={!valid}>
                {state.busy
                  ? state.busy === 'apply'
                    ? 'Saving assignment…'
                    : 'Testing connection…'
                  : state.step === 5
                    ? 'Save and close'
                    : state.step === 4
                      ? state.tested
                        ? 'Choose audience'
                        : 'Test connection'
                      : 'Continue'}
              </Button>
            </div>
          </div>
        </footer>
      </form>
    </dialog>
  );
}
