/**
 * Chapter 10: Talk to us. Enquiries are independent of account provisioning and
 * appear only when this installation accepts them. Once an enquiry is received the
 * Eye closes softly; a still story keeps it open and unchanged.
 */
import { useState } from 'react';
import { Link } from 'react-router';

import { ProductBrandMark } from '../ProductMotionControls';
import { EnterpriseEnquiryForm } from '../enquiry/EnterpriseEnquiryForm';
import '../enquiry/enquiry.css';

import { Reveal } from '../motion/Reveal';
import { useStoryMotion } from '../motion/useStoryMotion';

export function ContactChapter({ enquiriesEnabled = false }: { enquiriesEnabled?: boolean }) {
  const { still } = useStoryMotion();
  const [received, setReceived] = useState(false);
  return (
    <section id="contact" aria-label="Talk to us" className="story-chapter story-contact">
      <div className="contact-glow" aria-hidden="true" />
      <Reveal className="contact-inner">
        <div
          className="contact-eye"
          data-testid="contact-eye"
          data-closed={received && !still ? 'true' : undefined}
        >
          <ProductBrandMark size={56} />
        </div>
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
        {enquiriesEnabled ? <EnterpriseEnquiryForm onSubmitted={() => setReceived(true)} /> : null}
      </Reveal>
    </section>
  );
}
