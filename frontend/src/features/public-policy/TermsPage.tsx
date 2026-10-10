import { Link } from 'react-router';

import { serviceDetails } from './content';
import { DraftNotice } from './DraftNotice';
import { PolicyLayout, PolicySection } from './PolicyLayout';

export default function TermsPage() {
  return (
    <PolicyLayout title="Terms">
      <DraftNotice />
      <PolicySection id="service-terms" title="Installation terms">
        {serviceDetails.terms ? (
          <p className="whitespace-pre-line">{serviceDetails.terms}</p>
        ) : (
          <p>
            No software licence or deployment offer is granted by this draft. The operator must
            supply and approve the installation's terms before publication.
          </p>
        )}
      </PolicySection>
      <p>
        <Link to="/business">Business details</Link> identifies the operator.{' '}
        <Link to="/privacy">Privacy and storage</Link> describes information handling.{' '}
        <Link to="/attributions">Source attributions</Link> records source-specific conditions; a
        credit alone does not grant permission to reuse material.
      </p>
    </PolicyLayout>
  );
}
