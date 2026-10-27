import { Link } from 'react-router';

import { termsDocument } from './content';
import { DraftNotice } from './DraftNotice';
import { PolicyDocumentView } from './PolicyDocumentView';
import { PolicyLayout } from './PolicyLayout';
import { formatPolicyDate } from './policyDates';

export default function TermsPage() {
  return (
    <PolicyLayout title="Terms">
      <DraftNotice />
      <p className="policy-meta">
        Version of{' '}
        <time dateTime={termsDocument.version}>{formatPolicyDate(termsDocument.version)}</time>.
        Read these terms with the <Link to="/acceptable-use">Acceptable Use Policy</Link>.
      </p>
      <PolicyDocumentView sections={termsDocument.sections} />
      <p>
        <Link to="/business">Business details</Link> identifies the operator.{' '}
        <Link to="/privacy">Privacy and storage</Link> describes information handling.{' '}
        <Link to="/attributions">Source attributions</Link> records source-specific conditions; a
        credit alone does not grant permission to reuse material.
      </p>
    </PolicyLayout>
  );
}
