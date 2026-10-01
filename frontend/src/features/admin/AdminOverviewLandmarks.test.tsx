/**
 * The administration overview keeps all content inside landmarks and its headings in order
 * (KAN-67). There is no axe dependency, so this mirrors axe's `region` and `heading-order`
 * rules on the rendered page, including the shell around it.
 */
import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { renderApp } from '@/test/render';

const LANDMARKS = [
  'main',
  'nav',
  'aside',
  'footer',
  'header',
  'form[aria-label]',
  'section[aria-label]',
  'section[aria-labelledby]',
  '[role=main]',
  '[role=navigation]',
  '[role=banner]',
  '[role=complementary]',
  '[role=region]',
  '[role=contentinfo]',
  '[role=dialog]',
  '[role=alertdialog]',
].join(', ');

/** Text outside every landmark, except the skip link that axe also exempts. */
function strayText(): string[] {
  const stray: string[] = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const parent = node.parentElement;
    const text = node.textContent?.trim() ?? '';
    if (!parent || text === '' || parent.closest('[aria-hidden="true"], script, style')) continue;
    if (parent.closest('a[href="#main-content"]')) continue;
    if (!parent.closest(LANDMARKS)) stray.push(text);
  }
  return stray;
}

describe('administration overview structure', () => {
  it('keeps every piece of content inside a landmark', async () => {
    renderApp('/admin', 'admin');
    await screen.findByRole('heading', { level: 1, name: 'Administration' });
    await screen.findByRole('heading', { level: 2, name: 'AI usage' });
    expect(strayText()).toEqual([]);
    expect(screen.getByRole('complementary', { name: 'Eye assistant' })).toContainElement(
      screen.getByRole('button', { name: 'Ask Eye' }),
    );
  });

  it('has one h1 and never skips a heading level', async () => {
    renderApp('/admin', 'admin');
    await screen.findByRole('heading', { level: 1, name: 'Administration' });
    await screen.findByRole('heading', { level: 2, name: 'AI usage' });
    const levels = screen.getAllByRole('heading').map((heading) => Number(heading.tagName[1]));
    expect(levels.filter((level) => level === 1)).toHaveLength(1);
    expect(levels[0]).toBe(1);
    const skips = levels.filter((level, index) => index > 0 && level > levels[index - 1]! + 1);
    expect(skips).toEqual([]);
  });
});
