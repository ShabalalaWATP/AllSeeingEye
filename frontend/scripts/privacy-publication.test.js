import assert from 'node:assert/strict';
import { readFileSync, mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';

import { policyHash, publicationProblems, readPublicationState } from './privacy-publication.js';

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
  terms: 'Approved installation terms',
  businessDisclosure: 'Confirmed business disclosures',
  accessibilityContact: 'Confirmed accessibility contact',
};
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
  assert.deepEqual(publicationProblems(ready(), approval, 'a'.repeat(64), service), []);
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
    writeFileSync(
      join(directory, 'approval.json'),
      JSON.stringify({ ...approval, contentSha256: policyHash(directory) }),
    );
    assert.equal(readPublicationState(directory).approved, true);
    writeFileSync(
      join(directory, 'service.json'),
      JSON.stringify({ ...service, terms: 'Changed installation terms' }),
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
