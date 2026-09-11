import { useNavigate } from 'react-router';
import { memo } from 'react';
import type { AssistantAnswer } from '@/lib/api/assistant';
import { SourceLink } from '@/components/ui/SourceLink';
import { locateAssistantPoint } from '@/lib/assistantMapContext';
import { formatUtc } from '@/lib/format';

export const EyeAnswer = memo(function EyeAnswer({ answer }: { answer: AssistantAnswer }) {
  const navigate = useNavigate();
  // Hot reload can retain an answer parsed before the current response contract existed.
  const matched = answer.coverage.matched_count;
  const matchSummary = Number.isFinite(matched)
    ? `${matched.toLocaleString('en-GB')} matched the question.`
    : 'Matched count unavailable.';
  return (
    <div className="eye-answer">
      {answer.paragraphs.map((paragraph, index) => (
        <div key={index} className="eye-paragraph">
          {paragraph.kind !== 'finding' && (
            <span className="eye-answer-label">
              {paragraph.kind === 'inference' ? 'Assessment' : 'Coverage gap'}
            </span>
          )}
          <p>{paragraph.text}</p>
          {paragraph.citations.length > 0 && (
            <div className="eye-citations" aria-label="Supporting sources">
              {paragraph.citations.map((id) => {
                const source = answer.sources.find((item) => item.id === id);
                return source ? (
                  <SourceLink key={id} url={source.url}>
                    {id} · {source.title}
                  </SourceLink>
                ) : null;
              })}
            </div>
          )}
        </div>
      ))}
      <details className="eye-source-details">
        <summary>
          Sources and coverage{' '}
          <span>
            {answer.coverage.selected_count}{' '}
            {answer.coverage.selected_count === 1 ? 'record' : 'records'} ·{' '}
            {answer.coverage.source_count} {answer.coverage.source_count === 1 ? 'feed' : 'feeds'}
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
          {answer.sources.map((source) => (
            <div className="eye-source" key={source.id}>
              <strong>
                {source.id} · {source.title}
              </strong>
              <span>
                {source.source_id}
                {source.grade ? ` · ${source.grade}` : ''}
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
                <SourceLink url={source.url}>Open source</SourceLink>
                {source.point && (
                  <button
                    type="button"
                    onClick={() => {
                      if (!source.point) return;
                      locateAssistantPoint(source.point);
                      void navigate('/');
                    }}
                  >
                    Centre map here
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </details>
      <p className="eye-answer-meta">
        <time dateTime={answer.generated_at}>{formatUtc(answer.generated_at)}</time>
        {answer.model ? ` · ${answer.model.name}` : ' · Source availability response'}
      </p>
    </div>
  );
});
