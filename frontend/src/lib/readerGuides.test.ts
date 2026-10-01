/**
 * The reader guides name the same workspaces as the navigation definition, and none of
 * them describes a navigation link the app no longer has. Test support reads the
 * repository's docs from disk; the app never imports them.
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

import { helpDestination, navigationEntries } from './workspaceNavigation';

const DOCS = resolve(process.cwd(), '..', 'docs');
const guide = (name: string) => readFileSync(resolve(DOCS, name), 'utf8');

/** The first column of the "Find your way around" table in the features guide. */
function workspaceTableLabels(markdown: string): string[] {
  const section = markdown.split('## Find your way around')[1]?.split('\n## ')[0] ?? '';
  return section
    .split('\n')
    .filter((line) => line.startsWith('|') && !/^\|\s*(Workspace|---)/.test(line))
    .map((line) => line.split('|')[1]?.trim().replace(/\*\*/g, '') ?? '')
    .filter(Boolean);
}

describe('reader guides', () => {
  it('list every navigation destination in the features guide with the same label', () => {
    const labels = workspaceTableLabels(guide('04_FEATURES_AND_VIEWS.md'));
    const expected = [
      ...navigationEntries({ admin: true }).map((entry) => entry.label),
      helpDestination.label,
    ];
    expect(labels).toEqual(expected);
  });

  it.each(['04_FEATURES_AND_VIEWS.md', 'ECONOMY_WORKSPACE.md', 'RESEARCH_WORKSPACE_OPERATIONS.md'])(
    '%s describes no retired navigation',
    (name) => {
      const text = guide(name);
      // Settings links only to account security; the catalogue and alert rules live elsewhere.
      expect(text).not.toMatch(/settings[^.]*links?\s+to\s+the\s+source\s+catalogue/i);
      expect(text).not.toMatch(/six-item\s+sidebar|main\s+sidebar\s+contains/i);
      expect(text).not.toMatch(/Research\s+contains\s+New\s+research,\s+Saved\s+reports/i);
      expect(text).not.toMatch(/Obsidian,\s+Slate\s+and\s+Daylight\s+themes/i);
    },
  );
});
