/** Public account pages: a live brand plane beside a quiet, opaque form. */
import { Link, NavLink, Outlet } from 'react-router';

import { PublicRouteFocus } from '@/app/shell/PublicRouteFocus';
import EvilEye from '@/components/brand/EvilEye';
import { MotionToggle } from '@/components/brand/MotionToggle';
import { useMotionPause } from '@/components/brand/useMotionPause';
import { usePageVisible, useReducedMotion } from '@/components/brand/useMotionPreferences';
import { useSiteFacts } from '@/lib/useSiteFacts';

import './auth.css';

export function AuthLayout() {
  const reducedMotion = useReducedMotion();
  const visible = usePageVisible();
  const { chosenPause } = useMotionPause();
  const site = useSiteFacts();
  const productPage = site.status === 'ready' && site.facts.product_page_enabled;

  return (
    <div className="auth-shell">
      <section className="auth-brand" aria-label="The All Seeing Eye">
        <div className="auth-grid" aria-hidden="true" />
        <p className="auth-eyebrow">Open-source intelligence</p>
        <MotionToggle tone="auth" className="absolute top-6 right-6 flex flex-col items-end" />
        <div className="auth-identity">
          <div className="auth-eye" aria-hidden="true" data-testid="auth-backdrop">
            <EvilEye
              backgroundColor="#060606"
              scale={0.9}
              maxFps={reducedMotion ? 1 : 24}
              flameSpeed={reducedMotion ? 0 : 1}
              pupilFollow={reducedMotion ? 0 : 1}
              paused={!visible || chosenPause}
              fallbackSizes="(max-width: 480px) 180px, (max-width: 899px) 240px, 480px"
            />
          </div>
          <div className="auth-brand-copy">
            <p className="auth-brand-name">
              The All Seeing Eye<span>.</span>
            </p>
            <p className="auth-brand-description">AI-assisted OSINT collection and analysis.</p>
            {productPage ? (
              <Link className="auth-discover" to="/enterprise">
                Discover what it can do
              </Link>
            ) : null}
          </div>
        </div>
        <div className="auth-brand-footer" aria-hidden="true">
          <span>ASE / RESEARCH</span>
          <span>OBSERVE · CONNECT · ASSESS</span>
        </div>
      </section>
      <main className="auth-access" id="account-access">
        <PublicRouteFocus />
        <div className="auth-access-inner">
          <nav className="auth-navigation" aria-label="Account access">
            <NavLink to="/login">Sign in</NavLink>
            <NavLink to="/request-account">Sign up</NavLink>
          </nav>
          <div className="auth-form">
            <Outlet />
          </div>
        </div>
      </main>
    </div>
  );
}
