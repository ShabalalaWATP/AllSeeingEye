import { Link, useRouteError } from 'react-router';

import { Wordmark } from '@/components/brand/Wordmark';
import { Button } from '@/components/ui/Button';
import { isStaleBuildError, reloadPage } from '@/lib/pageRecovery';

/** Recovery inside a layout, so its navigation stays usable. The raw error is never shown. */
export function RouteErrorPanel() {
  return (
    <section className="flex min-h-full flex-col items-center justify-center gap-4 p-6 text-center">
      <Recovery />
    </section>
  );
}

/** Last resort when a layout itself could not render. */
export function RouteErrorPage() {
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center gap-4 bg-ground p-6 text-center">
      <Wordmark />
      <Recovery />
    </main>
  );
}

function Recovery() {
  // Code removed by a newer deploy cannot load again without fetching the new build.
  const stale = isStaleBuildError(useRouteError());
  return (
    <>
      <h1 className="text-2xl font-semibold">
        {stale ? 'A newer version is available' : 'This page could not load'}
      </h1>
      <p className="max-w-md text-sm text-muted">
        {stale
          ? 'The app was updated while this page was open. Reload to continue with the latest version.'
          : 'Something went wrong while showing this page. Reload to try again, or go back to the map.'}
      </p>
      <div className="flex flex-wrap items-center justify-center gap-4">
        <Button onClick={() => reloadPage()}>Reload</Button>
        {!stale && (
          <Link to="/" className="text-sm text-ember hover:underline">
            Back to map
          </Link>
        )}
      </div>
    </>
  );
}
