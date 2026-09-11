import { useEffect, useEffectEvent, useId, useRef } from 'react';
import type { CSSProperties, SyntheticEvent } from 'react';
import { Link } from 'react-router';
import { useAssistantMapAvailability } from '@/lib/assistantMapContext';
import { researchHref } from '@/lib/researchNavigation';
import { EyeAnswer } from './EyeAnswer';
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
  style,
}: {
  id: string;
  chat: EyeChat;
  onClose: () => void;
  onResetPosition: () => void;
  style: CSSProperties;
}) {
  const map = useAssistantMapAvailability();
  const input = useRef<HTMLTextAreaElement>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const panel = useRef<HTMLElement>(null);
  const close = useEffectEvent(onClose);
  const inputId = useId();
  const scopeId = useId();
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
  const lastQuestion = chat.turns.at(-1)?.question ?? chat.question;
  return (
    <section
      ref={panel}
      id={id}
      role="dialog"
      aria-label="Eye assistant"
      aria-modal="false"
      className="eye-assistant-panel"
      style={style}
    >
      <header className="eye-assistant-heading">
        <img src="/brand/eye-512.png" alt="" aria-hidden="true" width="42" height="30" />
        <div>
          <h2>The Eye</h2>
          <p>Ask your map sources</p>
        </div>
        <button
          type="button"
          className="eye-icon-action"
          aria-label="Close Eye assistant"
          onClick={onClose}
        >
          ×
        </button>
      </header>
      <div className="eye-assistant-tools">
        <button
          type="button"
          onClick={chat.clear}
          disabled={chat.turns.length === 0 && !chat.question}
        >
          New chat
        </button>
        <button type="button" onClick={onResetPosition}>
          Reset position
        </button>
        <span>Session only</span>
      </div>
      <div className="eye-transcript" role="log" aria-live="polite" aria-label="Eye conversation">
        {chat.turns.length === 0 && (
          <div className="eye-welcome">
            <h3>What would you like to know?</h3>
            <p>
              Search across retained map feeds, even when their layers are switched off. Answers
              include sources, timestamps and coverage limits.
            </p>
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
          </div>
        )}
        {chat.turns.map((turn) => (
          <article key={turn.id} className="eye-turn">
            <p className="eye-question">
              <span className="sr-only">You: </span>
              {turn.question}
            </p>
            {turn.answer && <EyeAnswer answer={turn.answer} />}
            {turn.status === 'pending' && (
              <div role="status">
                <p className="eye-pending">
                  <span aria-hidden="true" />
                  Searching sources and preparing a reply…
                </p>
                <p className="eye-answer-meta">
                  May take up to two minutes. You can stop at any time.
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
        <div className="eye-scope">
          <label htmlFor={scopeId}>Search</label>
          <select
            id={scopeId}
            aria-label="Eye search scope"
            value={chat.scope}
            disabled={chat.busy}
            onChange={(event) => {
              const value = event.target.value;
              if (value === 'global' || value === 'viewport' || value === 'selected')
                chat.setScope(value);
            }}
          >
            <option value="global">All retained map sources</option>
            <option value="viewport" disabled={!map?.bounds}>
              Current map area
            </option>
            <option value="selected" disabled={!map?.selected}>
              Selected map item
            </option>
          </select>
        </div>
        {chat.scope === 'viewport' && (
          <p className="eye-scope-note">
            Uses the current geographic view boundary, including layers switched off.
          </p>
        )}
        {chat.scope === 'selected' && (
          <p className="eye-scope-note">
            {map?.selected ? map.selected.title : 'Select an item on the map to continue.'}
          </p>
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
          disabled={chat.busy}
          onChange={(event) => chat.setQuestion(event.target.value)}
          placeholder="Ask about events, places or sources…"
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
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
        <div className="eye-research-link">
          <Link
            to={researchHref(
              lastQuestion || 'Investigate the available evidence and its limitations.',
            )}
            onClick={onClose}
          >
            Search deeper in Research →
          </Link>
          <span>Review scope before creating a report.</span>
        </div>
      </form>
    </section>
  );
}
