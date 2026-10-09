import { Button } from '@/components/ui/Button';
import { embedProviderIds, embedProviders } from '@/lib/embedProviders';
import { useEmbedConsentStore } from '@/stores/embedConsent';

export function EmbedPrivacyPreferences() {
  const { choices, forget, error } = useEmbedConsentStore();
  return (
    <section aria-labelledby="external-media-heading" className="space-y-4">
      <h2 id="external-media-heading" className="text-xl font-semibold">
        External media
      </h2>
      <p className="text-sm text-muted">
        Charts and embedded videos connect directly to their providers after you choose to load
        them. Remembered choices allow later embeds from the same provider. Cameras still require
        Play. Browser choices apply to everyone using this browser, until you forget them or clear
        site data.
      </p>
      <ul className="divide-y divide-line">
        {embedProviderIds.map((provider) => (
          <li key={provider} className="flex flex-wrap items-center justify-between gap-3 py-3">
            <span>
              {embedProviders[provider].name}:{' '}
              {choices[provider] === 'browser'
                ? 'remembered in this browser'
                : choices[provider] === 'session'
                  ? 'remembered until reload or sign-out'
                  : 'ask before loading'}
            </span>
            <Button variant="secondary" onClick={() => forget(provider)}>
              Forget {embedProviders[provider].name} choice
            </Button>
          </li>
        ))}
      </ul>
      {error && <p role="alert">{error}</p>}
      <p className="text-sm text-muted">
        Forgetting a choice stops open embeds and blocks future loads here. It cannot undo
        information already sent or remove cookies held by the provider. Direct camera images and
        streams also share your IP address with their provider when you choose Load image or Play
        video.
      </p>
    </section>
  );
}
