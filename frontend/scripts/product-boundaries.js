// Traverse public-route imports, including transitive barrels and lazy imports. A
// direct-import-only lint rule misses shared helpers that pull in account stores.
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';

const PRIVATE_SOURCE =
  /^(?:stores\/|features\/(?!product\/)|app\/(?:App\.|router\/|shell\/(?:AppShell|AdminShell|RequireAuth|RequireAdmin)\.)|lib\/map\/)/;
const MAP_RUNTIME = /^(?:maplibre-gl|three|hls\.js|@(?:deck|luma|loaders|math)\.gl)(?:\/|$)/;

function imports(source) {
  const found = [];
  function visit(node) {
    if ((ts.isImportDeclaration(node) || ts.isExportDeclaration(node)) && node.moduleSpecifier)
      found.push(node.moduleSpecifier);
    if (ts.isCallExpression(node) && node.expression.kind === ts.SyntaxKind.ImportKeyword)
      found.push(node.arguments[0]);
    if (ts.isImportTypeNode(node) && ts.isLiteralTypeNode(node.argument))
      found.push(node.argument.literal);
    ts.forEachChild(node, visit);
  }
  visit(source);
  return found.filter((node) => node && ts.isStringLiteralLike(node)).map((node) => node.text);
}

export function inspectProductImports(root, entry = 'src/features/product/ProductPage.tsx') {
  const config = ts.readConfigFile(path.join(root, 'tsconfig.app.json'), ts.sys.readFile);
  if (config.error) throw new Error('Cannot load application TypeScript config.');
  const parsed = ts.parseJsonConfigFileContent(config.config, ts.sys, root);
  if (parsed.errors.length) throw new Error('Invalid application TypeScript config.');
  const cache = ts.createModuleResolutionCache(root, (name) => name, parsed.options);
  const pending = [[path.resolve(root, entry), entry]];
  const seen = new Set();
  const failures = [];
  while (pending.length) {
    const [file, trail] = pending.pop();
    if (seen.has(file)) continue;
    seen.add(file);
    const relative = path.relative(path.join(root, 'src'), file).split(path.sep).join('/');
    if (PRIVATE_SOURCE.test(relative)) {
      failures.push(`${trail}: public product code reaches private application code.`);
      continue;
    }
    const code = ts.sys.readFile(file);
    if (code === undefined) throw new Error(`Missing product import: ${file}`);
    const source = ts.createSourceFile(file, code, ts.ScriptTarget.Latest, true);
    for (const specifier of imports(source)) {
      if (MAP_RUNTIME.test(specifier)) {
        failures.push(`${trail} -> ${specifier}: public product code reaches a map/media runtime.`);
        continue;
      }
      const resolved = ts.resolveModuleName(
        specifier,
        file,
        parsed.options,
        ts.sys,
        cache,
      ).resolvedModule;
      if (resolved && !resolved.isExternalLibraryImport)
        pending.push([resolved.resolvedFileName, `${trail} -> ${specifier}`]);
    }
  }
  return { files: [...seen].sort(), failures };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const result = inspectProductImports(path.resolve(process.argv[2] ?? '.'));
  for (const failure of result.failures) console.error(`product-boundaries: ${failure}`);
  console.log(`Product import boundary: ${result.files.length} source files inspected.`);
  process.exitCode = result.failures.length ? 1 : 0;
}
