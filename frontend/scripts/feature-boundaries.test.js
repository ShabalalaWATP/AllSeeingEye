import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { test } from 'node:test';
import { Linter } from 'eslint';
import tseslint from 'typescript-eslint';
import { featureBoundaryRule } from './feature-boundaries.js';

test('feature boundaries resolve aliases, relative paths, types and re-exports', () => {
  const root = mkdtempSync(path.join(os.tmpdir(), 'ase-boundaries-'));
  try {
    for (const folder of ['src/features/alpha', 'src/features/beta', 'src/lib']) {
      mkdirSync(path.join(root, folder), { recursive: true });
      writeFileSync(
        path.join(root, folder, 'index.ts'),
        'export const value = 1; export type Value = number;',
      );
    }
    writeFileSync(
      path.join(root, 'tsconfig.app.json'),
      JSON.stringify({
        compilerOptions: {
          moduleResolution: 'bundler',
          module: 'esnext',
          baseUrl: '.',
          paths: { '@/*': ['./src/*'] },
        },
        include: ['src'],
      }),
    );
    const rule = featureBoundaryRule(root);
    const linter = new Linter({ cwd: root });
    const lint = (code, filename = 'src/features/alpha/example.ts') =>
      linter.verify(
        code,
        [
          {
            files: ['**/*.ts'],
            languageOptions: { parser: tseslint.parser },
            plugins: { boundaries: { rules: { features: rule } } },
            rules: { 'boundaries/features': 'error' },
          },
        ],
        { filename: path.join(root, filename) },
      );
    for (const code of [
      "import { value } from '../beta';",
      "import type { Value } from '@/features/beta';",
      "export { value } from '@/features/beta/index';",
      "export type { Value } from '../beta/index';",
      "export * from '../beta';",
      "const lazy = import('@/features/beta');",
      'const lazy = import(`@/features/beta`);',
      "type Value = import('../beta').Value;",
    ]) {
      const messages = lint(code);
      assert.equal(messages.length, 1, code);
      assert.equal(messages[0].ruleId, 'boundaries/features', code);
    }
    for (const code of [
      "import { value } from './index';",
      "import type { Value } from '@/features/alpha';",
      "import { value } from '@/lib';",
      "import React from 'react';",
    ])
      assert.deepEqual(lint(code), [], code);
    assert.deepEqual(lint("import { value } from '@/features/beta';", 'src/app.ts'), []);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
