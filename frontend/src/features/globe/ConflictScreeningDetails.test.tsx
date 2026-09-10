import { fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { expect, it, vi } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import { ConflictScreeningDetails } from './ConflictScreeningDetails';
import { EventInspector } from './EventInspector';

const pending = liveEvent({ category: 'conflict', source_id: 'gdelt_events', subtype: 'fight' });

it('labels raw and uncertain signals without presenting their provider titles as verified headlines', () => {
  const { rerender } = render(<ConflictScreeningDetails event={pending} />);
  expect(screen.getByText('Unreviewed media signal')).toBeVisible();
  expect(screen.getByText(/generated title is not the original article headline/)).toBeVisible();
  expect(screen.queryByText('Screening model')).not.toBeInTheDocument();
  rerender(
    <ConflictScreeningDetails
      event={liveEvent({
        ...pending,
        attributes: {
          conflict_screening: 'llm',
          conflict_relevance: 'uncertain',
          conflict_screening_reason: 'The matched text does not identify armed actors.',
        },
      })}
    />,
  );
  expect(screen.getByText('Uncertain media signal')).toBeVisible();
  expect(screen.getByText(/does not identify armed actors/)).toBeVisible();
  expect(screen.getByText(/not verification of the event/)).toBeVisible();
});

it('shows model screening evidence as plain text while retaining grade, provider subtype and precision', () => {
  const event = liveEvent({
    ...pending,
    attributes: {
      conflict_screening: 'llm',
      conflict_relevance: 'armed_conflict',
      conflict_screening_reason: 'The article describes armed forces exchanging fire.',
      conflict_screening_quote: '<img src=x onerror=alert(1)> Troops exchanged fire.',
      conflict_screening_model: 'test-model',
      conflict_screening_source: 'bbc_world',
      root_code: '19',
    },
  });
  render(
    <MemoryRouter>
      <EventInspector event={event} onClose={vi.fn()} />
    </MemoryRouter>,
  );
  const review = screen.getByRole('region', { name: 'Conflict relevance screening' });
  expect(within(review).getByText('Armed conflict reporting')).toBeVisible();
  expect(within(review).getByText('test-model')).toBeVisible();
  expect(within(review).getByText('bbc_world')).toBeVisible();
  expect(within(review).getByText(/<img src=x onerror=alert\(1\)>/)).toBeVisible();
  expect(review.querySelector('img')).toBeNull();
  expect(screen.getByText(`Grade ${event.grade}`)).toBeVisible();
  expect(screen.getByText('fight')).toBeVisible();
  expect(screen.getByText('Location precision')).toBeVisible();
  expect(screen.getByText('root_code')).not.toBeVisible();
  fireEvent.click(screen.getByText('Source fields'));
  expect(screen.getByText('root_code')).toBeVisible();
  expect(screen.queryByText('conflict_screening_quote')).not.toBeInTheDocument();
});

it('shows known exclusions and omits the section for provider-coded and other-category records', () => {
  const { rerender } = render(
    <ConflictScreeningDetails
      event={liveEvent({
        ...pending,
        attributes: {
          conflict_screening: 'llm',
          conflict_relevance: 'unrelated',
          conflict_screening_model: 'test-model',
        },
      })}
    />,
  );
  expect(screen.getByText('Unrelated to conflict')).toBeVisible();
  expect(screen.queryByText('Matched source')).not.toBeInTheDocument();
  expect(screen.queryByText('Text used for screening')).not.toBeInTheDocument();
  rerender(
    <ConflictScreeningDetails
      event={liveEvent({
        ...pending,
        attributes: {
          conflict_screening: 'llm',
          conflict_relevance: 'context',
          conflict_screening_source: 'un_news',
        },
      })}
    />,
  );
  expect(screen.getByText('Context reporting')).toBeVisible();
  expect(screen.queryByText('Screening model')).not.toBeInTheDocument();
  rerender(
    <ConflictScreeningDetails event={liveEvent({ ...pending, source_id: 'acled_events' })} />,
  );
  expect(screen.queryByRole('region')).not.toBeInTheDocument();
  rerender(<ConflictScreeningDetails event={liveEvent({ ...pending, category: 'news' })} />);
  expect(screen.queryByRole('region')).not.toBeInTheDocument();
});
