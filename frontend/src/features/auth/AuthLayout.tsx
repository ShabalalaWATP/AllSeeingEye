/** Public account pages: a live brand plane beside a quiet, opaque form. */
import { NavLink, Outlet } from 'react-router';

import EvilEye from '@/components/brand/EvilEye';
import { usePageVisible, useReducedMotion } from '@/components/brand/useMotionPreferences';

import './auth.css';

export function AuthLayout() {
  const reducedMotion = useReducedMotion();
  const visible = usePageVisible();

  return (
    <div className="auth-shell">
      <section className="auth-brand" aria-label="The All Seeing Eye">
        <div className="auth-grid" aria-hidden="true" />
        <p className="auth-eyebrow">Open-source intelligence</p>
        <div className="auth-identity">
          <div className="auth-eye" aria-hidden="true" data-testid="auth-backdrop">
            <EvilEye
              backgroundColor="#060606"
              scale={0.72}
              maxFps={reducedMotion ? 1 : 24}
              flameSpeed={reducedMotion ? 0 : 1}
              pupilFollow={reducedMotion ? 0 : 1}
              paused={!visible}
            />
          </div>
          <div className="auth-brand-copy">
            <p className="auth-brand-name">
              The All Seeing Eye<span>.</span>
            </p>
            <p className="auth-brand-description">AI-assisted OSINT collection and analysis.</p>
          </div>
        </div>
        <div className="auth-brand-footer" aria-hidden="true">
          <span>ASE / RESEARCH</span>
          <span>OBSERVE · CONNECT · ASSESS</span>
        </div>
      </section>
      <main className="auth-access" id="account-access">
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
