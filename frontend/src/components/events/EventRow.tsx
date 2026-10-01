import { useId } from 'react';
import { Link } from 'react-router';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { eventResearchHref } from '@/lib/researchNavigation';
import { formatUtc } from '@/lib/format';
import { isHttpUrl } from '@/lib/urls';
import { CATEGORY_STYLES } from '@/lib/categories';
import { SourceText } from './SourceText';
import { englishTitle, shownTitle } from './sourceLanguage';

/**
 * One event as a list row: category, grade, time and the title as a link when safe.
 * The category's map colour marks a dot; the label stays in theme text so it reads in every theme.
 * An original-language title keeps its own `lang`; the English research label never embeds it.
 */
export function EventRow({ event }: { event: LiveEvent }) {
  const style = CATEGORY_STYLES[event.category];
  const titleId = useId();
  const title = shownTitle(event);
  const english = englishTitle(event);
  const text = (
    <SourceText id={titleId} language={title.language}>
      {title.text}
    </SourceText>
  );
  return (
    <li className="flex flex-wrap items-baseline gap-2 border-t border-line/60 py-2 text-sm">
      <span className="px-1.5 font-mono text-2xs text-text">
        <span
          aria-hidden="true"
          className="mr-1.5 inline-block size-1.5 rounded-full align-middle"
          style={{ backgroundColor: style.css }}
        />
        {style.label}
      </span>
      <span className="font-mono text-2xs text-muted" title={event.grade_rationale}>
        {event.grade}
      </span>
      <span className="font-mono text-2xs text-muted">{formatUtc(event.published_at)}</span>
      {isHttpUrl(event.url) ? (
        <a
          href={event.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-text hover:underline"
        >
          {text}
        </a>
      ) : (
        <span className="text-text">{text}</span>
      )}
      <Link
        to={eventResearchHref(event)}
        aria-label={english === null ? 'Research this report' : `Research this report: ${english}`}
        aria-describedby={english === null ? titleId : undefined}
        title="Review the question before starting research"
        className="inline-flex min-h-11 items-center text-xs text-ember hover:underline focus-visible:outline-2 focus-visible:outline-ember"
      >
        Research this
      </Link>
    </li>
  );
}
