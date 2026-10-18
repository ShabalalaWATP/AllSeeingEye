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

// Structured public documents. Every string is published wording; `{ pending }` marks a
// decision the operator has not made and always blocks publication.
const documentFiles = ['terms.json', 'acceptable-use.json', 'accessibility.json'];
const serviceFields = ['businessDisclosure', 'businessAddress', 'accessibilityContact'];
const datedFields = {
  'terms.json': ['version'],
  'accessibility.json': ['lastReviewed', 'nextReview'],
};
const placeholder =
  /\b(TODO|TBC|TBD|placeholder|pending approval|awaiting confirmation|not (?:yet )?(?:decided|confirmed|approved)|to be confirmed)\b/i;

const isoDate = (value) =>
  typeof value === 'string' &&
  /^\d{4}-\d{2}-\d{2}$/.test(value) &&
  Number.isFinite(Date.parse(value)) &&
  new Date(value).getUTCFullYear() >= 1 &&
  new Date(value).toISOString().slice(0, 10) === value;

function documentProblems(name, document, check, problems) {
  for (const key of datedFields[name] ?? [])
    if (!isoDate(document?.[key])) problems.push(`Missing dated ${name} ${key}`);
  if (!Array.isArray(document?.sections) || document.sections.length === 0) {
    problems.push(`Missing ${name} sections`);
    return;
  }
  const wording = (value, label) => {
    if (value !== null && typeof value === 'object' && !Array.isArray(value) && 'pending' in value)
      problems.push(`Unresolved decision in ${label}`);
    else check(value, label);
  };
  document.sections.forEach((section, index) => {
    const label = `${name} section ${index + 1}`;
    check(section?.id, `${label} id`);
    check(section?.title, `${label} title`);
    if (!Array.isArray(section?.paragraphs) || section.paragraphs.length === 0)
      problems.push(`Missing ${label} wording`);
    else for (const value of section.paragraphs) wording(value, label);
    if (section?.items === undefined) return;
    if (!Array.isArray(section.items)) problems.push(`Invalid ${label} list`);
    else for (const value of section.items) wording(value, `${label} list`);
  });
}

export function publicationProblems(notice, approval, contentHash, service = {}, documents = {}) {
  const problems = [];
  const check = (value, label) => {
    if (typeof value !== 'string' || value.trim().length < 3) problems.push(`Missing ${label}`);
    else if (placeholder.test(value)) problems.push(`Unresolved placeholder in ${label}`);
  };
  for (const key of requiredOperatorFields) check(notice.operator?.[key], `operator.${key}`);
  for (const key of serviceFields) check(service?.[key], `service.${key}`);
  for (const name of documentFiles) documentProblems(name, documents[name], check, problems);
  if (!Array.isArray(notice.purposes) || notice.purposes.length < 5)
    problems.push('Missing purposes and lawful bases');
  else
    for (const purpose of notice.purposes)
      check(purpose.lawfulBasis, `${purpose.name}.lawfulBasis`);
  check(approval.approvedBy, 'legal wording approval');
  if (!isoDate(approval.approvedOn)) problems.push('Missing dated legal wording approval');
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
    const read = (name) => JSON.parse(readFileSync(join(directory, name), 'utf8'));
    for (const name of ['storage.json', 'attributions.generated.json']) read(name);
    const documents = Object.fromEntries(documentFiles.map((name) => [name, read(name)]));
    const hash = policyHash(directory);
    const problems = publicationProblems(
      read('privacy.json'),
      read('approval.json'),
      hash,
      read('service.json'),
      documents,
    );
    return { approved: problems.length === 0, hash, problems };
  } catch {
    return { approved: false, hash: null, problems: ['Invalid policy content or approval'] };
  }
}

/** Operator identity for the shared footer, from the same hashed content. Strings or null. */
export function footerDetails(directory = contentDir) {
  const text = (value) => (typeof value === 'string' && value.trim() ? value.trim() : null);
  try {
    const notice = JSON.parse(readFileSync(join(directory, 'privacy.json'), 'utf8'));
    const service = JSON.parse(readFileSync(join(directory, 'service.json'), 'utf8'));
    return {
      operator: text(notice.operator?.controllerName),
      contact: text(notice.operator?.controllerContact),
      address: text(service.businessAddress),
    };
  } catch {
    return { operator: null, contact: null, address: null };
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
