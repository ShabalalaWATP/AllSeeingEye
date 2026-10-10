import { serviceDetails } from './content';
import { DraftNotice } from './DraftNotice';
import { PolicyLayout, PolicySection } from './PolicyLayout';

export default function AccessibilityPage() {
  return (
    <PolicyLayout title="Accessibility">
      <DraftNotice />
      <p>
        Accessibility review is ongoing. A complete accessibility conformance audit has not been
        completed.
      </p>
      <PolicySection id="controls" title="Reading and navigation">
        <ul>
          <li>
            Use the skip link to reach the main content and Tab to move between links and controls.
          </li>
          <li>
            Browser zoom and narrow layouts are supported. Visual maps also provide text-based lists
            and detail panels.
          </li>
          <li>
            The public story has a Pause animation control and respects the device's reduced-motion
            preference.
          </li>
          <li>
            Forms identify validation errors and retain entered information when a submission needs
            correction.
          </li>
        </ul>
      </PolicySection>
      <PolicySection id="limitations" title="Known limits and feedback">
        <p>
          Maps, graphics and third-party media may have limitations that are not identified by
          automated checks. Automated accessibility results do not establish complete conformance.
        </p>
        <p className="whitespace-pre-line">
          {serviceDetails.accessibilityContact ??
            'The operator has not yet confirmed an accessibility contact. This blocks publication.'}
        </p>
        <p>
          When reporting an access barrier, include the page, the task you were trying to complete
          and the browser or assistive technology involved. Avoid including passwords or private
          research material.
        </p>
      </PolicySection>
    </PolicyLayout>
  );
}
