/**
 * Guards for the product story's content: it must cover what the app really offers and
 * must not advertise sources whose terms forbid commercial or promotional use.
 */
import { readdirSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';

import { MAP_LAYER_GROUPS } from '@/lib/mapLayerDirectory';

import { buildScene } from '../scenes/sceneData';
import { CHAPTER_LINKS } from './chapters';
import { LAYER_STORIES, MAP_TOOLS, STORY_LAYERS } from './observe';
import { WORKSPACES } from './platform';
import { DEPTHS, EVIDENCE, JUDGEMENTS, PHIA_BANDS } from './research';
import { ON_DEMAND_TOTAL, SCHEDULED_TOTAL, SOURCE_TOPICS, SOURCE_TOTAL } from './sources';
import * as observe from './observe';
import * as platform from './platform';
import * as research from './research';
import * as sources from './sources';

// Cloudflare Radar, OONI, IODA, DeepState, adsb.fi, EOX, The Independent, CNA, Reddit,
// Open-Meteo, Global Fishing Watch and OpenSanctions, however they are spelt.
const RESTRICTED =
  /cloudflare|ooni|\bioda\b|deep\s?state|adsb\.fi|\beox\b|the independent|\bcna\b|channel newsasia|reddit|open[\s-]?meteo|\bgfw\b|fishing watch|open\s?sanctions/i;

const PRODUCT = resolve(__dirname, '..');
/** The page's own source text, so copy written straight into a chapter is checked too. */
const STORY_SOURCES = [
  ...readdirSync(resolve(PRODUCT, 'chapters'))
    .filter((file) => file.endsWith('.tsx') && !file.includes('.test.'))
    .map((file) => resolve(PRODUCT, 'chapters', file)),
  resolve(PRODUCT, 'ProductStory.tsx'),
];

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
    // Pinned so a directory change is a deliberate copy change, not a silent one.
    expect(MAP_TOOLS).toHaveLength(17);
    expect(STORY_LAYERS).toHaveLength(15);
  });

  it('covers all eleven source topics and adds up its own totals', () => {
    expect(SOURCE_TOPICS).toHaveLength(11);
    // Recounted from the backend catalogue on 18 October 2026: live connectors built
    // with no keys, and research specs (KAN-171 claims register, source recount).
    expect(SCHEDULED_TOTAL).toBe(263);
    expect(ON_DEMAND_TOTAL).toBe(160);
    expect(Object.fromEntries(SOURCE_TOPICS.map((topic) => [topic.id, topic.scheduled]))).toEqual({
      disaster: 15,
      conflict: 4,
      news: 97,
      aviation: 7,
      maritime: 2,
      space: 8,
      cyber: 20,
      social: 68,
      political: 11,
      humanitarian: 5,
      economic: 26,
    });
    expect(SOURCE_TOTAL).toBe(
      SOURCE_TOPICS.reduce((sum, topic) => sum + topic.scheduled + topic.onDemand, 0),
    );
  });

  it('names no source whose terms forbid commercial or promotional use', () => {
    const text = JSON.stringify([observe, platform, research, sources]);
    expect(text).not.toMatch(RESTRICTED);
    expect(STORY_SOURCES.length).toBeGreaterThan(10);
    for (const file of STORY_SOURCES) {
      expect(readFileSync(file, 'utf8'), file).not.toMatch(RESTRICTED);
    }
  });

  it('recognises every restricted spelling', () => {
    for (const name of [
      'Cloudflare Radar',
      'OONI',
      'IODA',
      'DeepState',
      'adsb.fi',
      'EOX',
      'The Independent',
      'CNA',
      'Reddit',
      'Open-Meteo',
      'Open Meteo',
      'GFW',
      'Global Fishing Watch',
      'OpenSanctions',
    ]) {
      expect(`Data from ${name}.`).toMatch(RESTRICTED);
    }
  });

  it('uses the PHIA yardstick and only cites evidence that exists', () => {
    expect(PHIA_BANDS).toHaveLength(7);
    const ids = new Set(EVIDENCE.map((card) => card.id));
    for (const judgement of JUDGEMENTS) {
      expect(PHIA_BANDS).toContain(judgement.likelihood);
      expect(['High', 'Moderate', 'Low']).toContain(judgement.confidence);
      for (const cite of judgement.cites) expect(ids.has(cite)).toBe(true);
    }
    expect(DEPTHS.map((depth) => depth.name)).toEqual(['Basic', 'Deep', 'Advanced']);
  });

  it('keeps out the wording the claims register found unsupported', () => {
    // docs/product-page/claims-register.md: each phrase overstated or contradicted the
    // code or documentation it describes (KAN-171).
    const overclaims =
      /every source, grade|event by event|one command|data stays put|strict content security|any date window|per-domain filters|source health beside every feed|until reviewed|could not find/i;
    const text = JSON.stringify([observe, platform, research, sources]);
    expect(text).not.toMatch(overclaims);
    for (const file of STORY_SOURCES) {
      expect(readFileSync(file, 'utf8'), file).not.toMatch(overclaims);
    }
  });

  it('links each header chapter to a story section and keeps copy free of em dashes', () => {
    expect(new Set(CHAPTER_LINKS.map((chapter) => chapter.id)).size).toBe(CHAPTER_LINKS.length);
    const text = JSON.stringify([observe, platform, research, sources, WORKSPACES]);
    expect(text).not.toContain('—');
  });
});
