import { Link } from 'react-router';

import { Wordmark } from '@/components/brand/Wordmark';

export function NotFoundPage() {
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center gap-4 bg-ground p-6 text-center">
      <Wordmark />
      <h1 className="text-2xl font-semibold">Page not found</h1>
      <p className="text-sm text-muted">There is nothing at this address.</p>
      <Link to="/" className="text-sm text-ember hover:underline">
        Back to the globe
      </Link>
    </main>
  );
}
