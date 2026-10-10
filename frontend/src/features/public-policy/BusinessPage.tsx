import { privacyNotice, serviceDetails } from './content';
import { DraftNotice } from './DraftNotice';
import { PolicyLayout, PolicySection } from './PolicyLayout';

export default function BusinessPage() {
  return (
    <PolicyLayout title="Business details">
      <DraftNotice />
      <p>
        These details identify the operator responsible for this installation. No company identity
        or commercial offer is inferred from the application name.
      </p>
      <PolicySection id="operator" title="Installation operator">
        <dl>
          {(
            [
              ['controllerName', 'Controller identity'],
              ['controllerContact', 'Operator contact'],
              ['jurisdiction', 'Applicable jurisdictions and representatives'],
            ] as const
          ).map(([key, label]) => (
            <div key={key}>
              <dt>{label}</dt>
              <dd>
                {privacyNotice.operator[key] ??
                  'Not yet confirmed by the operator. This blocks publication.'}
              </dd>
            </div>
          ))}
        </dl>
      </PolicySection>
      <PolicySection id="business-disclosures" title="Registered address and business disclosures">
        <p className="whitespace-pre-line">
          {serviceDetails.businessDisclosure ??
            'The operator has not yet confirmed the applicable business identity, address and registration disclosures. This blocks publication.'}
        </p>
      </PolicySection>
    </PolicyLayout>
  );
}
