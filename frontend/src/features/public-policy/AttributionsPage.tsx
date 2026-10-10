import register from './attributions.generated.json';
import { PolicyLayout, PolicySection } from './PolicyLayout';

export default function AttributionsPage() {
  const families = [...new Set(register.sources.map((source) => source.family))].sort();
  return (
    <PolicyLayout title="Source attributions">
      <p>
        Credits for all supported catalogue sources, including optional sources. This is a superset
        of the sources an installation may enable; it does not reveal live source configuration. The
        register was assessed on {register.assessedOn}.
      </p>
      <p>
        A credit is not permission to use a source. Unknown or restricted rights remain unresolved,
        and source-specific and enrichment conditions both apply. Preserve the original record’s
        author, date, link and any additional credits when using evidence.
      </p>
      <nav aria-label="Source categories">
        <p>
          The application may filter, normalise, combine and summarise source material. Derived
          displays and assessments are not the provider’s original publication.
        </p>
        <ul>
          {families.map((family) => (
            <li key={family}>
              <a href={`#${family}`}>{family.replaceAll('_', ' ')}</a>
            </li>
          ))}
        </ul>
      </nav>
      {families.map((family) => (
        <PolicySection key={family} id={family} title={family.replaceAll('_', ' ')}>
          {register.sources
            .filter((source) => source.family === family)
            .map((source) => (
              <details key={source.id}>
                <summary>{source.name}</summary>
                <p>
                  {source.sourceUrl ? (
                    <a href={source.sourceUrl} rel="noreferrer">
                      Source or publisher
                    </a>
                  ) : (
                    'Original source varies by item.'
                  )}{' '}
                  <code>{source.id}</code>
                </p>
                <dl>
                  {source.policies.map((policy) => (
                    <div key={policy.id}>
                      <dt>{policy.name}</dt>
                      <dd>
                        <p>
                          {policy.licence}. {policy.attribution}
                        </p>
                        <p>
                          Review status: {policy.reviewStatus.replaceAll('_', ' ')}.{' '}
                          {policy.checkedOn
                            ? `Terms checked ${policy.checkedOn}.`
                            : 'Applicable terms have not been fully verified.'}
                        </p>
                        {policy.termsUrl && (
                          <p>
                            <a href={policy.termsUrl} rel="noreferrer">
                              {policy.checkedOn
                                ? 'Terms and evidence'
                                : 'Provider reference, not a verified grant'}
                            </a>
                          </p>
                        )}
                        {policy.additionalTermsUrls.length > 0 && (
                          <ul>
                            {policy.additionalTermsUrls.map((url, index) => (
                              <li key={url}>
                                <a href={url} rel="noreferrer">
                                  Additional terms reference {index + 1}
                                </a>
                              </li>
                            ))}
                          </ul>
                        )}
                      </dd>
                    </div>
                  ))}
                </dl>
              </details>
            ))}
        </PolicySection>
      ))}
    </PolicyLayout>
  );
}
