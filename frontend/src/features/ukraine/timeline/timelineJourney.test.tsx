import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { UkraineReference } from '@/lib/api/ukraine';
import { mockMatchMedia, mockWebGl2, setVisibility } from '@/test/env';
import { ukraineReference } from '@/test/fixtures.ukraineReference';

import { TimelineSection } from '../TimelineSection';

const scene = {
  travelTo: vi.fn(),
  setPlaying: vi.fn(),
  setRunning: vi.fn(),
  resize: vi.fn(),
  dispose: vi.fn(),
};
const createJourneyScene = vi.fn(() => scene);
vi.mock('./journeyScene', () => ({ createJourneyScene: () => createJourneyScene() }));

const event = (
  id: string,
  phase: string,
  on: string,
  title: string,
  theme = 'ground',
): UkraineReference['events'][number] => ({
  id,
  phase_id: phase,
  on,
  title,
  text: `What happened at ${title}.`,
  theme,
  wikidata_id: null,
  image_id: null,
  links: [{ label: 'Wikipedia article', url: `https://en.wikipedia.org/wiki/${id}` }],
});

const reference: UkraineReference = {
  ...ukraineReference,
  themes: { ground: 'Ground war', diplomacy: 'Diplomacy and aid' },
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
    event('invasion-day', 'invasion', '2022-02-24', 'The full-scale invasion begins'),
    event('kyiv', 'invasion', '2022-03-25', 'The battle for Kyiv is won'),
    event('talks', '2026', '2026-01-15', 'Talks without a ceasefire', 'diplomacy'),
  ],
};

const stage = () => screen.getByTestId('journey-stage');
const announcement = () => within(stage()).getByText(/^Event \d/);

