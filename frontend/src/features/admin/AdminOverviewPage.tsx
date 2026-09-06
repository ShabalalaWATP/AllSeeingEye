import { Link } from 'react-router';

import { adminSections } from '@/lib/adminNavigation';

export default function AdminOverviewPage() {
  return (
    <section className="h-full overflow-y-auto px-5 py-8 sm:px-8 lg:px-12 lg:py-10">
      <div className="max-w-4xl">
        <p className="mb-3 font-mono text-xs uppercase tracking-widest text-muted">
          Administrator workspace
        </p>
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Administration</h1>
        <p className="mt-4 max-w-2xl text-sm leading-6 text-muted">
          Manage access, configure the services used by researchers and review administrative
          activity. Changes here can affect people across the application.
        </p>
        <div className="mt-9 border-t border-line">
          {adminSections.map((section) => (
            <section
              key={section.title}
              aria-label={section.title}
              className="border-b border-line py-6 md:grid md:grid-cols-[11rem_1fr] md:gap-8"
            >
              <h2 className="mb-4 text-sm font-semibold md:mb-0 md:pt-3">{section.title}</h2>
              <div>
                {section.items.map((item) => (
                  <Link
                    key={item.to}
                    to={item.to}
                    className="group flex items-start justify-between gap-4 rounded-md px-3 py-3 hover:bg-surface-2 focus-visible:bg-surface-2"
                  >
                    <span>
                      <span className="block text-sm font-medium">{item.label}</span>
                      <span className="mt-1 block text-sm leading-6 text-muted">
                        {item.description}
                      </span>
                    </span>
                    <span aria-hidden="true" className="pt-1 text-muted group-hover:text-text">
                      →
                    </span>
                  </Link>
                ))}
              </div>
            </section>
          ))}
        </div>
      </div>
    </section>
  );
}
