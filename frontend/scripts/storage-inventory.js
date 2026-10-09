/** Static, fail-closed inventory for application-owned browser storage. No app imports. */
import { readFileSync, readdirSync } from 'node:fs';
import { resolve, relative } from 'node:path';
import ts from 'typescript';

export function browserStorageKeys(source, filename = 'sample.ts', forwardingAdapter = false) {
  const tree = ts.createSourceFile(
    filename,
    source,
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TSX,
  );
  const values = new Map();
  const functions = new Map();
  const aliases = new Map();
  const keys = new Set();
  const failures = [];
  const visit = (node, action) => {
    action(node);
    ts.forEachChild(node, (child) => visit(child, action));
  };
  visit(tree, (node) => {
    if (ts.isVariableDeclaration(node) && ts.isIdentifier(node.name) && node.initializer) {
      const previous = values.get(node.name.text);
      values.set(
        node.name.text,
        values.has(node.name.text) && previous?.getText(tree) !== node.initializer.getText(tree)
          ? null
          : node.initializer,
      );
    }
    if (ts.isFunctionDeclaration(node) && node.name) functions.set(node.name.text, node);
    if (ts.isImportSpecifier(node) && node.propertyName)
      aliases.set(node.name.text, node.propertyName.text);
  });
  const evaluate = (node, seen = new Set()) => {
    if (!node || seen.has(node)) return null;
    seen = new Set([...seen, node]);
    if (ts.isStringLiteralLike(node)) return node.text;
    if (ts.isIdentifier(node))
      return values.has(node.text) ? evaluate(values.get(node.text), seen) : null;
    if (ts.isTemplateExpression(node)) {
      let result = node.head.text;
      for (const span of node.templateSpans)
        result += (evaluate(span.expression, seen) ?? '*') + span.literal.text;
      return result;
    }
    if (ts.isCallExpression(node) && ts.isIdentifier(node.expression)) {
      const fn = functions.get(node.expression.text);
      const returns = fn?.body?.statements.filter(ts.isReturnStatement) ?? [];
      return returns.length === 1 ? evaluate(returns[0].expression, seen) : null;
    }
    return null;
  };
  const record = (node) => {
    if (forwardingAdapter && node && ts.isIdentifier(node) && node.text === 'key') return;
    const key = evaluate(node);
    if (key === null || key === '*' || key.startsWith('*'))
      failures.push(`Unresolved storage key: ${node?.getText(tree) ?? '(absent)'}`);
    else keys.add(key);
  };
  visit(tree, (node) => {
    if (!ts.isCallExpression(node)) return;
    const expression = node.expression.getText(tree);
    const call = aliases.get(expression) ?? expression;
    if (
      /^(?:readStored|writeStored|removeStored)$/.test(call) ||
      /(?:localStorage|sessionStorage|safeLocalStorage)(?:\.|\[['"])(?:getItem|setItem|removeItem)/.test(
        call,
      )
    )
      record(node.arguments[0]);
    if (call === 'persist' && /from ['"]zustand\/middleware['"]/.test(source)) {
      const options = node.arguments[1];
      const name =
        options && ts.isObjectLiteralExpression(options)
          ? options.properties.find(
              (item) => ts.isPropertyAssignment(item) && item.name.getText(tree) === 'name',
            )
          : null;
      record(name && ts.isPropertyAssignment(name) ? name.initializer : null);
    }
  });
  // New APIs/indirection need an explicit review rather than escaping the inventory.
  visit(tree, (node) => {
    if (ts.isIdentifier(node) && ['sessionStorage', 'indexedDB', 'cookieStore'].includes(node.text))
      failures.push('New browser-storage mechanism needs a declaration and scanner support');
    if (
      ts.isBinaryExpression(node) &&
      node.operatorToken.kind === ts.SyntaxKind.EqualsToken &&
      node.left.getText(tree).replaceAll(' ', '') === 'document.cookie'
    )
      failures.push('New browser cookie write needs a declaration and scanner support');
    if (
      ts.isVariableDeclaration(node) &&
      node.initializer &&
      /^(?:window\.)?(?:localStorage|sessionStorage)$/.test(node.initializer.getText(tree))
    )
      failures.push('Aliased browser storage needs explicit scanner support');
  });
  return { keys: [...keys].sort(), failures };
}

export function cookieKeys(source) {
  const constants = new Map(
    [...source.matchAll(/^\s*(\w+)\s*=\s*["']([^"']+)["']/gm)].map((match) => [match[1], match[2]]),
  );
  const keys = new Set();
  for (const match of source.matchAll(
    /\.(?:set_cookie|delete_cookie)\(\s*(?:key\s*=\s*)?([^,\n]+)/g,
  )) {
    const expression = match[1].trim().replace(/\)\s*$/, '');
    const key = /^['"]([^'"]+)['"]$/.exec(expression)?.[1] ?? constants.get(expression);
    if (!key) throw new Error(`Unresolved cookie name: ${expression}`);
    keys.add(key);
  }
  return [...keys].sort();
}

function files(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) =>
    entry.isDirectory() ? files(resolve(directory, entry.name)) : [resolve(directory, entry.name)],
  );
}

export function storageProblems(root, declarations) {
  const problems = [];
  const found = new Set();
  for (const file of files(resolve(root, 'frontend/src'))) {
    const path = relative(root, file).replaceAll('\\', '/');
    if (!/\.[jt]sx?$/.test(path) || /\.(test|gen)\./.test(path) || path.includes('/test/'))
      continue;
    const source = readFileSync(file, 'utf8');
    if (
      !/Storage|readStored|writeStored|removeStored|zustand\/middleware|document.cookie|indexedDB|cookieStore/.test(
        source,
      )
    )
      continue;
    // Only the existing adapter's exact key parameter may be forwarded unresolved.
    const inventory = browserStorageKeys(source, file, path === 'frontend/src/lib/safeStorage.ts');
    problems.push(...inventory.failures.map((message) => `${path}: ${message}`));
    for (const key of inventory.keys) {
      found.add(key);
      if (!declarations.some((row) => row.name === key && row.kind === 'localStorage'))
        problems.push(`Undeclared localStorage key ${key} in ${path}`);
    }
  }
  for (const file of files(resolve(root, 'backend/src'))) {
    if (!file.endsWith('.py')) continue;
    for (const key of cookieKeys(readFileSync(file, 'utf8'))) {
      found.add(key);
      if (!declarations.some((row) => row.name === key && row.kind === 'cookie'))
        problems.push(`Undeclared cookie ${key}`);
    }
  }
  for (const row of declarations)
    if (!found.has(row.name)) problems.push(`Stale declaration ${row.name}`);
  return problems;
}
