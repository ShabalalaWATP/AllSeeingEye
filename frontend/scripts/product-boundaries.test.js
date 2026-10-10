import assert from 'node:assert/strict';
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { test } from 'node:test';
import { inspectProductImports } from './product-boundaries.js';

test('follows aliased, relative, re-exported and lazy product dependencies', () => {
  const root = mkdtempSync(path.join(os.tmpdir(), 'ase-product-boundary-'));
  try {
    for (const folder of ['features/product', 'lib', 'stores', 'app/shell'])
      mkdirSync(path.join(root, 'src', folder), { recursive: true });
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
    const entry = path.join(root, 'src/features/product/ProductPage.tsx');
    writeFileSync(entry, 'import "@/lib/public";');
    const shared = path.join(root, 'src/lib/public.ts');
    writeFileSync(shared, 'export const value=1;');
    assert.deepEqual(inspectProductImports(root).failures, []);
    writeFileSync(path.join(root, 'src/stores/auth.ts'), 'export{}');
    writeFileSync(path.join(root, 'src/app/shell/AppShell.tsx'), 'export{}');
    writeFileSync(path.join(root, 'src/app/shell/pageTitles.ts'), 'export{}');
    writeFileSync(path.join(root, 'src/lib/workspaceNavigation.ts'), 'export{}');
    for (const code of [
      'export * from "../stores/auth";',
      'const lazy=()=>import("@/app/shell/AppShell");',
      'const lazy=()=>import(`@/stores/auth`);',
      'import type { State } from "@/stores/auth";',
      'export * from "@/app/shell/pageTitles";',
      'export * from "@/lib/workspaceNavigation";',
      'import "maplibre-gl";',
      'import "@deck.gl/core";',
    ]) {
      writeFileSync(shared, code);
      const failures = inspectProductImports(root).failures;
      assert.equal(failures.length, 1, code);
      assert.match(failures[0], /@\/lib\/public -> /);
    }
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('the delivered public route has no transitive account or globe imports', () => {
  assert.deepEqual(inspectProductImports(path.resolve('.')).failures, []);
});
