import { Link } from 'react-router';
import footer from 'virtual:policy-footer';

const linkClass =
  'rounded-sm underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-4';

const LINKS = [
  ['/privacy', 'Privacy and storage'],
  ['/privacy/requests', 'Personal-data requests'],
  ['/attributions', 'Source attributions'],
  ['/accessibility', 'Accessibility'],
  ['/terms', 'Terms'],
  ['/acceptable-use', 'Acceptable use'],
  ['/business', 'Business details'],
] as const;

/** The operator line from the same reviewed content as /business; plain text, never HTML. */
function businessLine(): string {
  const parts = [
    `Operated by ${footer.operator ?? 'an operator not yet confirmed'}`,
    footer.contact,
    footer.address ?? 'Business address awaiting the operator’s decision',
  ];
  return parts.filter((part): part is string => part !== null).join(' · ');
}

/**
 * Same-origin links only; safe in public and signed-in layouts. The shared legal footer also
 * names the operator, unless a layout shows these links twice and turns that off for one.
 */
export function PolicyLinks({
  label = 'Privacy and source information',
  business = true,
}: {
  label?: string;
  business?: boolean;
}) {
  return (
    <>
      <nav aria-label={label} className="flex flex-wrap gap-x-5 gap-y-2 text-sm">
        {LINKS.map(([to, name]) => (
          <Link key={to} className={linkClass} to={to}>
            {name}
          </Link>
        ))}
      </nav>
      {business ? <p className="mt-2 text-xs">{businessLine()}</p> : null}
    </>
  );
}
