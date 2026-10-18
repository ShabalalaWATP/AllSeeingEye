import { Link } from 'react-router';

import { acceptableUseDocument, termsDocument } from './content';
import { DraftNotice } from './DraftNotice';
import { PolicyDocumentView } from './PolicyDocumentView';
import { PolicyLayout } from './PolicyLayout';
import { formatPolicyDate } from './policyDates';

export default function AcceptableUsePage() {
  return (
    <PolicyLayout title="Acceptable Use Policy">
      <DraftNotice />
      <p className="policy-meta">
        Part of the <Link to="/terms">Terms</Link>, version of{' '}
        <time dateTime={termsDocument.version}>{formatPolicyDate(termsDocument.version)}</time>.
      </p>
      <PolicyDocumentView sections={acceptableUseDocument.sections} />
    </PolicyLayout>
  );
}
