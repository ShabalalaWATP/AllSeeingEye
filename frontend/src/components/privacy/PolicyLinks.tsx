import { Link } from 'react-router';

/** Same-origin links only; safe in public and signed-in layouts. */
export function PolicyLinks({ label = 'Privacy and source information' }: { label?: string }) {
  return (
    <nav aria-label={label} className="flex flex-wrap gap-x-5 gap-y-2 text-sm">
      <Link
        className="rounded-sm underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-4"
        to="/privacy"
      >
        Privacy and storage
      </Link>
      <Link
        className="rounded-sm underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-4"
        to="/privacy/requests"
      >
        Personal-data requests
      </Link>
      <Link
        className="rounded-sm underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-4"
        to="/attributions"
      >
        Source attributions
      </Link>
    </nav>
  );
}
