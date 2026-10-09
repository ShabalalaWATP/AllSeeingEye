import type { ReactNode } from 'react';
import { Link } from 'react-router';

import { PublicRouteFocus } from '@/app/shell/PublicRouteFocus';
import { PolicyLinks } from '@/components/privacy/PolicyLinks';

import './policy.css';

export function PolicyLayout({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="policy-page">
      <a className="policy-skip" href="#policy-main">
        Skip to content
      </a>
      <header className="policy-header">
        <Link to="/login">The All Seeing Eye</Link>
        <PolicyLinks />
      </header>
      <main id="policy-main" tabIndex={-1}>
        <PublicRouteFocus title={title} />
        <h1>{title}</h1>
        {children}
      </main>
      <footer className="policy-footer">
        <PolicyLinks />
      </footer>
    </div>
  );
}

export function PolicySection({
  id,
  title,
  children,
}: {
  id: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <section id={id} aria-labelledby={`${id}-title`}>
      <h2 id={`${id}-title`}>{title}</h2>
      {children}
    </section>
  );
}
