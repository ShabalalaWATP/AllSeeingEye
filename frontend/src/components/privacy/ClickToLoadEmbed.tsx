import { useRef, useState, type ReactNode } from 'react';

import { Button } from '@/components/ui/Button';
import { embedProviders, type EmbedProvider } from '@/lib/embedProviders';
import { useEmbedConsentStore } from '@/stores/embedConsent';

/** Children mount only with consent. Cameras still require Play on every new selection. */
export function ClickToLoadEmbed({
  provider,
  content,
  children,
}: {
  provider: EmbedProvider;
  content: 'chart' | 'video';
  children: (loadedHere: boolean) => ReactNode;
}) {
  const { choices, revisions, error, remember, forget } = useEmbedConsentStore();
  const [grant, setGrant] = useState<{ provider: EmbedProvider; revision: number } | null>(null);
  const [rememberChoice, setRememberChoice] = useState(false);
  const [persistent, setPersistent] = useState(false);
  const focusNextControl = useRef(false);
  const retainFocus = (node: HTMLButtonElement | null) => {
    if (node && focusNextControl.current) {
      node.focus();
      focusNextControl.current = false;
    }
  };
  const details = embedProviders[provider];
  const loadedHere = grant?.provider === provider && grant.revision === revisions[provider];
  const allowed = choices[provider] !== null || loadedHere;

  return (
    <div className="space-y-3 rounded border border-line bg-surface/40 p-4 text-sm text-text">
      <p>
        Loading this {content} connects your browser to {details.name}, which receives{' '}
        {details.shared} and may set cookies.{' '}
        <a
          className="text-cyan underline underline-offset-4"
          href={details.privacyUrl}
          target="_blank"
          rel="noopener noreferrer"
        >
          {details.name} privacy policy
        </a>
      </p>
      {allowed ? (
        <>
          <div className="flex flex-wrap items-center gap-3">
            <p className="text-muted">
              {choices[provider] === 'browser'
                ? `Remembered for ${details.name} in this browser, including other accounts.`
                : choices[provider] === 'session'
                  ? `Remembered for ${details.name} until you reload or sign out.`
                  : `Allowed for this ${content} only.`}
            </p>
            <Button
              ref={retainFocus}
              className="min-h-11"
              variant="secondary"
              onClick={() => {
                focusNextControl.current = true;
                forget(provider);
              }}
            >
              {choices[provider] ? `Forget ${details.name} choice` : `Block ${details.name}`}
            </Button>
          </div>
          {children(loadedHere)}
        </>
      ) : (
        <>
          <label className="flex min-h-11 items-center gap-3">
            <input
              type="checkbox"
              checked={rememberChoice}
              onChange={(event) => {
                setRememberChoice(event.target.checked);
                if (!event.target.checked) setPersistent(false);
              }}
            />
            Remember for {details.name} until I reload or sign out
          </label>
          {rememberChoice && (
            <label className="flex min-h-11 items-center gap-3">
              <input
                type="checkbox"
                checked={persistent}
                onChange={(event) => setPersistent(event.target.checked)}
              />
              Also save this choice in this browser, including for other accounts
            </label>
          )}
          <Button
            ref={retainFocus}
            className="min-h-11"
            onClick={() => {
              focusNextControl.current = true;
              if (rememberChoice) remember(provider, persistent);
              setGrant({ provider, revision: revisions[provider] });
              setRememberChoice(false);
              setPersistent(false);
            }}
          >
            Load {content} from {details.name}
          </Button>
        </>
      )}
      {error && <p role="alert">{error}</p>}
    </div>
  );
}
