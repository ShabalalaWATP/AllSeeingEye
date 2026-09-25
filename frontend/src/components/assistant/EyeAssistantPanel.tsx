import { useEffect, useEffectEvent, useId, useRef, useState } from 'react';
import type { CSSProperties, SyntheticEvent } from 'react';
import { Link } from 'react-router';
import { AiResearchNotice } from '@/components/research/AiResearchNotice';
import { researchHref, subscriptionHref } from '@/lib/researchNavigation';
import { EyeAnswer } from './EyeAnswer';
import { EyeMapControls } from './EyeMapControls';
import { EyeNewerResearchLink, EyeReportContext } from './EyeReportContext';
import { EyeSavedChats } from './EyeSavedChats';
import './eyeConversation.css';
import type { EyeChat } from './useEyeChat';

const prompts = [
  [
    'Recent activity',
    'What are the most significant recent observations in the available map sources?',
  ],
  ['Source coverage', 'Which map sources have useful recent coverage, and where are the gaps?'],
] as const;

export function EyeAssistantPanel({
  id,
  chat,
  onClose,
  onResetPosition,
  expanded,
  onToggleExpanded,
  style,
}: {
  id: string;
  chat: EyeChat;
  onClose: () => void;
  onResetPosition: () => void;
  expanded: boolean;
  onToggleExpanded: () => void;
  style: CSSProperties;
}) {
  const input = useRef<HTMLTextAreaElement>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const panel = useRef<HTMLElement>(null);
  const [savedOpen, setSavedOpen] = useState(false);
  const close = useEffectEvent(onClose);
  const inputId = useId();
  const scopeId = useId();
  const timeId = useId();
  useEffect(() => {
    input.current?.focus();
  }, []);
  useEffect(() => {
    if (typeof bottom.current?.scrollIntoView === 'function')
      bottom.current.scrollIntoView({ block: 'nearest' });
  }, [chat.turns]);
  useEffect(() => {
    const dismiss = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && panel.current?.contains(document.activeElement)) {
        event.preventDefault();
        event.stopPropagation();
        close();
      }
    };
    document.addEventListener('keydown', dismiss);
    return () => document.removeEventListener('keydown', dismiss);
  }, []);
  const submit = (event: SyntheticEvent) => {
    event.preventDefault();
    void chat.send();
  };
  const answered = [...chat.turns].reverse().find((turn) => turn.status === 'answered');
  const draft = chat.question.trim();
  const lastQuestion = draft.length ? draft : (answered?.question ?? chat.turns.at(-1)?.question);
  const interpretation = draft ? null : answered?.answer?.interpretation;
  const country = interpretation?.countries.length === 1 ? interpretation.countries[0] : null;
  const subscriptionCountry =
    answered?.answer?.interpretation.countries.length === 1
      ? answered.answer.interpretation.countries[0]
      : null;
  const timeRange =
    interpretation?.since && interpretation.until
      ? { since: interpretation.since, until: interpretation.until }
      : null;
  return (
    <section
      ref={panel}
      id={id}
      role="dialog"
      aria-label="Eye assistant"
      aria-modal="false"
      className="eye-assistant-panel"
      data-expanded={expanded}
      style={style}
    >
      <header className="eye-assistant-heading">
        <img src="/brand/eye-512.png" alt="" aria-hidden="true" width="42" height="30" />
        <div>
          <h2>The Eye</h2>
          <p>{chat.report ? 'Ask this report edition' : 'Ask your map sources'}</p>
        </div>
        <div className="eye-window-actions">
          <button
            type="button"
            className="eye-size-action"
            aria-label={expanded ? 'Restore compact chat' : 'Expand chat'}
            title={expanded ? 'Restore compact chat' : 'Expand chat'}
            aria-pressed={expanded}
            onClick={onToggleExpanded}
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path
                d={
                  expanded
                    ? 'M8 3v5H3m13-5v5h5M3 16h5v5m13-5h-5v5'
                    : 'M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5'
                }
              />
            </svg>
            <span>{expanded ? 'Restore' : 'Expand'}</span>
          </button>
          <button
            type="button"
            className="eye-icon-action"
            aria-label="Minimise chat window"
            title="Minimise chat window"
            onClick={onClose}
          >
            −
          </button>
        </div>
      </header>
      <div className="eye-assistant-tools">
        <button
          type="button"
          onClick={() => {
            chat.clear();
            setSavedOpen(false);
          }}
          disabled={chat.turns.length === 0 && !chat.question}
        >
          New chat
        </button>
        <button type="button" onClick={onResetPosition}>
          Reset position
        </button>
        <button
          type="button"
          aria-expanded={savedOpen}
          onClick={() => setSavedOpen((previous) => !previous)}
        >
          Saved chats
        </button>
        <span>Private</span>
      </div>
      {savedOpen && (
        <EyeSavedChats
          chat={chat}
          onResume={() => {
            setSavedOpen(false);
            input.current?.focus();
          }}
        />
      )}
      <AiResearchNotice className="eye-setup-note" linkClassName="" onNavigate={onClose} />
      {chat.report && <EyeReportContext report={chat.report} onMapChat={chat.clear} />}
      {chat.savedSnapshotNotice && <p className="eye-snapshot-note">{chat.savedSnapshotNotice}</p>}
      <div className="eye-transcript" role="log" aria-live="polite" aria-label="Eye conversation">
        {chat.turns.length === 0 && (
          <div className="eye-welcome">
            <h3>{chat.report ? 'What does this edition say?' : 'What would you like to know?'}</h3>
            <p>
              {chat.report
                ? 'Ask about a claim, uncertainty or source in this saved version. The answer may say this edition does not address your question.'
                : 'Search across retained map feeds, even when their layers are switched off. Answers include sources, timestamps and coverage limits.'}
            </p>
            {!chat.report && (
              <div className="eye-suggestions">
                {prompts.map(([label, question]) => (
                  <button
                    type="button"
                    key={label}
                    onClick={() => {
                      chat.setQuestion(question);
                      input.current?.focus();
                    }}
                  >
                    {label}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
        {chat.turns.map((turn) => (
          <article key={turn.id} className="eye-turn">
            <p className="eye-question">
              <span className="sr-only">You: </span>
              {turn.question}
            </p>
            {turn.saved && <p className="eye-turn-snapshot">Saved answer · recheck before use</p>}
            {turn.answer && <EyeAnswer answer={turn.answer} />}
            {turn.status === 'pending' && (
              <div role="status">
                <p className="eye-pending">
                  <span aria-hidden="true" />
                  Searching sources and preparing a reply…
                </p>
                <p className="eye-answer-meta">
                  May take up to two minutes. You can draft the next question or stop this one.
                </p>
              </div>
            )}
            {turn.status === 'stopped' && (
              <p className="eye-answer-meta">Stopped. No answer was added.</p>
            )}
            {turn.status === 'failed' && (
              <p className="eye-answer-meta">This question could not be answered.</p>
            )}
          </article>
        ))}
        <div ref={bottom} />
      </div>
      <form className="eye-composer" onSubmit={submit} noValidate>
        {chat.scope !== 'report' && (
          <EyeMapControls chat={chat} scopeId={scopeId} timeId={timeId} />
        )}
        <label className="sr-only" htmlFor={inputId}>
          Ask the Eye
        </label>
        <textarea
          id={inputId}
          ref={input}
          value={chat.question}
          maxLength={2000}
          rows={2}
          onChange={(event) => chat.setQuestion(event.target.value)}
          placeholder={
            chat.report ? 'Ask about this report edition…' : 'Ask about events, places or sources…'
          }
          onKeyDown={(event) => {
            if (
              event.key === 'Enter' &&
              !chat.busy &&
              !event.shiftKey &&
              !event.nativeEvent.isComposing
            ) {
              event.preventDefault();
              void chat.send();
            }
          }}
        />
        {chat.error && (
          <p className="eye-error" role="alert">
            {chat.error}
          </p>
        )}
        <div className="eye-composer-actions">
          <span>Enter to send · Shift + Enter for a new line</span>
          {chat.busy ? (
            <button type="button" className="eye-send" onClick={chat.stop}>
              Stop
            </button>
          ) : (
            <button type="submit" className="eye-send" disabled={!chat.question.trim()}>
              Ask Eye <span aria-hidden="true">↑</span>
            </button>
          )}
        </div>
        {chat.report ? (
          <EyeNewerResearchLink
            question={lastQuestion ?? `Find newer evidence about ${chat.report.title}`}
            report={chat.report}
            onNavigate={onClose}
          />
        ) : (
          <div className="eye-research-link">
            <Link
              to={researchHref(
                lastQuestion ?? 'Investigate the available evidence and its limitations.',
                country,
                timeRange,
              )}
              onClick={onClose}
            >
              Search deeper in Research →
            </Link>
            <span>Opens a reviewable research draft. Refine its scope and sources there.</span>
            {answered?.answer && (
              <Link to={subscriptionHref(answered.question, subscriptionCountry)} onClick={onClose}>
                Create subscription draft →
              </Link>
            )}
          </div>
        )}
      </form>
    </section>
  );
}
