import { Link } from 'react-router';

import { Wordmark } from '@/components/brand/Wordmark';

import { NOT_FOUND_TITLE } from './shell/pageTitles';
import { PublicRouteFocus } from './shell/PublicRouteFocus';

export function NotFoundPage() {
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center gap-4 bg-ground p-6 text-center">
      <PublicRouteFocus title={NOT_FOUND_TITLE} />
      <Wordmark />
      <h1 className="text-2xl font-semibold">{NOT_FOUND_TITLE}</h1>
      <p className="text-sm text-muted">There is nothing at this address.</p>
      <Link to="/" className="text-sm text-ember hover:underline">
        Back to the globe
      </Link>
    </main>
  );
}
