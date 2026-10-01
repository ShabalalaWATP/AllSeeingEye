import type { LiveEvent } from '@/lib/api/eventSchemas';

import { SourceText, type SourceTextElement } from './SourceText';
import { shownTitle } from './sourceLanguage';

/**
 * An event's display title: the English translation when there is one, otherwise the
 * original marked with its source language so screen readers use the right voice.
 */
export function EventTitle({
  event,
  as,
  className,
}: {
  event: Pick<LiveEvent, 'title' | 'title_en' | 'language'>;
  as?: SourceTextElement;
  className?: string;
}) {
  const shown = shownTitle(event);
  return (
    <SourceText language={shown.language} as={as} className={className}>
      {shown.text}
    </SourceText>
  );
}
