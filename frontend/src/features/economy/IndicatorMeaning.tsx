import type { EconomySeries } from '@/lib/api/economy';
import type { ExplainerGlossaryEntry } from '@/lib/api/economyExplainer';
import { metricExplanation } from './economyPresentation';
import { plainEnglishFor } from './explainerModel';

/**
 * A native disclosure, so it is keyboard usable and never hover only. The project's
 * careful note is always shown first; the model's everyday wording sits underneath and
 * is labelled, so a disagreement never replaces the careful note.
 */
export function IndicatorMeaning({
  series,
  glossary,
}: {
  series: EconomySeries;
  glossary: readonly ExplainerGlossaryEntry[];
}) {
  const plain = plainEnglishFor(series.id, series.name, glossary);
  return (
    <details className="border-t border-line/60 px-3 pb-3 sm:px-4">
      <summary className="w-fit cursor-pointer py-2 text-[11px] text-muted hover:text-text focus-visible:outline-2 focus-visible:outline-ember">
        What does this mean?
      </summary>
      <div className="space-y-2 pb-1 text-[12px] leading-5 text-muted">
        <p>{metricExplanation(series.id)}</p>
        {plain && (
          <p>
            <span className="font-medium text-text">In everyday words: </span>
            {plain}
            <span className="block text-2xs">Written by the model from these figures.</span>
          </p>
        )}
        <p className="text-[11px]">
          Unit: {series.unit}. Source: {series.provider}.
        </p>
      </div>
    </details>
  );
}
