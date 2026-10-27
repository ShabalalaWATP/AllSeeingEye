import { accessibilityStatement, serviceDetails } from './content';
import { DraftNotice } from './DraftNotice';
import { PolicyDocumentView } from './PolicyDocumentView';
import { PolicyLayout } from './PolicyLayout';
import { formatPolicyDate } from './policyDates';

/** Follows the structure of the GOV.UK sample accessibility statement. */
export default function AccessibilityPage() {
  const { lastReviewed, nextReview, sections } = accessibilityStatement;
  return (
    <PolicyLayout title="Accessibility">
      <DraftNotice />
      <p className="policy-meta">
        Accessibility statement, last reviewed on{' '}
        <time dateTime={lastReviewed}>{formatPolicyDate(lastReviewed)}</time>.
      </p>
      <PolicyDocumentView
        sections={sections}
        lead={{
          feedback: (
            <p className="whitespace-pre-line">
              {serviceDetails.accessibilityContact ??
                'The operator has not yet confirmed an accessibility contact. This blocks publication.'}
            </p>
          ),
          enforcement: (
            <p>
              <a href="https://saavutettavuusvaatimukset.fi/en/submit-complaint-web-accessibility-or-request-clarification">
                Traficom accessibility complaints and requests for clarification
              </a>
            </p>
          ),
          preparation: (
            <p>
              Last reviewed on <time dateTime={lastReviewed}>{formatPolicyDate(lastReviewed)}</time>
              . The next review is due by{' '}
              <time dateTime={nextReview}>{formatPolicyDate(nextReview)}</time>.
            </p>
          ),
        }}
      />
    </PolicyLayout>
  );
}
