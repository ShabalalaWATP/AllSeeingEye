import path from 'node:path';
import ts from 'typescript';

/** Resolve imports using the same paths and extension rules as the application compiler. */
export function featureBoundaryRule(root) {
  const configPath = path.join(root, 'tsconfig.app.json');
  const config = ts.readConfigFile(configPath, ts.sys.readFile);
  if (config.error) throw new Error('Cannot load application TypeScript config.');
  const parsed = ts.parseJsonConfigFileContent(config.config, ts.sys, root);
  if (parsed.errors.length) throw new Error('Invalid application TypeScript config.');
  const featureRoot = path.join(root, 'src/features');
  const cache = ts.createModuleResolutionCache(root, (name) => name, parsed.options);
  const feature = (filename) => {
    const relative = path.relative(featureRoot, filename);
    return relative.startsWith('..') || path.isAbsolute(relative)
      ? null
      : relative.split(path.sep)[0];
  };
  return {
    meta: {
      type: 'problem',
      schema: [],
      messages: {
        crossFeature:
          'Feature "{{from}}" must not import feature "{{to}}". Move shared code to components, lib or stores.',
      },
    },
    create(context) {
      const filename = context.filename;
      const from = feature(filename);
      const check = (source) => {
        const specifier =
          source?.type === 'TemplateLiteral' && source.expressions.length === 0
            ? source.quasis[0]?.value.cooked
            : source?.value;
        if (!from || typeof specifier !== 'string') return;
        const resolved = ts.resolveModuleName(
          specifier,
          filename,
          parsed.options,
          ts.sys,
          cache,
        ).resolvedModule;
        if (!resolved) return; // TypeScript separately rejects unresolved application imports.
        const to = feature(resolved.resolvedFileName);
        if (to && to !== from)
          context.report({ node: source, messageId: 'crossFeature', data: { from, to } });
      };
      return {
        ImportDeclaration: (node) => check(node.source),
        ExportNamedDeclaration: (node) => check(node.source),
        ExportAllDeclaration: (node) => check(node.source),
        ImportExpression: (node) => check(node.source),
        TSImportType: (node) =>
          check(node.argument.type === 'TSLiteralType' ? node.argument.literal : node.argument),
      };
    },
  };
}
