import type { ReactNode } from 'react';

import type { PolicyDocumentSection, PolicyWording } from './content';
import { PolicySection } from './PolicyLayout';

/** A decision the operator has not made stays visible on the page and blocks publication. */
function Wording({ value }: { value: PolicyWording }) {
  if (typeof value === 'string') return <>{value}</>;
  return (
    <span className="policy-pending">
      <strong>Decision needed:</strong> {value.pending} This blocks publication.
    </span>
  );
}

function key(value: PolicyWording): string {
  return typeof value === 'string' ? value : `pending:${value.pending}`;
}

/**
 * Structured policy text rendered as React text; nothing in the content is parsed as HTML.
 * `lead` places reviewed content from elsewhere, such as a contact, at the start of a section.
 */
export function PolicyDocumentView({
  sections,
  lead = {},
}: {
  sections: readonly PolicyDocumentSection[];
  lead?: Readonly<Record<string, ReactNode>>;
}) {
  return sections.map((section) => (
    <PolicySection key={section.id} id={section.id} title={section.title}>
      {lead[section.id]}
      {section.paragraphs.map((paragraph) => (
        <p key={key(paragraph)}>
          <Wording value={paragraph} />
        </p>
      ))}
      {section.items === undefined ? null : (
        <ul>
          {section.items.map((item) => (
            <li key={key(item)}>
              <Wording value={item} />
            </li>
          ))}
        </ul>
      )}
    </PolicySection>
  ));
}
