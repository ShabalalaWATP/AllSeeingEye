/**
 * Staggered motion must finish: every element whose CSS formula combines the chapter's
 * --progress with its own --i index has to be fully drawn and opaque at progress 1,
 * which is also where a still or paused story holds each chapter. The formulas are
 * read from the stylesheets and evaluated for the last item of each list.
 */
import { readdirSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { render } from '@testing-library/react';
import { expect, it } from 'vitest';

import { DeployChapter } from './chapters/DeployChapter';
import { REVIEW_TIMELINE, TRUST_LAYERS } from './content/platform';
import { EVIDENCE, JUDGEMENTS, REPORT_NEXT, SCOPE_CHIPS } from './content/research';
import { SOURCE_TOPICS } from './content/sources';
import { StoryMotionContext } from './motion/useStoryMotion';

function diagramCounts(): { links: number; nodes: number } {
  const { container, unmount } = render(
    <StoryMotionContext.Provider value={{ still: true, idle: true }}>
      <DeployChapter />
    </StoryMotionContext.Provider>,
  );
  const counts = {
    links: container.querySelectorAll('.architecture-link').length,
    nodes: container.querySelectorAll('.architecture-node').length,
  };
  unmount();
  return counts;
}

/** How many items each staggered selector is given by the chapters. */
function itemCounts(): Record<string, number> {
  const diagram = diagramCounts();
  return {
    '.trust-layer': TRUST_LAYERS.length,
    '.scope-chip': SCOPE_CHIPS.length,
    '.evidence-card': EVIDENCE.length,
    '.judgement': JUDGEMENTS.length,
    '.report-next li': REPORT_NEXT.length,
    '.timeline-beat': REVIEW_TIMELINE.length,
    '.orbit-node': SOURCE_TOPICS.length,
    '.architecture-link': diagram.links,
    '.architecture-node': diagram.nodes,
  };
}

/** Top-level comma-separated arguments of the call that opens at `start`. */
function callArguments(text: string, start: number): { args: string[]; end: number } {
  const args: string[] = [];
  let depth = 0;
  let current = '';
  for (let index = start; index < text.length; index++) {
    const char = text[index] ?? '';
    if (char === '(' && depth++ === 0) continue;
    if (char === ')' && --depth === 0) return { args: [...args, current.trim()], end: index };
    if (char === ',' && depth === 1) {
      args.push(current.trim());
      current = '';
    } else current += char;
  }
  throw new Error(`Unbalanced call in ${text}`);
}

/** Evaluates + - * / and brackets over plain numbers. */
function evaluate(expression: string): number {
  const tokens = expression.match(/\d*\.?\d+|[-+*/()]/g) ?? [];
  let position = 0;
  const next = () => tokens[position++] ?? '';
  const peek = () => tokens[position] ?? '';
  function factor(): number {
    const token = next();
    if (token === '-') return -factor();
    if (token === '(') {
      const value = sum();
      next();
      return value;
    }
    return Number(token);
  }
  function product(): number {
    let value = factor();
    while (peek() === '*' || peek() === '/')
      value = next() === '*' ? value * factor() : value / factor();
    return value;
  }
  function sum(): number {
    let value = product();
    while (peek() === '+' || peek() === '-')
      value = next() === '+' ? value + product() : value - product();
    return value;
  }
  return sum();
}

/** The value inside each clamp(0, value, 1), with progress and index substituted. */
function clampedValues(declaration: string, progress: number, index: number): number[] {
  const values: number[] = [];
  let at = declaration.indexOf('clamp(');
  while (at !== -1) {
    const { args, end } = callArguments(declaration, at + 'clamp'.length);
    const expression = (args[1] ?? '')
      .replaceAll('calc', '')
      .replaceAll('var(--progress)', String(progress))
      .replaceAll('var(--i)', String(index));
    values.push(evaluate(expression));
    at = declaration.indexOf('clamp(', end);
  }
  return values;
}

const staggered = readdirSync(__dirname)
  .filter((file) => file.endsWith('.css'))
  .flatMap((file) => {
    const css = readFileSync(resolve(__dirname, file), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');
    return [...css.matchAll(/([^{}]+)\{([^{}]*)\}/g)].flatMap((match) =>
      (match[2] ?? '')
        .split(';')
        .filter((line) => line.includes('var(--progress)') && line.includes('var(--i)'))
        .map((line) => ({ file, selector: (match[1] ?? '').trim(), declaration: line.trim() })),
    );
  });

it('finds the staggered formulas it checks', () => {
  expect(staggered.length).toBeGreaterThanOrEqual(9);
  expect(evaluate('1 * 10 - 8.2 - 2 * 0.35')).toBeCloseTo(1.1);
});

it('brings the last staggered item of every list fully in by progress 1', () => {
  const counts = itemCounts();
  const unfinished = staggered.flatMap(({ file, selector, declaration }) => {
    const count = counts[selector];
    if (count === undefined) return [`${file}: register the item count for ${selector}`];
    expect(count, selector).toBeGreaterThan(0);
    return clampedValues(declaration, 1, count - 1)
      .filter((value) => value < 1)
      .map((value) => `${file}: ${selector} reaches ${value.toFixed(2)} (${declaration})`);
  });
  expect(unfinished).toEqual([]);
});
