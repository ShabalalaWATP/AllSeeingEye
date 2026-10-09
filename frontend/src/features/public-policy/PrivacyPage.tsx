import { Link } from 'react-router';

import { noticeApproved, privacyNotice, storageDeclaration } from './content';
import { PolicyLayout, PolicySection } from './PolicyLayout';
import { usePublicRetention } from './usePublicRetention';

const operatorLabels: Record<string, string> = {
  controllerName: 'Controller identity',
  controllerContact: 'Controller contact',
  complaintsContact: 'Data protection complaints contact',
  complaintsProcedure: 'Complaints handling procedure',
  jurisdiction: 'Applicable jurisdictions and representatives',
  hosting: 'Hosting provider and location',
  emailProvider: 'Email provider',
  aiProviders: 'Configured AI providers',
  otherRecipients: 'Other recipients',
  internationalTransfers: 'International transfers and safeguards',
  retentionCriteria: 'Retention periods and criteria',
  publicSourceAssessment: 'Public-source material and indirect collection',
  storageAssessment: 'Storage and consent assessment',
  automatedDecisions: 'Automated decisions and profiling',
};

export default function PrivacyPage() {
  const retention = usePublicRetention();
  return (
    <PolicyLayout title="Privacy and storage">
      {!noticeApproved && (
        <aside className="policy-draft" aria-label="Draft notice">
          <strong>Draft for review. Publication is blocked.</strong>
          <p>
            Installation details and legal wording remain unapproved. The technical descriptions
            below do not establish legal compliance.
          </p>
        </aside>
      )}
      <p>
        Notice version: {privacyNotice.version}. This page describes the application and identifies
        decisions the installation operator must confirm.
      </p>
      <nav aria-label="On this page">
        <ul>
          <li>
            <a href="#operator">Controller and installation</a>
          </li>
          <li>
            <a href="#purposes">Information and purposes</a>
          </li>
          <li>
            <a href="#retention">Retention</a>
          </li>
          <li>
            <a href="#storage">Cookies and browser storage</a>
          </li>
          <li>
            <a href="#rights">Rights, requests and complaints</a>
          </li>
        </ul>
      </nav>
      <PolicySection id="operator" title="Controller and installation">
        <dl>
          {Object.entries(operatorLabels).map(([key, label]) => (
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
      <PolicySection id="purposes" title="Information and purposes">
        {privacyNotice.purposes.map((purpose) => (
          <section key={purpose.name}>
            <h3>{purpose.name}</h3>
            <p>{purpose.data}</p>
            <p>{purpose.purpose}</p>
            <p>
              <strong>Lawful basis: </strong>
              {purpose.lawfulBasis ??
                'Not yet approved for this installation. This blocks publication.'}
            </p>
          </section>
        ))}
      </PolicySection>
      <PolicySection id="public-sources" title="People in public-source material">
        <p>{privacyNotice.publicSources}</p>
        <p>
          <Link to="/attributions">Source attributions</Link> identify supported source products and
          their recorded terms. Inclusion is not proof that a source is enabled or that reuse is
          authorised.
        </p>
      </PolicySection>
      <PolicySection id="retention" title="Retention">
        <p>
          The table describes implemented behaviour. It is not a complete approved retention policy.
        </p>
        <div className="policy-table">
          <table>
            <caption className="sr-only">Data retention and current limitations</caption>
            <thead>
              <tr>
                <th scope="col">Data</th>
                <th scope="col">Current behaviour</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <th scope="row">Enterprise enquiries</th>
                <td>
                  {retention.status === 'loading'
                    ? 'Loading the installation’s public retention setting…'
                    : retention.status === 'ready'
                      ? `This installation is configured for ${retention.days} days from submission. Expired enquiries are excluded from administration immediately; background deletion runs in bounded batches.`
                      : 'The installation’s current retention setting could not be loaded. Ask the operator to confirm it; no default is presented as the live value.'}{' '}
                  Email copies and backups are separate. Changing enquiry status does not restart
                  the retention period.
                </td>
              </tr>
              {privacyNotice.retention.map((row) => (
                <tr key={row.name}>
                  <th scope="row">{row.name}</th>
                  <td>{row.behaviour}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </PolicySection>
      <PolicySection id="storage" title="Cookies and browser storage">
        <p>
          These are application-owned cookies and local-storage keys. Local storage is per browser
          and can outlast sign-out. Clearing it does not delete your account or server records.
          Private research form drafts remain in page memory.
        </p>
        <dl>
          {storageDeclaration.map((item) => (
            <div key={item.name}>
              <dt>
                <code>{item.name}</code> ({item.kind})
              </dt>
              <dd>
                {item.purpose} {item.contents} {item.duration}
              </dd>
            </div>
          ))}
        </dl>
        <p>
          Web push requires an explicit enable action and browser permission. Disable it in
          notification settings, remove the registered device and review your browser’s site
          permissions. A service worker receives push events; the application does not use it as an
          offline research cache.
        </p>
      </PolicySection>
      <PolicySection id="external-media" title="Maps, cameras and external media">
        <p>{privacyNotice.externalMedia}</p>
        <p>
          The default hybrid map uses EOX imagery and OpenFreeMap tiles and labels, derived in part
          from OpenStreetMap. Other selected overlays and camera streams have their own hosts. The
          privacy and attribution pages load no map, camera, video or market widget.
        </p>
      </PolicySection>
      <PolicySection id="rights" title="Rights, requests and complaints">
        <p>{privacyNotice.rights}</p>
        <p>
          <Link to="/privacy/requests">Follow the personal-data request procedure</Link> for the
          approved administrator contact and the supported actions.
        </p>
        <p>
          The operator must confirm the separate data protection complaints contact and handling
          procedure shown above before publication. You can also{' '}
          <a href="https://ico.org.uk/make-a-complaint/" rel="noreferrer">
            raise a concern with the Information Commissioner’s Office
          </a>
          . The appropriate regulator depends on your circumstances and applicable law.
        </p>
      </PolicySection>
      <PolicySection id="references" title="Reference information">
        <ul>
          {privacyNotice.references.map((reference) => (
            <li key={reference.url}>
              <a href={reference.url} rel="noreferrer">
                {reference.label}
              </a>
            </li>
          ))}
        </ul>
      </PolicySection>
    </PolicyLayout>
  );
}
