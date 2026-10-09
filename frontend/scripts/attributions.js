/** Build public credits from the reviewed catalogue, without contacting providers. */
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { format, resolveConfig } from 'prettier';

const here = dirname(fileURLToPath(import.meta.url));
const resources = resolve(here, '../../backend/src/ase/resources');
const target = resolve(here, '../src/features/public-policy/attributions.generated.json');

export function attributionContent(catalogue, register) {
  const ids = new Set();
  return {
    assessedOn: register.assessed_on,
    sources: catalogue.sources.map((source) => {
      if (ids.has(source.id)) throw new Error(`Duplicate source ${source.id}`);
      ids.add(source.id);
      return {
        id: source.id,
        name: source.name,
        family: source.family,
        sourceUrl: source.source_url,
        policies: [...new Set([source.policy, ...source.additional_policies])].map((id) => {
          const policy = register.policies[id];
          if (!policy) throw new Error(`Missing attribution policy ${id}`);
          return {
            id,
            name: policy.name,
            licence: policy.licence,
            attribution: policy.attribution,
            termsUrl: policy.terms_url,
            additionalTermsUrls: policy.additional_terms_urls,
            reviewStatus: policy.review_status,
            checkedOn: policy.terms_checked_on,
          };
        }),
      };
    }),
  };
}

export async function renderedAttributions() {
  return format(
    JSON.stringify(
      attributionContent(
        JSON.parse(readFileSync(resolve(resources, 'source_licences.json'), 'utf8')),
        JSON.parse(readFileSync(resolve(resources, 'source_licence_policies.json'), 'utf8')),
      ),
      null,
      2,
    ),
    { ...(await resolveConfig(target)), parser: 'json' },
  );
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const expected = await renderedAttributions();
  if (process.argv.includes('--check')) {
    if (readFileSync(target, 'utf8').replaceAll('\r\n', '\n') !== expected)
      throw new Error('Public attributions are stale. Run pnpm gen:attributions.');
  } else writeFileSync(target, expected);
}
