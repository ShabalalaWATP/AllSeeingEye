import type {
  EconomyExplainer,
  ExplainerSection,
  ExplainerStatus,
} from '@/lib/api/economyExplainer';

const worldSection: ExplainerSection = {
  takeaway: 'The world economy is growing slowly while price rises keep easing.',
  paragraphs: [
    'Output grew by 2.4% in 2024, a little faster than the 1.2% recorded in 2023. That is steady rather than strong, so most households will not notice a sudden change.',
    'Shop prices rose by 3% in 2024, down from 5% in 2022. One likely reason is calmer energy costs, although the figures on their own cannot show that.',
  ],
  drivers: [
    'Growth of 2.4% in 2024 was the strongest figure supplied.',
    'Price rises slowed to 3% in 2024.',
  ],
  watch: [
    'Whether price rises keep easing next year.',
    'Whether the missing unemployment figures are published.',
  ],
};

const regionSection = (name: string): ExplainerSection => ({
  takeaway: `${name} took a knock and is now edging back, helped by what it sells abroad.`,
  paragraphs: [
    `${name} grew by 2.4% in 2024 after 1.2% in 2023. Visitors and services are a large part of what the country earns from the rest of the world.`,
    'The latest unemployment figure is not published here, so that part of the picture is missing rather than reassuring.',
  ],
  drivers: [`Growth of 2.4% in 2024 was better than 2023.`],
  watch: ['Whether the missing unemployment figure is published later.'],
});

export const economyExplainer: EconomyExplainer = {
  status: 'ready',
  stale: false,
  reason: null,
  explainer: {
    world: worldSection,
    regions: [
      { id: 'GB', section: regionSection('The United Kingdom') },
      { id: 'US', section: regionSection('The United States') },
      { id: 'RU', section: regionSection('Russia') },
      { id: 'CN', section: regionSection('China') },
      { id: 'IR', section: regionSection('Iran') },
    ],
    glossary: [
      {
        term: 'Consumer price inflation',
        plain_english: 'How quickly the prices in the shops go up over a year.',
      },
      {
        term: 'GDP growth',
        plain_english: 'How much more, or less, a country produced than the year before.',
      },
      {
        term: 'Reference rate',
        plain_english: 'A daily published exchange rate for information, not a price to trade at.',
      },
    ],
  },
  provenance: {
    model: 'plain-english-fixture',
    generated_at: '2026-09-12T06:00:00Z',
    snapshot_fetched_at: '2026-09-12T05:55:00Z',
    prompt_tokens: 4200,
    completion_tokens: 2100,
    sources: [
      'World Bank annual indicators',
      'European Central Bank euro reference rates',
      'Dated publisher economy headlines',
    ],
    written_by:
      'Written by the model from the figures shown on this page. The figures are the source of truth; the words are a plain-English description of them.',
  },
};

/** The honest states: nothing yet, being written, behind the figures, or refused. */
export function explainerState(status: ExplainerStatus, reason: string | null): EconomyExplainer {
  const carries = status === 'stale' || status === 'generating';
  return {
    ...economyExplainer,
    status,
    stale: status === 'stale',
    reason,
    explainer: carries && status === 'stale' ? economyExplainer.explainer : null,
    provenance: status === 'stale' ? economyExplainer.provenance : null,
  };
}
