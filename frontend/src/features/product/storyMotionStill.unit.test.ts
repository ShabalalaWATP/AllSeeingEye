/**
 * The pause control and reduced-motion requests set data-motion="still" on the story.
 * Every CSS animation or transition under the product feature needs a matching still
 * override, or a paused page keeps moving.
 */
import { readdirSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { expect, it } from 'vitest';

const DIR = resolve(__dirname);
const STILL = "[data-motion='still']";

interface Rule {
  file: string;
  selector: string;
  body: string;
}

function rules(file: string): Rule[] {
  const css = readFileSync(resolve(DIR, file), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');
  return [...css.matchAll(/([^{}]+)\{([^{}]*)\}/g)].map((match) => ({
    file,
    selector: (match[1] ?? '').trim(),
    body: match[2] ?? '',
  }));
}

function parts(selector: string): string[] {
  const out: string[] = [];
  let depth = 0;
  let current = '';
  for (const char of selector) {
    if (char === '(') depth++;
    if (char === ')') depth--;
    if (char === ',' && depth === 0) {
      out.push(current.trim());
      current = '';
    } else current += char;
  }
  out.push(current.trim());
  return out.filter(Boolean);
}

/** Expands `:is(a, b)` so each alternative can be compared on its own. */
function alternatives(part: string): string[] {
  const match = /:is\(([^)]*)\)/.exec(part);
  if (!match) return [part];
  return parts(match[1] ?? '').map((inner) => part.replace(match[0], inner));
}

const classes = (selector: string) => new Set(selector.match(/\.[\w-]+/g) ?? []);

const files = readdirSync(DIR).filter((file) => file.endsWith('.css'));
const all = files.flatMap(rules);
const moves = (body: string, property: string) =>
  new RegExp(`(^|[;\\s])${property}\\s*:\\s*(?!none)`).test(body);
const stops = (body: string, property: string) =>
  new RegExp(`(^|[;\\s])${property}\\s*:\\s*none`).test(body);

it.each(['animation', 'transition'])('pauses every product %s when the story is still', (prop) => {
  const moving = all.filter(
    (rule) =>
      !rule.selector.includes(STILL) && !rule.selector.startsWith('@') && moves(rule.body, prop),
  );
  const stilled = all
    .filter((rule) => rule.selector.includes(STILL) && stops(rule.body, prop))
    .flatMap((rule) => parts(rule.selector).flatMap(alternatives))
    .map(classes);
  expect(moving.length).toBeGreaterThan(2);
  const unguarded = moving.flatMap((rule) =>
    parts(rule.selector)
      .filter((part) => {
        const wanted = classes(part);
        return !stilled.some(
          (guard) => guard.size > 0 && [...guard].every((name) => wanted.has(name)),
        );
      })
      .map((part) => `${rule.file}: ${part}`),
  );
  expect(unguarded).toEqual([]);
});
