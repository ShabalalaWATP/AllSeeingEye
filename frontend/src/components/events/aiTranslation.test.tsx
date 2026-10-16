import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { expect, it } from 'vitest';

import type { LiveEvent } from '@/lib/api/eventSchemas';
import { textTransformationSchema } from '@/lib/api/sourceProvenance';
import { liveEvent } from '@/test/fixtures';
import { EventRow } from './EventRow';
import { EventTitle } from './EventTitle';

const transformation = textTransformationSchema.parse({
  field: 'title',
  original_text: 'قصف في حلب',
  transformed_text: 'Shelling in Aleppo',
  kind: 'translation',
  source_language: 'ar',
  target_language: 'en',
  origin: 'machine',
  method: 'ase-title-translation-v1',
  review_status: 'unreviewed',
});
const translated = liveEvent({
  title: transformation.original_text,
  title_en: transformation.transformed_text,
  language: 'ar',
  transformations: [transformation],
});

it('labels the displayed AI translation without changing the title or original-language text', () => {
  const { rerender } = render(<EventTitle event={translated} as="h3" />);
  expect(screen.getByRole('heading', { name: 'Shelling in Aleppo' })).not.toHaveAttribute('lang');
  expect(screen.getByText('AI-assisted translation')).toBeVisible();

  rerender(<EventTitle event={{ ...translated, title_en: null }} as="h3" />);
  expect(screen.getByRole('heading', { name: 'قصف في حلب' })).toHaveAttribute('lang', 'ar');
  expect(screen.queryByText('AI-assisted translation')).not.toBeInTheDocument();
});

it('labels the event row while preserving the source and research link names', () => {
  render(
    <MemoryRouter>
      <ul>
        <EventRow event={translated} />
      </ul>
    </MemoryRouter>,
  );
  expect(screen.getByText('AI-assisted translation')).toBeVisible();
  expect(screen.getByRole('link', { name: 'Shelling in Aleppo' })).toHaveAttribute(
    'href',
    translated.url,
  );
  expect(
    screen.getByRole('link', { name: 'Research this report: Shelling in Aleppo' }),
  ).toBeInTheDocument();
});

const notAi: [string, NonNullable<LiveEvent['transformations']>][] = [
  ['missing provenance', []],
  ['operator translation', [{ ...transformation, origin: 'operator', model: 'declared-model' }]],
  ['source translation', [{ ...transformation, origin: 'source' }]],
  ['transliteration', [{ ...transformation, kind: 'transliteration' }]],
  ['different original', [{ ...transformation, original_text: 'Other title' }]],
  ['different result', [{ ...transformation, transformed_text: 'Other result' }]],
  ['unidentified machine method', [{ ...transformation, method: 'Unknown method' }]],
];

it.each(notAi)('does not infer AI authorship from %s', (_name, transformations) => {
  render(<EventTitle event={{ ...translated, transformations }} />);
  expect(screen.getByText('Shelling in Aleppo')).toBeVisible();
  expect(screen.queryByText('AI-assisted translation')).not.toBeInTheDocument();
});

it('includes the visible disclosure in the name when a translated title is a link', () => {
  render(
    <a href="https://example.com/source">
      <EventTitle event={translated} />
    </a>,
  );
  expect(
    screen.getByRole('link', { name: /Shelling in Aleppo.*AI-assisted translation/ }),
  ).toHaveAttribute('href', 'https://example.com/source');
});

it('recognises recorded model provenance without requiring the current translation method', () => {
  render(
    <EventTitle
      event={{
        ...translated,
        transformations: [{ ...transformation, method: 'Older method', model: 'saved-model' }],
      }}
    />,
  );
  expect(screen.getByText('AI-assisted translation')).toBeVisible();
});
