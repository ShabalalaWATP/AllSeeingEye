/**
 * Chapter 10: Talk to us. Enquiries are independent of account provisioning and
 * appear only when this installation accepts them.
 */
import { Link } from 'react-router';

import { ProductBrandMark } from '../ProductMotionControls';
import { EnterpriseEnquiryForm } from '../enquiry/EnterpriseEnquiryForm';
import '../enquiry/enquiry.css';

import { Reveal } from '../motion/Reveal';

export function ContactChapter({ enquiriesEnabled = false }: { enquiriesEnabled?: boolean }) {
  return (
    <section id="contact" aria-label="Talk to us" className="story-chapter story-contact">
      <div className="contact-glow" aria-hidden="true" />
      <Reveal className="contact-inner">
        <ProductBrandMark size={56} />
        <p className="story-eyebrow">10 · Talk to us</p>
        <h2 className="story-title">Bring The All Seeing Eye inside your organisation.</h2>
        <p className="story-lead">
          Tell us about your team, where it needs to run and the questions you need answered. We
          will help you plan the deployment, connect your AI provider and choose sources whose terms
          fit your use.
        </p>
        <div className="hero-actions">
          <Link className="story-button story-button-primary" to="/request-account">
            Request access
          </Link>
          <Link className="story-button" to="/login">
            Sign in
          </Link>
        </div>
        {enquiriesEnabled ? <EnterpriseEnquiryForm /> : null}
      </Reveal>
    </section>
  );
}
