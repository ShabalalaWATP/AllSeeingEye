import { screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { watchHandlers } from '@/test/handlers.watches';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

import { HEADING_WAIT_MS, focusPage } from './useRouteFocus';

function announcer() {
  return document.querySelector('[aria-live="polite"][aria-atomic="true"]');
}

afterEach(() => {
  vi.useRealTimers();
});

describe('route titles, focus and announcements', () => {
  it('names the first page without moving focus or announcing it', async () => {
    renderApp('/subscriptions', 'user');
    await screen.findByRole('heading', { name: 'Subscriptions', level: 1 });
    expect(document.title).toBe('Subscriptions · The All Seeing Eye');
    expect(document.body).toHaveFocus();
    expect(announcer()).toHaveTextContent('');
  });

  it('moves focus to the new heading and announces a rail navigation', async () => {
    server.use(...watchHandlers);
    const { user } = renderApp('/subscriptions', 'user');
    const primary = await screen.findByRole('navigation', { name: 'Primary' });
    await user.click(within(primary).getByRole('link', { name: 'Watches' }));
    const heading = await screen.findByRole('heading', { name: 'Watches', level: 1 });
    await waitFor(() => {
      expect(heading).toHaveFocus();
    });
    expect(heading).toHaveAttribute('tabindex', '-1');
    expect(document.title).toBe('Watches · The All Seeing Eye');
    expect(announcer()).toHaveTextContent('Navigated to Watches');
  });

  it('announces a redirect but leaves focus where the reader had it', async () => {
    const { router } = renderApp('/research/recurring', 'user');
    await screen.findByRole('heading', { name: 'Subscriptions', level: 1 });
    expect(router.state.location.pathname).toBe('/subscriptions');
    await waitFor(() => {
      expect(announcer()).toHaveTextContent('Navigated to Subscriptions');
    });
    expect(document.body).toHaveFocus();
  });

  it('treats entering the research shell from administration as a navigation', async () => {
    const { user } = renderApp('/admin', 'admin');
    await screen.findByRole('heading', { name: 'Administration', level: 1 });
    expect(document.title).toBe('Administration · The All Seeing Eye');
    await user.click(screen.getByRole('link', { name: 'Return to research' }));
    await screen.findByRole('navigation', { name: 'Primary' });
    await waitFor(() => {
      expect(announcer()).toHaveTextContent('Navigated to Map');
    });
    // The globe has no page heading, so focus rests on the main landmark.
    expect(screen.getByRole('main')).toHaveFocus();
    expect(document.title).toBe('Map · The All Seeing Eye');
  });

  it('resets the title when the shell unmounts', async () => {
    const view = renderApp('/teams', 'user');
    await screen.findByRole('heading', { name: 'Teams', level: 1 });
    expect(document.title).toBe('Teams · The All Seeing Eye');
    view.unmount();
    expect(document.title).toBe('The All Seeing Eye');
  });
});

describe('focusPage', () => {
  const created: HTMLElement[] = [];
  afterEach(() => {
    for (const element of created.splice(0)) element.remove();
  });
  function main() {
    const element = document.createElement('main');
    element.tabIndex = -1;
    document.body.append(element);
    created.push(element);
    return element;
  }

  it('focuses a heading that renders after the page loads', async () => {
    const region = main();
    focusPage(region);
    expect(region).toHaveFocus();
    const heading = document.createElement('h1');
    heading.textContent = 'Late page';
    region.append(heading);
    await waitFor(() => {
      expect(heading).toHaveFocus();
    });
    expect(heading.classList.contains('focus:outline-none')).toBe(true);
  });

  it('never takes focus back from something the reader chose', async () => {
    const region = main();
    const button = document.createElement('button');
    region.append(button);
    focusPage(region);
    button.focus();
    const heading = document.createElement('h1');
    region.append(heading);
    await Promise.resolve();
    expect(button).toHaveFocus();
  });

  it('stops waiting when asked or once the wait has passed', async () => {
    vi.useFakeTimers();
    const stopped = main();
    focusPage(stopped)();
    const early = document.createElement('h1');
    stopped.append(early);
    await Promise.resolve();
    expect(stopped).toHaveFocus();

    const waited = main();
    focusPage(waited);
    vi.advanceTimersByTime(HEADING_WAIT_MS);
    const late = document.createElement('h1');
    waited.append(late);
    await Promise.resolve();
    expect(waited).toHaveFocus();
  });

  it('keeps an existing tab order on the heading', () => {
    const region = main();
    const heading = document.createElement('h1');
    heading.tabIndex = 0;
    region.append(heading);
    focusPage(region)();
    expect(heading).toHaveFocus();
    expect(heading).toHaveAttribute('tabindex', '0');
  });
});
