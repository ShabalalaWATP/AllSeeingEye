import { privacyNotice } from './content';
import { PolicyLayout, PolicySection } from './PolicyLayout';

export default function PersonalDataPage() {
  const procedure = privacyNotice.requestProcedure;
  return (
    <PolicyLayout title="Personal-data requests">
      <p>
        The installation uses an operator-assisted procedure, approved on {procedure.approvedOn}. It
        covers selected supported actions and does not promise complete account erasure.
      </p>
      <PolicySection id="contact" title="Contact the administrator">
        <p>
          Email <a href={`mailto:${procedure.contact}`}>{procedure.contact}</a> privately to request
          a copy, correction or removal of personal data.
        </p>
        <p>
          This is the approved request-handling contact. The draft privacy notice separately
          identifies controller and complaints details still awaiting confirmation.
        </p>
      </PolicySection>
      <PolicySection id="procedure" title="What happens next">
        <ol>
          {procedure.steps.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
        <p>
          <a href={procedure.source} rel="noreferrer">
            Read the full operator procedure and current capability inventory
          </a>
          .
        </p>
      </PolicySection>
    </PolicyLayout>
  );
}
