import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

import type { UkraineReference } from '@/lib/api/ukraine';
import { mockWebGl2 } from '@/test/env';
import { ukraineReference } from '@/test/fixtures.ukraineReference';

import { TimelineSection } from '../TimelineSection';

// jsdom has no WebGL; the scene is replaced by inert calls, as in the journey tests.
vi.mock('./journeyScene', () => ({
  createJourneyScene: () => ({
    travelTo: () => undefined,
    setPlaying: () => undefined,
    setRunning: () => undefined,
    resize: () => undefined,
    dispose: () => undefined,
  }),
}));

const event = (
  id: string,
  phase: string,
  on: string,
  title: string,
  imageId: string | null = null,
): UkraineReference['events'][number] => ({
  id,
  phase_id: phase,
  on,
  title,
  text: `What happened at ${title}.`,
  theme: 'ground',
  wikidata_id: null,
  image_id: imageId,
  links: [{ label: 'Wikipedia article', url: `https://en.wikipedia.org/wiki/${id}` }],
});

const reference: UkraineReference = {
  ...ukraineReference,
  themes: { ground: 'Ground war' },
  phases: [
    {
      id: 'invasion',
      label: 'Full-scale invasion',
      start: '2022-02-24',
      end: '2022-04-07',
      summary: 'Russia attacked from the north, east and south.',
    },
    {
      id: '2026',
      label: 'The fifth year',
      start: '2026-01-01',
      end: null,
      summary: 'The war continued into its fifth year.',
    },
  ],
  events: [
    event(
      'invasion-day',
      'invasion',
      '2022-02-24',
      'The full-scale invasion begins',
      'invasion-day',
    ),
    event('kyiv', 'invasion', '2022-03-25', 'The battle for Kyiv is won'),
    event('talks', '2026', '2026-01-15', 'Talks without a ceasefire'),
  ],
};

const fetcher = () => Promise.resolve(new Blob(['x'], { type: 'image/jpeg' }));

beforeAll(() => {
  // jsdom has no object URLs; the image only needs a string it can put in src.
  if (!('createObjectURL' in URL)) {
    Object.assign(URL, { createObjectURL: () => 'blob:journey', revokeObjectURL: () => undefined });
  }
});

const stage = () => screen.getByTestId('journey-stage');
const counter = () => screen.getByText(/^\d+ of \d+$/);

/** Anything a keyboard can reach or a script can focus, as axe's aria-hidden-focus sees it. */
const FOCUSABLE = [
  'a[href]',
  'area[href]',
  'button',
  'input',
  'select',
  'textarea',
  'summary',
  'iframe',
  'audio[controls]',
  'video[controls]',
  '[tabindex]',
  '[contenteditable=""]',
  '[contenteditable="true"]',
].join(', ');

/** Every focusable element that an aria-hidden ancestor (or its own attribute) hides. */
function focusableUnderAriaHidden(root: HTMLElement): string[] {
  return Array.from(root.querySelectorAll<HTMLElement>(FOCUSABLE))
    .filter((element) => element.closest('[aria-hidden="true"]') !== null)
    .map((element) => `${element.tagName.toLowerCase()}: ${element.textContent}`);
}

async function renderWithImage(): Promise<void> {
  render(<TimelineSection reference={reference} fetcher={fetcher} />);
  // The credit link arrives with the picture, so wait for it before checking the card.
  await waitFor(() => {
    expect(within(stage()).getByText('Someone else')).toBeInTheDocument();
  });
}

