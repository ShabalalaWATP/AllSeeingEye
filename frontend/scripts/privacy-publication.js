/** Fail closed for publication. Ordinary local builds can still review the draft. */
import { createHash } from 'node:crypto';
import { readFileSync, readdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const contentDir = resolve(
  dirname(fileURLToPath(import.meta.url)),
  '../src/features/public-policy',
);
const requiredOperatorFields = [
  'controllerName',
  'controllerContact',
  'complaintsContact',
  'complaintsProcedure',
  'jurisdiction',
  'hosting',
  'emailProvider',
  'aiProviders',
  'otherRecipients',
  'internationalTransfers',
  'retentionCriteria',
  'publicSourceAssessment',
  'storageAssessment',
  'automatedDecisions',
];

export function publicationProblems(notice, approval, contentHash) {
  const problems = [];
  const check = (value, label) => {
    if (typeof value !== 'string' || value.trim().length < 3) problems.push(`Missing ${label}`);
    else if (/\b(TODO|TBC|TBD|placeholder|pending approval|awaiting confirmation)\b/i.test(value))
      problems.push(`Unresolved placeholder in ${label}`);
  };
  for (const key of requiredOperatorFields) check(notice.operator?.[key], `operator.${key}`);
  if (!Array.isArray(notice.purposes) || notice.purposes.length < 5)
    problems.push('Missing purposes and lawful bases');
  else
    for (const purpose of notice.purposes)
      check(purpose.lawfulBasis, `${purpose.name}.lawfulBasis`);
  check(approval.approvedBy, 'legal wording approval');
  if (
    !/^\d{4}-\d{2}-\d{2}$/.test(approval.approvedOn ?? '') ||
    !Number.isFinite(Date.parse(approval.approvedOn)) ||
    new Date(approval.approvedOn).getUTCFullYear() < 1 ||
    new Date(approval.approvedOn).toISOString().slice(0, 10) !== approval.approvedOn
  )
    problems.push('Missing dated legal wording approval');
  if (approval.contentSha256 !== contentHash) problems.push('Unapproved or changed policy content');
  return problems;
}

export function policyHash(directory = contentDir) {
  const hash = createHash('sha256');
  for (const name of readdirSync(directory)
    .filter(
      (name) =>
        /\.(json|tsx?|css)$/.test(name) && name !== 'approval.json' && !/\.test\./.test(name),
    )
    .sort()) {
    hash
      .update(name)
      .update('\0')
      .update(readFileSync(join(directory, name), 'utf8').replaceAll('\r\n', '\n').trim())
      .update('\0');
  }
  return hash.digest('hex');
}

export function readPublicationState(directory = contentDir) {
  try {
    for (const name of [
      'privacy.json',
      'storage.json',
      'attributions.generated.json',
      'approval.json',
    ])
      JSON.parse(readFileSync(join(directory, name), 'utf8'));
    const notice = JSON.parse(readFileSync(join(directory, 'privacy.json'), 'utf8'));
    const approval = JSON.parse(readFileSync(join(directory, 'approval.json'), 'utf8'));
    const hash = policyHash(directory);
    const problems = publicationProblems(notice, approval, hash);
    return { approved: problems.length === 0, hash, problems };
  } catch {
    return { approved: false, hash: null, problems: ['Invalid policy content or approval'] };
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const { hash, problems } = readPublicationState();
  if (problems.length) {
    console.error(
      `Public policy publication is blocked:\n${problems.map((problem) => `- ${problem}`).join('\n')}`,
    );
    console.error(
      `Review content SHA256: ${hash}. Record approval only after the operator actually approves this wording.`,
    );
    process.exitCode = 1;
  } else console.log(`Public policy approval matches ${hash}`);
}
