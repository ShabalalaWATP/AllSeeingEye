import assert from 'node:assert/strict';
import { readFileSync, mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';

import {
  footerDetails,
  policyHash,
  publicationProblems,
  readPublicationState,
} from './privacy-publication.js';

const content = JSON.parse(
  readFileSync(new URL('../src/features/public-policy/privacy.json', import.meta.url)),
);
const draft = {
  ...content,
  operator: Object.fromEntries(Object.keys(content.operator).map((key) => [key, null])),
  purposes: content.purposes.map((purpose) => ({ ...purpose, lawfulBasis: null })),
};
const approval = {
  approvedBy: 'Operator',
  approvedOn: '2026-10-10',
  contentSha256: 'a'.repeat(64),
};
const service = {
  businessDisclosure: 'Confirmed business disclosures',
  businessAddress: 'Confirmed business address',
  accessibilityContact: 'Confirmed accessibility contact',
};
const section = { id: 'terms', title: 'Approved title', paragraphs: ['Approved wording'] };
const documents = {
  'terms.json': { version: '2026-10-18', sections: [section] },
  'acceptable-use.json': { sections: [{ ...section, items: ['Approved prohibition'] }] },
  'accessibility.json': {
    lastReviewed: '2026-10-18',
    nextReview: '2027-04-18',
    sections: [section],
  },
};
const problems = (overrides = {}) =>
  publicationProblems(ready(), approval, 'a'.repeat(64), service, { ...documents, ...overrides });
const ready = () => ({
  ...draft,
  operator: Object.fromEntries(
    Object.keys(draft.operator).map((key) => [key, 'Confirmed installation detail']),
  ),
  purposes: draft.purposes.map((row) => ({
    ...row,
    lawfulBasis: 'Confirmed basis and assessment',
  })),
});

test('the supplied draft cannot be published', () => {
  const problems = publicationProblems(
    draft,
    { approvedBy: null, approvedOn: null, contentSha256: null },
    'a'.repeat(64),
  );
  assert.ok(problems.some((problem) => problem.includes('controllerName')));
  assert.ok(problems.some((problem) => problem.includes('lawfulBasis')));
  assert.ok(problems.some((problem) => problem.includes('approval')));
});

test('requires complete details and an approval for the exact content', () => {
  assert.deepEqual(problems(), []);
  assert.ok(
    publicationProblems(ready(), approval, 'b'.repeat(64)).some((problem) =>
      problem.includes('changed'),
    ),
  );
  const notice = ready();
  notice.operator.controllerName = 'TODO: confirm';
  assert.ok(
    publicationProblems(notice, approval, 'a'.repeat(64)).some((problem) =>
      problem.includes('placeholder'),
    ),
  );
});

test('rejects invalid calendar approval dates consistently with the deployment check', () => {
  for (const approvedOn of ['2026-02-30', '0000-01-01', '2026-13-01', '2026-2-1', 'not a date'])
    assert.ok(
      publicationProblems(ready(), { ...approval, approvedOn }, 'a'.repeat(64)).some((problem) =>
        problem.includes('dated'),
      ),
    );
});

test('preview approval becomes false when approved content is edited', () => {
  const directory = mkdtempSync(join(tmpdir(), 'ase-policy-gate-'));
  try {
    writeFileSync(join(directory, 'privacy.json'), JSON.stringify(ready()));
    writeFileSync(join(directory, 'service.json'), JSON.stringify(service));
    writeFileSync(join(directory, 'storage.json'), '[]');
    writeFileSync(join(directory, 'attributions.generated.json'), '{}');
    for (const [name, document] of Object.entries(documents))
      writeFileSync(join(directory, name), JSON.stringify(document));
    writeFileSync(
      join(directory, 'approval.json'),
      JSON.stringify({ ...approval, contentSha256: policyHash(directory) }),
    );
    assert.equal(readPublicationState(directory).approved, true);
    writeFileSync(
      join(directory, 'service.json'),
      JSON.stringify({ ...service, businessDisclosure: 'Changed business disclosures' }),
    );
    assert.equal(readPublicationState(directory).approved, false);
    writeFileSync(join(directory, 'service.json'), JSON.stringify(service));
    assert.equal(readPublicationState(directory).approved, true);
    writeFileSync(join(directory, 'PrivacyPage.tsx'), 'changed visible text');
    assert.equal(readPublicationState(directory).approved, false);
    writeFileSync(join(directory, 'approval.json'), '{invalid');
    assert.equal(readPublicationState(directory).approved, false);
  } finally {
    rmSync(directory, { recursive: true });
  }
});

test('matching privacy approval cannot release incomplete service details', () => {
  for (const key of Object.keys(service)) {
    for (const value of [null, '', 'TBC', 'TODO: confirm']) {
      const problems = publicationProblems(ready(), approval, 'a'.repeat(64), {
        ...service,
        [key]: value,
      });
      assert.ok(problems.some((problem) => problem.includes(`service.${key}`)));
    }
  }
});

test('operator undecided wording cannot be released even with a matching approval', () => {
  for (const value of ['Not decided', 'Not yet confirmed', 'Not yet approved', 'To be confirmed']) {
    const notice = ready();
    notice.operator.hosting = value;
    assert.ok(publicationProblems(notice, approval, 'a'.repeat(64), service).length > 0);
    const purposeNotice = ready();
    purposeNotice.purposes[0].lawfulBasis = value;
    assert.ok(publicationProblems(purposeNotice, approval, 'a'.repeat(64), service).length > 0);
    assert.ok(
      publicationProblems(ready(), approval, 'a'.repeat(64), {
        ...service,
        businessAddress: value,
      }).length > 0,
    );
  }
});

test('structured documents block publication while any decision is pending', () => {
  const pending = { pending: 'Governing law and courts' };
  for (const [name, document] of Object.entries(documents)) {
    const withPending = {
      ...document,
      sections: [{ ...section, paragraphs: ['Approved wording', pending] }],
    };
    assert.ok(problems({ [name]: withPending }).some((problem) => problem.includes('decision')));
    const pendingItem = { ...document, sections: [{ ...section, items: [pending] }] };
    assert.ok(problems({ [name]: pendingItem }).some((problem) => problem.includes('decision')));
  }
});

test('structured documents need sections, wording and valid review dates', () => {
  for (const name of Object.keys(documents)) {
    assert.ok(problems({ [name]: undefined }).some((problem) => problem.includes(name)));
    assert.ok(problems({ [name]: { ...documents[name], sections: [] } }).length > 0);
    assert.ok(
      problems({ [name]: { ...documents[name], sections: [{ ...section, paragraphs: [] }] } })
        .length > 0,
    );
    assert.ok(
      problems({
        [name]: { ...documents[name], sections: [{ ...section, paragraphs: ['TBC'] }] },
      }).some((problem) => problem.includes('placeholder')),
    );
    assert.ok(
      problems({ [name]: { ...documents[name], sections: [{ ...section, items: 'list' }] } })
        .length > 0,
    );
  }
  for (const [name, key] of [
    ['terms.json', 'version'],
    ['accessibility.json', 'lastReviewed'],
    ['accessibility.json', 'nextReview'],
  ])
    for (const value of [undefined, '2026-02-30', 'soon'])
      assert.ok(
        problems({ [name]: { ...documents[name], [key]: value } }).some((problem) =>
          problem.includes(`dated ${name} ${key}`),
        ),
      );
});

test('the shipped documents keep their unresolved decisions visible to the gate', () => {
  const state = readPublicationState();
  assert.equal(state.approved, false);
  for (const name of ['terms.json', 'acceptable-use.json', 'accessibility.json'])
    assert.ok(state.problems.some((problem) => problem.includes(`decision in ${name}`)));
  assert.ok(state.problems.includes('Missing service.businessAddress'));
});

test('footer details expose only trimmed operator strings, or null', () => {
  const directory = mkdtempSync(join(tmpdir(), 'ase-policy-footer-'));
  try {
    writeFileSync(
      join(directory, 'privacy.json'),
      JSON.stringify({ operator: { controllerName: ' Operator ', controllerContact: 3 } }),
    );
    writeFileSync(join(directory, 'service.json'), JSON.stringify({ businessAddress: '' }));
    assert.deepEqual(footerDetails(directory), {
      operator: 'Operator',
      contact: null,
      address: null,
    });
    writeFileSync(join(directory, 'service.json'), '{invalid');
    assert.deepEqual(footerDetails(directory), { operator: null, contact: null, address: null });
  } finally {
    rmSync(directory, { recursive: true });
  }
});
