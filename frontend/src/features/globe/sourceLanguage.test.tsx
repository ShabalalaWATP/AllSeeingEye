import { render, screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { useAuthStore } from '@/stores/auth';
import { liveEvent, plainUser, tokenFor } from '@/test/fixtures';
import { server } from '@/test/server';
import { EventInspector } from './EventInspector';
import { NewsPanel } from './NewsPanel';
import { useNewsFilters } from './newsFilters';

function article(id: string, overrides: Partial<LiveEvent>) {
  return liveEvent({
    id,
    category: 'news',
    subtype: 'headline',
    source_id: 'bbc_world',
    url: `https://example.com/${id}`,
    point: null,
    country_iso: null,
    geo_confidence: 'none',
    ...overrides,
  });
}

const ukrainian = article('uk', {
  language: 'uk',
  title: 'Обстріл Харкова',
  title_en: null,
  summary: 'Повідомлення про вибухи.',
});
const arabic = article('ar', {
  language: 'ar',
  title: 'قصف في حلب',
  title_en: 'Shelling in Aleppo',
  summary: 'تقارير عن انفجارات.',
});
const undetermined = article('und', {
  language: 'und',
  title: 'Mixed feed headline',
  title_en: null,
  summary: 'Mixed feed summary.',
});

function expectMarked(element: HTMLElement, language: string | null) {
  expect(element).toHaveAttribute('dir', 'auto');
  if (language === null) expect(element).not.toHaveAttribute('lang');
  else expect(element).toHaveAttribute('lang', language);
}

describe('EventInspector language marking', () => {
  const inspect = (event: LiveEvent) =>
    render(
      <MemoryRouter>
        <EventInspector event={event} onClose={vi.fn()} />
      </MemoryRouter>,
    );

  it('marks the original title and summary with the source language', () => {
    inspect(ukrainian);
    expectMarked(screen.getByRole('heading', { level: 2, name: 'Обстріл Харкова' }), 'uk');
    expectMarked(screen.getByText('Повідомлення про вибухи.'), 'uk');
  });

  it('keeps the English translation in the page language', () => {
    inspect(arabic);
    expectMarked(screen.getByRole('heading', { level: 2, name: 'قصف في حلب' }), 'ar');
    expectMarked(screen.getByText('تقارير عن انفجارات.'), 'ar');
    expect(screen.getByText('Shelling in Aleppo')).not.toHaveAttribute('lang');
  });

  it('gives undetermined text automatic direction without a language', () => {
    inspect(undetermined);
    expectMarked(screen.getByRole('heading', { level: 2, name: 'Mixed feed headline' }), null);
    expectMarked(screen.getByText('Mixed feed summary.'), null);
  });
});

describe('NewsPanel language marking', () => {
  beforeEach(() => useAuthStore.getState().setSession(tokenFor(plainUser)));

  function Harness() {
    const filters = useNewsFilters([], false);
    return (
      <MemoryRouter>
        <NewsPanel filters={filters} country={null} windowHours={null} onSelect={vi.fn()} />
      </MemoryRouter>
    );
  }

  async function renderStories(items: LiveEvent[]) {
    server.use(http.get('/api/events', () => HttpResponse.json({ items, count: items.length })));
    render(<Harness />);
    return within(await screen.findByRole('list', { name: 'News stories' }));
  }

  it('marks original headlines and summaries in three languages', async () => {
    const list = await renderStories([ukrainian, arabic, undetermined]);
    expectMarked(list.getByRole('heading', { name: 'Обстріл Харкова' }), 'uk');
    expectMarked(list.getByText('Повідомлення про вибухи.'), 'uk');
    expect(list.getByRole('heading', { name: 'Shelling in Aleppo' })).not.toHaveAttribute('lang');
    expectMarked(list.getByText('تقارير عن انفجارات.'), 'ar');
    expectMarked(list.getByRole('heading', { name: 'Mixed feed headline' }), null);
    expectMarked(list.getByText('Mixed feed summary.'), null);
  });

  it('marks the original titles of related evidence records', async () => {
    const lead = article('lead', {
      language: 'en',
      title: 'Strike reported in Kharkiv',
      story_id: 'story',
      published_at: '2026-09-05T02:00:00Z',
    });
    const related = article('related', {
      language: 'uk',
      title: 'Удар по Харкову',
      title_en: null,
      story_id: 'story',
      source_id: 'ukrinform',
      published_at: '2026-09-05T01:00:00Z',
    });
    const list = await renderStories([lead, related]);
    expectMarked(list.getByText('Удар по Харкову'), 'uk');
  });
});