describe('the timeline journey without WebGL', () => {
  it('reads the whole timeline as phases and events, and says why the view is static', () => {
    render(<TimelineSection reference={reference} />);
    const phases = screen.getByRole('list', { name: 'Phases of the war' });
    expect(within(phases).getAllByRole('heading', { level: 3 })).toHaveLength(2);
    expect(within(phases).getByText('Russia attacked from the north, east and south.')).toBeVisible();
    const invasion = screen.getByRole('list', { name: 'Events: Full-scale invasion' });
    expect(invasion.querySelectorAll(':scope > li')).toHaveLength(2);
    expect(within(invasion).getByText('24 February 2022')).toBeVisible();
    expect(within(invasion).getByText(/What happened at The battle for Kyiv/)).toBeVisible();
    expect(within(invasion).getAllByRole('link', { name: 'Wikipedia article' })[0]).toHaveAttribute(
      'href',
      'https://en.wikipedia.org/wiki/invasion-day',
    );
    expect(screen.getByText(/because this browser has no WebGL2/)).toBeVisible();
    expect(screen.queryByTestId('journey-canvas')).toBeNull();
    expect(screen.getByTestId('journey-backdrop')).toBeInTheDocument();
  });

  it('travels with the buttons, the scrubber, the keyboard and the phase selector', async () => {
    const user = userEvent.setup();
    render(<TimelineSection reference={reference} />);
    expect(announcement()).toHaveTextContent('Event 1 of 3. 24 February 2022.');
    await user.click(screen.getByRole('button', { name: 'Next event' }));
    expect(announcement()).toHaveTextContent('Event 2 of 3. 25 March 2022.');
    await user.click(screen.getByRole('button', { name: 'Previous event' }));
    expect(screen.getByRole('button', { name: 'Previous event' })).toBeDisabled();
    fireEvent.change(screen.getByRole('slider'), { target: { value: '2' } });
    expect(announcement()).toHaveTextContent('Event 3 of 3. 15 January 2026.');
    expect(screen.getByRole('button', { name: 'Next event' })).toBeDisabled();
    fireEvent.keyDown(screen.getByRole('button', { name: 'Previous event' }), { key: 'Home' });
    expect(announcement()).toHaveTextContent('Event 1 of 3.');
    fireEvent.keyDown(stage(), { key: 'ArrowRight' });
    expect(announcement()).toHaveTextContent('Event 2 of 3.');
    fireEvent.keyDown(stage(), { key: 'End' });
    expect(announcement()).toHaveTextContent('Event 3 of 3.');
    fireEvent.keyDown(stage(), { key: 'PageUp' });
    expect(announcement()).toHaveTextContent('Event 1 of 3.');
    fireEvent.keyDown(stage(), { key: 'Enter' });
    expect(announcement()).toHaveTextContent('Event 1 of 3.');
    const selector = screen.getByRole('list', { name: 'Phases' });
    await user.click(within(selector).getByRole('button', { name: /The fifth year/ }));
    expect(announcement()).toHaveTextContent('Event 3 of 3.');
    expect(within(selector).getByRole('button', { name: /The fifth year/ })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
  });

  it('marks the event in the reading list and travels when one is chosen', async () => {
    const user = userEvent.setup();
    const { container } = render(<TimelineSection reference={reference} />);
    await user.click(screen.getByRole('button', { name: 'The battle for Kyiv is won' }));
    expect(announcement()).toHaveTextContent('Event 2 of 3.');
    const current = container.querySelectorAll('[aria-current="true"]');
    expect(current).toHaveLength(1);
    expect(current[0]).toHaveTextContent('The battle for Kyiv is won');
  });

  it('travels on a wheel gesture and lets the page scroll on at the ends', () => {
    render(<TimelineSection reference={reference} />);
    // fireEvent returns false when a listener called preventDefault, which is where the
    // journey takes the wheel; true means the gesture was left to the page.
    const wheel = (deltaY: number) => !fireEvent.wheel(stage(), { deltaY, cancelable: true });
    expect(wheel(200)).toBe(true);
    expect(announcement()).toHaveTextContent('Event 3 of 3.');
    // Nothing further forward: the wheel is left to the page.
    expect(wheel(200)).toBe(false);
    expect(wheel(-95)).toBe(true);
    expect(announcement()).toHaveTextContent('Event 2 of 3.');
    expect(wheel(0)).toBe(false);
  });

  it('travels on a sideways swipe', () => {
    render(<TimelineSection reference={reference} />);
    const target = stage();
    fireEvent.pointerDown(target, { clientX: 300 });
    fireEvent.pointerMove(target, { clientX: 200 });
    expect(announcement()).toHaveTextContent('Event 2 of 3.');
    fireEvent.pointerUp(target);
    fireEvent.pointerMove(target, { clientX: 100 });
    expect(announcement()).toHaveTextContent('Event 2 of 3.');
  });

  it('narrows to a theme, restarts the journey and copes with an empty result', async () => {
    const user = userEvent.setup();
    render(<TimelineSection reference={reference} />);
    fireEvent.keyDown(stage(), { key: 'End' });
    await user.click(screen.getByRole('button', { name: 'Diplomacy and aid' }));
    expect(announcement()).toHaveTextContent('Event 1 of 1. 15 January 2026.');
    expect(screen.queryByRole('list', { name: 'Events: Full-scale invasion' })).toBeNull();
    await user.click(screen.getByRole('button', { name: 'Diplomacy and aid' }));
    expect(announcement()).toHaveTextContent('Event 1 of 3.');
    await user.click(screen.getByRole('button', { name: 'All themes' }));
    render(<TimelineSection reference={{ ...reference, events: [] }} />);
    expect(screen.getAllByText('No events match this theme.').length).toBeGreaterThan(0);
  });
});

describe('the timeline journey with WebGL', () => {
  beforeEach(() => {
    mockWebGl2(true);
    createJourneyScene.mockClear();
    for (const spy of Object.values(scene)) spy.mockClear();
  });

  it('loads the scene lazily, drives it and disposes of it on unmount', async () => {
    const user = userEvent.setup();
    const view = render(<TimelineSection reference={reference} />);
    expect(screen.getByTestId('journey-canvas')).toBeInTheDocument();
    expect(screen.queryByTestId('journey-backdrop')).toBeNull();
    await waitFor(() => {
      expect(createJourneyScene).toHaveBeenCalledTimes(1);
    });
    expect(scene.travelTo).toHaveBeenCalledWith(0);
    expect(scene.setRunning).toHaveBeenCalledWith(true);
    await user.click(screen.getByRole('button', { name: 'Next event' }));
    expect(scene.travelTo).toHaveBeenLastCalledWith(1);
    await user.click(screen.getByRole('button', { name: 'Pause motion' }));
    expect(scene.setPlaying).toHaveBeenLastCalledWith(false);
    expect(screen.getByRole('button', { name: 'Resume motion' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    setVisibility('hidden');
    expect(scene.setRunning).toHaveBeenLastCalledWith(false);
    setVisibility('visible');
    expect(scene.setRunning).toHaveBeenLastCalledWith(true);
    view.unmount();
    expect(scene.dispose).toHaveBeenCalledTimes(1);
  });

  it('keeps the reading list when the scene module cannot be loaded', async () => {
    createJourneyScene.mockImplementationOnce(() => {
      throw new Error('no context');
    });
    render(<TimelineSection reference={reference} />);
    await waitFor(() => {
      expect(screen.queryByTestId('journey-canvas')).toBeNull();
    });
    expect(screen.getByRole('list', { name: 'Events: Full-scale invasion' })).toBeInTheDocument();
  });

  it('leaves the moving view off when the reader has asked for reduced motion', () => {
    mockMatchMedia(true);
    render(<TimelineSection reference={reference} />);
    expect(screen.queryByTestId('journey-canvas')).toBeNull();
    expect(screen.getByText(/because you have asked for reduced motion/)).toBeVisible();
    expect(screen.queryByRole('button', { name: 'Pause motion' })).toBeNull();
    expect(createJourneyScene).not.toHaveBeenCalled();
  });
});
