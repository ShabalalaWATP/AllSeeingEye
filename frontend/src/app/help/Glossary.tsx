import { GLOSSARY } from '@/lib/glossary';
import { loadedBands, useYardstick } from '@/lib/hooks/useYardstick';

/** The research terms a report or alert rule uses, with the configured likelihood bands. */
export function Glossary() {
  const yardstick = useYardstick();
  return (
    <dl className="divide-y divide-line/70">
      {GLOSSARY.map((entry) => (
        <div
          key={entry.id}
          id={`glossary-${entry.id}`}
          className="grid scroll-mt-6 gap-1 py-2 sm:grid-cols-[14rem_1fr]"
        >
          <dt className="text-sm font-medium">{entry.term}</dt>
          <dd className="text-sm leading-6 text-muted">
            {entry.text}
            {entry.id === 'likelihood' && loadedBands(yardstick).length > 0 && (
              <ul aria-label="Configured likelihood bands" className="mt-1 list-disc pl-5">
                {loadedBands(yardstick).map((band) => (
                  <li key={band.probability}>{`${band.term}: ${band.range_description}`}</li>
                ))}
              </ul>
            )}
            {entry.id === 'likelihood' && yardstick === 'unavailable' && (
              <span className="block">The configured bands could not be loaded.</span>
            )}
          </dd>
        </div>
      ))}
    </dl>
  );
}
