import { expect, it } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import { LiveEventSnapshot } from './liveEventSnapshot';

const article = liveEvent({ category: 'news', observed_at: '2026-09-21T00:00:00Z' });
const newer = { ...article, title: 'Correction', observed_at: '2026-09-21T01:00:00Z' };
const create = (limit = 300, journal = 5000) =>
  new LiveEventSnapshot((event) => event.category === 'news', limit, journal);

it('keeps live corrections on equal timestamps and accepts genuinely newer snapshots', () => {
  const snapshot = create();
  snapshot.finish(snapshot.begin([newer]), [article]);
  expect(snapshot.getSnapshot()).toEqual([newer]);
  const equalTimeCorrection = { ...newer, title: 'Corrected again' };
  snapshot.upsert([equalTimeCorrection]);
  snapshot.finish(snapshot.begin([article]), [newer]);
  expect(snapshot.getSnapshot()).toEqual([equalTimeCorrection]);
  const latest = { ...newer, observed_at: '2026-09-21T02:00:00Z' };
  snapshot.finish(snapshot.begin([article]), [latest]);
  expect(snapshot.getSnapshot()).toEqual([latest]);
});

it('applies in-flight updates and removals for records absent from the viewport', () => {
  const snapshot = create();
  const pending = snapshot.begin([]);
  snapshot.upsert([newer]);
  snapshot.expire(['removed']);
  snapshot.finish(pending, [article, { ...article, id: 'removed' }]);
  expect(snapshot.getSnapshot()).toEqual([newer]);
  snapshot.expire([article.id]);
  expect(snapshot.getSnapshot()).toEqual([]);
  // A later independent server snapshot can establish a genuine reappearance.
  snapshot.finish(snapshot.begin([]), [newer]);
  expect(snapshot.getSnapshot()).toEqual([newer]);
});

it('honours expire/upsert order and removes category corrections', () => {
  const snapshot = create();
  const pending = snapshot.begin([]);
  snapshot.expire([article.id]);
  snapshot.upsert([newer]);
  snapshot.finish(pending, [article]);
  expect(snapshot.getSnapshot()).toEqual([newer]);
  snapshot.upsert([{ ...newer, category: 'aviation' }]);
  expect(snapshot.getSnapshot()).toEqual([]);
});

it('rejects overflow instead of losing removal history, then permits a fresh request', () => {
  const snapshot = create(1, 2);
  const pending = snapshot.begin([]);
  snapshot.expire(['first', 'second', article.id]);
  expect(() => snapshot.finish(pending, [article])).toThrow('bounded journal');
  expect(snapshot.getSnapshot()).toEqual([]);
  snapshot.finish(snapshot.begin([]), [article, { ...article, id: 'extra' }]);
  expect(snapshot.getSnapshot()).toEqual([article]);
});

it('clears old authority state and ignores superseded completions', () => {
  const snapshot = create();
  const old = snapshot.begin([]);
  snapshot.clear();
  snapshot.finish(old, [article]);
  expect(snapshot.getSnapshot()).toEqual([]);
  const first = snapshot.begin([]);
  const next = snapshot.begin([]);
  snapshot.cancel(first);
  snapshot.finish(first, [article]);
  snapshot.finish(next, [newer]);
  expect(snapshot.getSnapshot()).toEqual([newer]);
});

it('accepts a supplemental page alongside a full mirror without exhausting the delta journal', () => {
  const snapshot = create();
  snapshot.finish(snapshot.begin([]), [article]);
  const mirror = Array.from({ length: 5000 }, (_, index) =>
    liveEvent({ id: `aircraft-${index}`, category: 'aviation' }),
  );
  const pending = snapshot.begin(mirror);
  snapshot.upsert([{ ...article, id: 'new-live-news' }]);
  snapshot.finish(pending, [article, { ...article, id: 'new-live-news' }]);
  expect(snapshot.getSnapshot()).toHaveLength(2);
});
