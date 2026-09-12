import type { EconomyRegion } from '@/lib/api/economy';
import { annualIndicator, observationAge } from './economicChanges';
import { formatEconomicValue } from './economyPresentation';

const METRICS = [
  { id: 'growth', label: 'Growth' },
  { id: 'inflation', label: 'Inflation' },
  { id: 'unemployment', label: 'Unemployment' },
  { id: 'current_account', label: 'Current account' },
] as const;

/** Describe annual observations without inferring an outcome for the selected news period. */
export function countryOverview(region: EconomyRegion, currentYear?: number) {
  const facts = METRICS.flatMap(({ id, label }) => {
    const indicator = annualIndicator(region, id);
    if (!indicator) return [];
    const { series, point } = indicator;
    const amount = formatEconomicValue(Math.abs(point.value), series.unit);
    let text: string;
    switch (id) {
      case 'growth':
        text =
          point.value === 0
            ? `real output was unchanged in ${point.date}`
            : `real output ${point.value > 0 ? 'grew' : 'contracted'} by ${amount} in ${point.date}`;
        break;
      case 'inflation':
        text =
          point.value === 0
            ? `average consumer prices were unchanged in ${point.date}`
            : `consumer prices ${point.value > 0 ? 'rose' : 'fell'} by ${amount} in ${point.date}`;
        break;
      case 'unemployment':
        text = `unemployment was ${amount} of the labour force in ${point.date}`;
        break;
      case 'current_account':
        text =
          point.value === 0
            ? `the current account was balanced in ${point.date}`
            : `the current account recorded a ${point.value > 0 ? 'surplus' : 'deficit'} of ${amount} of GDP in ${point.date}`;
    }
    return [{ id, label, text, series, old: Boolean(observationAge(point.date, currentYear)) }];
  });
  const sentences = [facts.slice(0, 2), facts.slice(2)]
    .filter((group) => group.length > 0)
    .map((group) => {
      const sentence = group.map((fact) => fact.text).join(', while ');
      return `${sentence.charAt(0).toUpperCase()}${sentence.slice(1)}.`;
    });
  return {
    text: sentences.join(' '),
    sources: facts.map(({ id, label, series }) => ({
      id,
      label,
      url: series.source_url,
      provider: series.provider,
    })),
    hasOlderObservations: facts.some((fact) => fact.old),
    cached: facts.some((fact) => fact.series.status === 'stale'),
  };
}
