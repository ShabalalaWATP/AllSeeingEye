import { memo, useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import type { AssistantAnswer } from '@/lib/api/assistant';
import { SourceLink } from '@/components/ui/SourceLink';
import { locateAssistantSource } from '@/lib/assistantMapContext';
import { formatUtc } from '@/lib/format';
import { isHttpUrl } from '@/lib/urls';

function referenceUrl(value: string | null): string | null {
  if (!isHttpUrl(value)) return null;
  const url = new URL(value);
  if (url.username || url.password) return null;
  for (const char of value) if (char.charCodeAt(0) <= 32 || char.charCodeAt(0) === 127) return null;
  return value;
}

export function answerWithReferences(answer: AssistantAnswer): string {
  const paragraphs = answer.paragraphs.map((paragraph) => {
    const citations = paragraph.citations.length ? ` [${paragraph.citations.join(', ')}]` : '';
    const prefix =
      paragraph.kind === 'finding'
        ? ''
        : `${paragraph.kind === 'inference' ? 'Assessment' : 'Coverage gap'}: `;
    return `${prefix}${paragraph.text}${citations}`;
  });
  const references = answer.sources.map((source) => {
    const url = referenceUrl(source.url);
    return `[${source.id}] ${source.title} · ${source.source_id}${url ? ` · ${url}` : ''}`;
  });
  return (references.length ? [...paragraphs, 'References', ...references] : paragraphs).join('\n\n');
}

export const EyeAnswer = memo(function EyeAnswer({ answer }: { answer: AssistantAnswer }) {
  const navigate = useNavigate();
  const [copied, setCopied] = useState<'idle' | 'success' | 'failed'>('idle');
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [focusedSource, setFocusedSource] = useState<string | null>(null);
  const sourceRefs = useRef<Record<string, HTMLDivElement | null>>({});
  // Hot reload can retain a response parsed before interpretation was added to the contract.
  const interpretation = (answer as Partial<AssistantAnswer>).interpretation ?? {
    countries: [],
    topics: [],
    since: null,
    until: null,
    notes: [],
    source_categories: [],
  };
  const matched = answer.coverage.matched_count;
  const matchSummary = Number.isFinite(matched)
    ? `${matched.toLocaleString('en-GB')} matched the question.`
    : 'Matched count unavailable.';
  const showEvidence = (id: string) => {
    setEvidenceOpen(true);
    setFocusedSource(id);
    requestAnimationFrame(() => {
      const element = sourceRefs.current[id];
      if (element && typeof element.scrollIntoView === 'function')
        element.scrollIntoView({ block: 'nearest' });
    });
  };
  const copy = async () => {
    try {
      if (!('clipboard' in navigator)) throw new Error('Clipboard unavailable');
      await navigator.clipboard.writeText(answerWithReferences(answer));
      setCopied('success');
    } catch {
      setCopied('failed');
    }
  };
  return (
    <div className="eye-answer">
      <h3>Answer</h3>
      <div className="eye-answer-scope" aria-label="Search interpretation">
        <span>
          {answer.scope.mode === 'viewport'
            ? 'Area: map view'
            : answer.scope.mode === 'selected'
              ? 'Area: selected item'
              : 'Area: all available'}
        </span>
        {interpretation.countries.length > 0 && (
          <span>Countries: {interpretation.countries.join(', ')}</span>
        )}
        {interpretation.topics.length > 0 && (
          <span>Topics: {interpretation.topics.join(', ')}</span>
        )}
        {interpretation.source_categories.length > 0 && (
          <span>
            Sources:{' '}
            {interpretation.source_categories.length <= 3
              ? interpretation.source_categories.join(', ')
              : `${interpretation.source_categories.length} types`}
          </span>
        )}
        {interpretation.since && (
          <span>
            Published: {formatUtc(interpretation.since)}
            {interpretation.until && ` to ${formatUtc(interpretation.until)}`}
          </span>
        )}
      </div>
      {answer.paragraphs.map((paragraph, index) => (
        <section key={index} className="eye-paragraph" data-kind={paragraph.kind}>
          {paragraph.kind !== 'finding' && (
            <span className="eye-answer-label">
              {paragraph.kind === 'inference' ? 'Assessment' : 'Coverage gap'}
            </span>
          )}
          <p>{paragraph.text}</p>
          {paragraph.citations.length > 0 && (
            <div className="eye-citations" aria-label="Supporting records">
              {paragraph.citations.map((id) => {
                const source = answer.sources.find((item) => item.id === id);
                return source ? (
                  <button
                    key={id}
                    type="button"
                    title={source.title}
                    aria-label={`View evidence ${id}: ${source.title}`}
                    onClick={() => showEvidence(id)}
                  >
                    [{id}] {source.title}
                  </button>
                ) : null;
              })}
            </div>
          )}
        </section>
      ))}
      <div className="eye-answer-actions">
        <button type="button" onClick={() => void copy()}>
          Copy answer with references
        </button>
        {copied !== 'idle' && (
          <span role="status">
            {copied === 'success' ? 'Copied with references.' : 'Clipboard unavailable.'}
          </span>
        )}
      </div>
      <details
        className="eye-source-details"
        open={evidenceOpen}
        onToggle={(event) => setEvidenceOpen(event.currentTarget.open)}
      >
        <summary>
          Evidence and coverage{' '}
          <span>
            {answer.coverage.selected_count}{' '}
            {answer.coverage.selected_count === 1 ? 'record' : 'records'} ·{' '}
            {answer.coverage.source_count}{' '}
            {answer.coverage.source_count === 1 ? 'source group' : 'source groups'}
          </span>
        </summary>
        <div className="eye-coverage">
          <p>
            {answer.coverage.candidate_count.toLocaleString('en-GB')} candidates checked;{' '}
            {matchSummary}{' '}
            {answer.coverage.capped
              ? 'The answer uses a bounded sample.'
              : 'Coverage reflects records currently available to the app.'}
          </p>
          {answer.coverage.notes.map((note, index) => (
            <p key={index}>{note}</p>
          ))}
          {interpretation.notes.map((note, index) => (
            <p key={`scope-${index}`}>{note}</p>
          ))}
          {interpretation.source_categories.length > 3 && (
            <p>Source types searched: {interpretation.source_categories.join(', ')}</p>
          )}
          {answer.sources.map((source) => (
            <div
              className="eye-source"
              key={source.id}
              ref={(node) => {
                sourceRefs.current[source.id] = node;
              }}
              data-focused={focusedSource === source.id}
            >
              <strong>
                [{source.id}] {source.title}
              </strong>
              <span>
                {source.source_id}
                {source.grade ? ` · Source grade ${source.grade}` : ''}
              </span>
              <span>
                {source.published_at ? (
                  <>
                    Published{' '}
                    <time dateTime={source.published_at}>{formatUtc(source.published_at)}</time>
                  </>
                ) : (
                  'Publication time unknown'
                )}
              </span>
              {source.observed_at && (
                <span>
                  Observed{' '}
                  <time dateTime={source.observed_at}>{formatUtc(source.observed_at)}</time>
                </span>
              )}
              <div className="eye-source-actions">
                <SourceLink url={source.url}>Open original</SourceLink>
                {source.point && (
                  <button
                    type="button"
                    onClick={() => {
                      if (!source.point) return;
                      locateAssistantSource({
                        kind: source.kind,
                        id: source.record_id,
                        point: source.point,
                      });
                      void navigate('/');
                    }}
                  >
                    Show on map
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </details>
      <p className="eye-answer-meta">
        Prepared <time dateTime={answer.generated_at}>{formatUtc(answer.generated_at)}</time>
      </p>
    </div>
  );
});
