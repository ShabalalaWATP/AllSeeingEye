import { expect, it } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import { eventsResponseSchema } from '@/lib/api/eventSchemas';

// Opt-in CPU audit: avoid allocating an80MB synthetic response in routine CI.
it.skipIf(process.env.ASE_PARSE_BENCHMARK !== '1')(
  'measures2000-row JSON decoding and response validation',
  () => {
    const transformation = {
      field: 'summary',
      original_text: '原'.repeat(2000),
      transformed_text: 'x'.repeat(2000),
      kind: 'translation',
      source_language: 'zh',
      target_language: 'en',
      origin: 'source',
      method: 'Declared source translation',
      review_status: 'unreviewed',
      limitations: [],
    };
    for (const maximum of [false, true]) {
      const items = Array.from({ length: 2000 }, (_, i) => ({
        ...liveEvent({
          id: String(i),
          category: maximum ? 'news' : 'aviation',
          title: maximum ? 'T'.repeat(300) : `Aircraft${i}`,
          summary: maximum ? 'S'.repeat(2000) : null,
          attributes: Object.fromEntries(
            Array.from({ length: maximum ? 40 : 10 }, (_, j) => [
              `provider_field_${j}`,
              maximum ? 'v'.repeat(500) : j,
            ]),
          ),
        }),
        transformations: maximum ? Array.from({ length: 4 }, () => transformation) : [],
        source_dates: maximum
          ? Array.from({ length: 4 }, (_, j) => ({
              field: `date${j}`,
              raw_text: '2026-09-09',
              role: 'publication',
              calendar: 'gregorian',
              basis: 'source_spec',
              precision: 'day',
              status: 'resolved',
              method: 'Source metadata',
              limitations: [],
            }))
          : [],
      }));
      const text = JSON.stringify({ items, count: items.length });
      const timings = Array.from({ length: 3 }, () => {
        const start = performance.now();
        const decoded: unknown = JSON.parse(text);
        const decodedAt = performance.now();
        const validated = eventsResponseSchema.parse(decoded);
        const validatedAt = performance.now();
        expect(validated.items).toHaveLength(2000);
        return {
          jsonMs: +(decodedAt - start).toFixed(2),
          validationMs: +(validatedAt - decodedAt).toFixed(2),
        };
      });
      process.stdout.write(
        JSON.stringify({
          maximumMetadata: maximum,
          wireMiB: +(new TextEncoder().encode(text).byteLength / 1048576).toFixed(2),
          timings,
        }) + '\n',
      );
    }
  },
  60000,
);
