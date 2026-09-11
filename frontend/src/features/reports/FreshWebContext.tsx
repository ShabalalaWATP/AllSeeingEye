import { Fragment } from 'react';
import type { ReactNode } from 'react';

import type { WebResearch } from '@/lib/api/webResearch';
import { formatUtc } from '@/lib/format';

/** Citation offsets refer to code points, not UTF-16 positions in browser strings. */
function linkedSynthesis(record: WebResearch): ReactNode[] {
  const text = Array.from(record.synthesis);
  let cursor = 0;
  const parts: ReactNode[] = [];
  const citations = record.citations.map((citation, index) => ({ ...citation, index }));
  for (const citation of citations.sort((a, b) => a.end_index - b.end_index)) {
    const end = Math.max(cursor, Math.min(text.length, citation.end_index));
    parts.push(text.slice(cursor, end).join(''));
    parts.push(
      <a
        key={citation.index}
        href={citation.url}
        target="_blank"
        rel="noopener noreferrer"
        className="mx-1 text-ember underline"
        aria-label={`Web reference ${citation.index + 1}: ${citation.title}`}
      >
        [{citation.index + 1}]
      </a>,
    );
    cursor = end;
  }
  parts.push(text.slice(cursor).join(''));
  return parts;
}

export function FreshWebContext({ record }: { record: WebResearch | null | undefined }) {
  if (!record) return null;
  return (
    <section
      aria-label="Fresh web context"
      className="space-y-4 rounded-lg border border-line bg-surface p-5"
    >
      <header>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-base font-semibold">Fresh web context</h2>
          <span className="font-mono text-xs text-muted">{record.status.replaceAll('_', ' ')}</span>
        </div>
        <p className="mt-2 text-xs leading-relaxed text-muted">{record.notice}</p>
      </header>
      <p className="text-sm">{record.explanation}</p>
      {record.status === 'completed' && (
        <>
          <div className="whitespace-pre-wrap text-sm leading-relaxed [overflow-wrap:anywhere]">
            {linkedSynthesis(record).map((part, index) => (
              <Fragment key={index}>{part}</Fragment>
            ))}
          </div>
          <ol aria-label="Web references" className="space-y-2 border-t border-line pt-3 text-xs">
            {record.citations.map((citation, index) => (
              <li key={`${citation.url}:${index}`}>
                <a
                  href={citation.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-ember underline"
                >
                  {index + 1}. {citation.title}
                </a>
              </li>
            ))}
          </ol>
        </>
      )}
      <p className="text-xs text-muted">
        Retrieved {formatUtc(record.retrieved_at)} · {record.tool_calls} search/tool calls
        {record.returned_model ? ` · ${record.returned_model}` : ''}
      </p>
    </section>
  );
}
