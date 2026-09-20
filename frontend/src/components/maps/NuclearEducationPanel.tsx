/** A reference resource has no access to workspace geometry or live observations. */
export function NuclearEducationPanel() {
  return (
    <section className="map-tool-section" aria-label="Nuclear effects education">
      <h3 className="map-tool-section-title">Understanding nuclear consequences</h3>
      <p className="map-tool-help">
        NUKEMAP by Alex Wellerstein is an external educational resource for understanding the scale
        and humanitarian consequences of nuclear weapons.
      </p>
      <a
        className="map-tool-primary"
        href="https://nuclearsecrecy.com/nukemap/"
        target="_blank"
        rel="noopener noreferrer"
        referrerPolicy="no-referrer"
      >
        Open NUKEMAP in a new tab
      </a>
      <p className="map-tool-help">
        Its scenarios are approximate educational illustrations. They are not observed events or
        guidance for emergency planning or response.
      </p>
      <a
        className="map-tool-text-button"
        href="https://nuclearsecrecy.com/nukemap/faq/"
        target="_blank"
        rel="noopener noreferrer"
        referrerPolicy="no-referrer"
      >
        Read the model limitations and terms
      </a>
      <p className="map-tool-help">
        Opening the external site contacts its operator. Your drawings, selected locations and
        research questions are not included in these links.
      </p>
    </section>
  );
}
