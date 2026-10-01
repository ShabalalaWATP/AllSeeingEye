/**
 * WCAG 2.5.3 (label in name) checks for jsdom. The visible label is the rendered text
 * of a control, skipping anything hidden from sight (`aria-hidden`, `hidden` or the
 * `sr-only` utility). The accessible name comes from Testing Library's own name
 * computation, so it matches what `getByRole(..., { name })` sees.
 */
import { getRoles, queryAllByRole } from '@testing-library/react';
import { expect } from 'vitest';

function hiddenFromSight(element: Element): boolean {
  return (
    element.getAttribute('aria-hidden') === 'true' ||
    element.hasAttribute('hidden') ||
    element.classList.contains('sr-only')
  );
}

/** The text a sighted reader sees inside `element`, whitespace collapsed. */
export function visibleText(element: Element): string {
  const parts: string[] = [];
  const walk = (node: Node) => {
    if (node.nodeType === Node.TEXT_NODE) {
      parts.push(node.textContent ?? '');
      return;
    }
    if (node instanceof Element && hiddenFromSight(node)) return;
    node.childNodes.forEach(walk);
  };
  element.childNodes.forEach(walk);
  return parts.join(' ').replace(/\s+/g, ' ').trim();
}

function roleOf(element: HTMLElement, container: HTMLElement): string {
  const roles = getRoles(container);
  const role = Object.keys(roles).find((name) => roles[name]?.includes(element));
  if (role === undefined) throw new Error('The element has no accessible role.');
  return role;
}

/** The computed accessible name of `element`. */
export function accessibleName(element: HTMLElement): string {
  const container = element.parentElement ?? document.body;
  let name = '';
  queryAllByRole(container, roleOf(element, container), {
    name: (computed, candidate) => {
      if (candidate === element) name = computed;
      return false;
    },
  });
  return name;
}

/** Case, spacing and punctuation do not change what speech input users say. */
function spoken(text: string): string {
  return text.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, '');
}

/** Whether the accessible name contains the visible label, in the same order. */
export function labelInName(element: HTMLElement): boolean {
  const label = spoken(visibleText(element));
  return label !== '' && spoken(accessibleName(element)).includes(label);
}

/** Fails with both strings when the accessible name does not contain the visible label. */
export function expectLabelInName(element: HTMLElement): void {
  expect({
    name: accessibleName(element),
    visible: visibleText(element),
    contained: labelInName(element),
  }).toMatchObject({ contained: true });
}