describe('the journey card for assistive technology', () => {
  it('exposes the current event, its narrative and its links', async () => {
    await renderWithImage();
    const title = within(stage()).getByText('The full-scale invasion begins', { selector: 'h3' });
    expect(title.closest('[aria-hidden="true"]')).toBeNull();
    const card = screen.getByRole('region', { name: 'Current event' });
    expect(within(card).getByRole('heading', { level: 3 })).toHaveTextContent(
      'The full-scale invasion begins',
    );
    expect(within(card).getByText('Full-scale invasion')).toBeInTheDocument();
    expect(within(card).getByText('24 February 2022')).toBeInTheDocument();
    expect(
      within(card).getByText('What happened at The full-scale invasion begins.'),
    ).toBeInTheDocument();
    const links = within(card).getAllByRole('link');
    expect(links.map((link) => link.textContent)).toEqual(['Wikipedia article', 'Someone else']);
    for (const link of links) expect(link).not.toHaveAttribute('tabindex');
    // The year watermark only repeats the card's date as decoration, so it stays hidden.
    expect(within(stage()).getByText('2022').closest('[aria-hidden="true"]')).not.toBeNull();
  });

  it.each([
    ['without WebGL', false],
    ['with WebGL', true],
  ])('leaves no focusable element under aria-hidden %s', async (_label, webgl) => {
    mockWebGl2(webgl);
    await renderWithImage();
    expect(screen.queryAllByTestId('journey-canvas')).toHaveLength(webgl ? 1 : 0);
    const timeline = screen.getByRole('region', { name: 'Timeline of the war' });
    // Guard against an empty pass: the card itself carries links.
    expect(stage().querySelectorAll('a[href]').length).toBeGreaterThan(1);
    expect(focusableUnderAriaHidden(timeline)).toEqual([]);
  });

  it('keeps the arrow keys on a card link for the link, not for travel', () => {
    render(<TimelineSection reference={reference} />);
    const link = within(stage()).getByText('Wikipedia article');
    act(() => {
      link.focus();
    });
    fireEvent.keyDown(link, { key: 'ArrowRight' });
    fireEvent.keyDown(link, { key: 'End' });
    expect(link).toHaveFocus();
    expect(counter()).toHaveTextContent('1 of 3');
  });
});

describe('announcing a new stop', () => {
  let observer: MutationObserver | undefined;

  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
  });

  afterEach(() => {
    observer?.disconnect();
    vi.useRealTimers();
  });

  /**
   * Watches the stage's one polite live region. `step` runs a reader action and records the
   * region's text once if that action changed it, so `heard` lists each announcement made.
   */
  function listen() {
    const regions = Array.from(stage().querySelectorAll<HTMLElement>('[aria-live="polite"]'));
    expect(regions).toHaveLength(1);
    const [region] = regions;
    if (region === undefined) throw new Error('The stage has no live region');
    const heard: string[] = [];
    const watcher = new MutationObserver(() => undefined);
    watcher.observe(region, { childList: true, characterData: true, subtree: true });
    observer = watcher;
    const step = (action: () => void): void => {
      act(action);
      if (watcher.takeRecords().length > 0) heard.push(region.textContent);
    };
    return { region, heard, step };
  }

  const settle = () => vi.advanceTimersByTime(2_000);

  it('says only the new title, once, when the stop changes', () => {
    render(<TimelineSection reference={reference} />);
    const live = listen();
    // The first stop is already on the card; nothing has changed yet, so nothing is said.
    expect(live.region).toBeEmptyDOMElement();
    const next = screen.getByRole('button', { name: 'Next event' });
    next.focus();
    live.step(() => fireEvent.click(next));
    live.step(settle);
    live.step(() => vi.advanceTimersByTime(10_000));
    expect(live.heard).toEqual(['The battle for Kyiv is won']);
  });

  it('waits for travel to settle, so a fast run across stops is one announcement', () => {
    render(<TimelineSection reference={reference} />);
    const live = listen();
    for (const key of ['End', 'ArrowLeft', 'Home', 'ArrowRight']) {
      live.step(() => fireEvent.keyDown(stage(), { key }));
      live.step(() => vi.advanceTimersByTime(100));
    }
    live.step(settle);
    expect(live.heard).toEqual(['The battle for Kyiv is won']);
    // Away and straight back again is no change, so nothing more is said.
    live.step(() => fireEvent.keyDown(stage(), { key: 'ArrowRight' }));
    live.step(() => fireEvent.keyDown(stage(), { key: 'ArrowLeft' }));
    live.step(settle);
    expect(live.heard).toEqual(['The battle for Kyiv is won']);
  });

  it('leaves the title to a focused control that already says it', () => {
    render(<TimelineSection reference={reference} />);
    const live = listen();
    const slider = screen.getByRole('slider');
    live.step(() => slider.focus());
    live.step(() => fireEvent.change(slider, { target: { value: '2' } }));
    live.step(settle);
    // The scrubber's value text already speaks the date and the title.
    expect(slider).toHaveAttribute('aria-valuetext', '15 January 2026, Talks without a ceasefire');
    // Focusing an entry in the open reading list travels there; its name is the title.
    live.step(() => screen.getByRole('button', { name: 'The battle for Kyiv is won' }).focus());
    live.step(settle);
    expect(counter()).toHaveTextContent('2 of 3');
    expect(live.heard).toEqual([]);
    const next = screen.getByRole('button', { name: 'Next event' });
    live.step(() => next.focus());
    live.step(() => fireEvent.click(next));
    live.step(settle);
    expect(live.heard).toEqual(['Talks without a ceasefire']);
  });
});
