import { useMemo, useState } from 'react';
import type { Category, LiveEvent } from '@/lib/api/eventSchemas';

export const NEWS_SUBJECTS = [
  { id: 'news', label: 'General news' },
  { id: 'political', label: 'Politics and policy' },
  { id: 'humanitarian', label: 'Humanitarian reporting' },
  { id: 'economic', label: 'Economy and business' },
  { id: 'social', label: 'Public social reporting' },
] as const;
export const NEWS_CATEGORIES: readonly Category[] = NEWS_SUBJECTS.map((subject) => subject.id);
export const isNewsCategory = (category: Category) => NEWS_CATEGORIES.includes(category);
export interface NewsOptions {
  categories: readonly Category[];
  query: string;
  source: string;
}
export const DEFAULT_NEWS_OPTIONS: NewsOptions = { categories: ['news'], query: '', source: '' };
export function newsSourceLabel(event: LiveEvent): string {
  const name = event.attributes.original_source_name;
  return typeof name === 'string' && name.trim() ? name : event.source_id.replaceAll('_', ' ');
}
export function matchesNews(event: LiveEvent, options: NewsOptions) {
  return (
    options.categories.includes(event.category) &&
    (!options.source || event.source_id === options.source) &&
    [event.title, event.title_en, event.summary, event.source_id, event.country_iso]
      .join(' ')
      .toLocaleLowerCase()
      .includes(options.query.trim().toLocaleLowerCase())
  );
}
/** The News control owns news-related display subjects; backend categories stay unchanged. */
export function useNewsFilters(events: readonly LiveEvent[], enabled: boolean) {
  const [options, setOptions] = useState<NewsOptions>(DEFAULT_NEWS_OPTIONS);
  const filtered = useMemo(
    () =>
      events.filter(
        (event) => !isNewsCategory(event.category) || (enabled && matchesNews(event, options)),
      ),
    [events, enabled, options],
  );
  const count = useMemo(
    () => events.filter((event) => matchesNews(event, options)).length,
    [events, options],
  );
  return { enabled, options, setOptions, filtered, count };
}

/** Group only known story identities or identical links, never invent corroboration. */
export function newsStories(events: readonly LiveEvent[]) {
  const groups = new Map<string, { lead: LiveEvent; records: LiveEvent[] }>();
  const ordered = [...events].sort(
    (a, b) => (Date.parse(b.published_at ?? '') || 0) - (Date.parse(a.published_at ?? '') || 0),
  );
  for (const event of ordered) {
    const key = event.story_id ? `story:${event.story_id}` : (event.url ?? `event:${event.id}`);
    const group = groups.get(key);
    if (group) group.records.push(event);
    else groups.set(key, { lead: event, records: [event] });
  }
  return [...groups.values()];
}
