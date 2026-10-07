/**
 * Guards for the product story's content: it must cover what the app really offers and
 * must not advertise sources whose terms forbid commercial or promotional use.
 */
import { describe, expect, it } from 'vitest';

import { MAP_LAYER_GROUPS } from '@/lib/mapLayerDirectory';

import { buildScene } from '../scenes/sceneData';
import { CHAPTER_LINKS } from './chapters';
import { LAYER_STORIES, MAP_TOOLS, STORY_LAYERS } from './observe';
import { WORKSPACES } from './platform';
import { DEPTHS, EVIDENCE, JUDGEMENTS, PHIA_BANDS } from './research';
import { SOURCE_TOPICS, SOURCE_TOTAL } from './sources';
import * as observe from './observe';
import * as platform from './platform';
import * as research from './research';
import * as sources from './sources';

const RESTRICTED =
  /cloudflare|ooni|\bioda\b|deepstate|adsb\.fi|\beox\b|the independent|\bcna\b|channel newsasia|reddit|open-meteo|fishing watch|opensanctions/i;

describe('product story content', () => {
  it('describes every live and reference layer the globe offers, with its filters', () => {
    const directory = MAP_LAYER_GROUPS.filter((group) =>
      ['Live events', 'Reference layers'].includes(group.title),
    ).flatMap((group) => group.items.map((item) => item.id));
    expect(STORY_LAYERS.map((layer) => layer.id)).toEqual(directory);
    for (const id of directory) {
      expect(LAYER_STORIES[id]?.filters.length, id).toBeGreaterThan(0);
    }
    expect(buildScene().map((layer) => layer.id)).toEqual(directory);
  });

  it('lists every map setup and planning tool', () => {
    const tools = MAP_LAYER_GROUPS.filter((group) =>
      ['Map setup', 'Planning tools'].includes(group.title),
    ).flatMap((group) => group.items);
    expect(MAP_TOOLS).toEqual(tools);
  });

  it('covers all eleven source topics and adds up its own totals', () => {
    expect(SOURCE_TOPICS).toHaveLength(11);
    expect(SOURCE_TOTAL).toBe(
      SOURCE_TOPICS.reduce((sum, topic) => sum + topic.scheduled + topic.onDemand, 0),
    );
  });

  it('names no source whose terms forbid commercial or promotional use', () => {
    const text = JSON.stringify([observe, platform, research, sources]);
    expect(text).not.toMatch(RESTRICTED);
  });

  it('uses the PHIA yardstick and only cites evidence that exists', () => {
    expect(PHIA_BANDS).toHaveLength(7);
    const ids = new Set(EVIDENCE.map((card) => card.id));
    for (const judgement of JUDGEMENTS) {
      expect(PHIA_BANDS).toContain(judgement.likelihood);
      for (const cite of judgement.cites) expect(ids.has(cite)).toBe(true);
    }
    expect(DEPTHS.map((depth) => depth.name)).toEqual(['Basic', 'Deep', 'Advanced']);
  });

  it('links each header chapter to a story section and keeps copy free of em dashes', () => {
    expect(new Set(CHAPTER_LINKS.map((chapter) => chapter.id)).size).toBe(CHAPTER_LINKS.length);
    const text = JSON.stringify([observe, platform, research, sources, WORKSPACES]);
    expect(text).not.toContain('—');
  });
});
