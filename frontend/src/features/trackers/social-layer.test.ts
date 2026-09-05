import { describe, expect, it, vi } from 'vitest';

import { buildEventLayers } from '@/features/globe/layers/registry';
import { liveEvent } from '@/test/fixtures';

describe('social globe layer', () => {
  it('shows only located posts and honours the existing category toggle', () => {
    const located = liveEvent({ category: 'social', subtype: 'post', tags: ['mastodon'] });
    const unlocated = liveEvent({ id: 'unlocated', category: 'social', point: null });
    const layers = buildEventLayers([located, unlocated], [], vi.fn(), null);
    expect(layers).toHaveLength(1);
    expect(layers[0]?.id).toBe('events-social');
    expect(layers[0]?.props.data).toEqual([located]);
    expect(buildEventLayers([located, unlocated], ['social'], vi.fn(), null)).toEqual([]);
  });
});
