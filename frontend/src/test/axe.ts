/**
 * axe-core accessibility checks for rendered pages and primitives (KAN-61).
 *
 * jsdom has no layout or paint, so some axe rules cannot give a true answer there:
 * - `color-contrast` and `link-in-text-block` need computed, painted colours. Token contrast
 *   is checked from the theme tokens for every palette in `styles/paletteClasses.test.ts`
 *   and `styles/readability.test.ts` instead.
 * - `target-size` needs real box sizes; jsdom reports every box as 0 by 0.
 * - Nothing can be hit-tested, so axe's "is a modal covering the page" heuristic always
 *   answers no. Real modal dialogs are still checked through their roles and `aria-modal`.
 * Everything else (names, roles, ARIA structure, landmarks, heading order, duplicate ids,
 * focusable content under `aria-hidden`) runs as in a browser. A browser pass is still
 * needed for contrast over images, zoom, reflow and screen reader behaviour.
 *
 * A check that throws is reported as a failure too: axe files it as "incomplete", which
 * would otherwise let a whole rule be skipped without anyone noticing.
 *
 * Test support only: never import this from application code.
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import axe from 'axe-core';
import { expect } from 'vitest';

// jsdom starts from a bare document; give it the language and title the served page declares.
const INDEX = readFileSync(resolve(process.cwd(), 'index.html'), 'utf8');
const PAGE_LANGUAGE = /<html lang="([^"]+)"/.exec(INDEX)?.[1];
const PAGE_TITLE = /<title>([^<]+)<\/title>/.exec(INDEX)?.[1];

const JSDOM_UNSUPPORTED = ['color-contrast', 'link-in-text-block', 'target-size'];

export interface AxeCheckOptions {
  /**
   * Rules to skip for this check, each with a reason in the calling test. Use sparingly:
   * a primitive rendered without the shell, for example, has no landmarks around it.
   */
  disable?: readonly string[];
}

/** One readable entry per failing node: rule, impact, what to fix, where and the guide. */
function describeNodes(result: axe.Result, nodes: axe.NodeResult[], summary: string): string[] {
  return nodes.map(
    (node) =>
      `${result.id} (${result.impact ?? 'unknown'}): ${summary}\n` +
      `  at ${node.target.join(' ')}\n` +
      `  ${(node.failureSummary ?? '').replaceAll('\n', '\n  ')}\n` +
      `  ${result.helpUrl}`,
  );
}

/** True when one of the node's checks threw rather than giving an answer. */
function errored(node: axe.NodeResult): boolean {
  return [...node.any, ...node.all, ...node.none].some((check) => check.id === 'error-occurred');
}

/** Prepare jsdom's bare document the way the served page and a browser would present it. */
function prepareDocument(): void {
  if (PAGE_LANGUAGE && !document.documentElement.lang) {
    document.documentElement.lang = PAGE_LANGUAGE;
  }
  if (PAGE_TITLE && !document.title) document.title = PAGE_TITLE;
  // Without hit testing axe's modal check throws and skips whole rules, `aria-hidden-focus`
  // among them. axe polyfills `elementsFromPoint` from this, so nothing is under any point.
  if (typeof document.elementFromPoint !== 'function') {
    Object.defineProperty(document, 'elementFromPoint', { value: () => null, configurable: true });
  }
}

/** The axe violations, and checks axe could not run, in `context` (default: the document). */
export async function axeViolations(
  context: Element | Document = document,
  { disable = [] }: AxeCheckOptions = {},
): Promise<string[]> {
  prepareDocument();
  const rules = Object.fromEntries(
    [...JSDOM_UNSUPPORTED, ...disable].map((id) => [id, { enabled: false }]),
  );
  const results = await axe.run(context, { rules, resultTypes: ['violations', 'incomplete'] });
  return [
    ...results.violations.flatMap((result) => describeNodes(result, result.nodes, result.help)),
    ...results.incomplete.flatMap((result) =>
      describeNodes(result, result.nodes.filter(errored), `axe could not run: ${result.help}`),
    ),
  ];
}

/** Fails with every violation listed, so the message says what to fix and where. */
export async function expectNoAxeViolations(
  context: Element | Document = document,
  options: AxeCheckOptions = {},
): Promise<void> {
  expect(await axeViolations(context, options)).toEqual([]);
}
