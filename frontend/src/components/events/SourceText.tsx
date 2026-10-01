import type { ReactNode } from 'react';
import { sourceLanguageTag } from './sourceLanguage';

type SourceTextElement = 'span' | 'p' | 'h2' | 'h3' | 'div';

/**
 * Source-language text (WCAG 3.1.2): sets `lang` only for a plausible, determined language tag,
 * and always lets the browser pick the reading direction from the text itself.
 */
export function SourceText({
  language,
  as: Element = 'span',
  id,
  className,
  children,
}: {
  /** The source-declared language code; `und`, `null` or implausible values set no `lang`. */
  language: string | null | undefined;
  as?: SourceTextElement;
  id?: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <Element id={id} lang={sourceLanguageTag(language)} dir="auto" className={className}>
      {children}
    </Element>
  );
}
