import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

import { attributionContent, renderedAttributions } from './attributions.js';

test('public credits include every catalogue identity and all primary/additional policies', async () => {
  const actual = readFileSync(
    new URL('../src/features/public-policy/attributions.generated.json', import.meta.url),
    'utf8',
  );
  assert.equal(actual.replaceAll('\r\n', '\n'), await renderedAttributions());
});

test('unknown rights stay unknown and enrichment terms are retained', () => {
  const unknown = {
    name: 'Unknown',
    licence: 'Not established',
    attribution: 'Preserve source credit',
    terms_url: null,
    additional_terms_urls: [],
    review_status: 'not_reviewed',
    terms_checked_on: null,
  };
  const result = attributionContent(
    {
      sources: [
        {
          id: 'example',
          name: 'Example',
          family: 'feed',
          source_url: null,
          policy: 'primary',
          additional_policies: ['enrichment'],
        },
      ],
    },
    {
      assessed_on: '2026-10-09',
      policies: { primary: unknown, enrichment: { ...unknown, name: 'Enrichment' } },
    },
  );
  assert.deepEqual(
    result.sources[0].policies.map((policy) => policy.name),
    ['Unknown', 'Enrichment'],
  );
  assert.equal(result.sources[0].policies[1].termsUrl, null);
  assert.equal(result.sources[0].policies[1].reviewStatus, 'not_reviewed');
  assert.throws(() =>
    attributionContent(
      { sources: [{ additional_policies: [], policy: 'missing' }] },
      { policies: {} },
    ),
  );
});
