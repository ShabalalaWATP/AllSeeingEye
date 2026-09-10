import './mapTool.css';

/** The enclosing drawer supplies its own title; standalone tools retain this heading. */
export function MapToolIntro({
  title,
  description,
  status,
  statusActive = false,
}: {
  title: string;
  description: string;
  status?: string;
  statusActive?: boolean;
}) {
  return (
    <header className="map-tool-intro">
      <h2 className="map-tool-intro-title">{title}</h2>
      {status && (
        <span className="map-tool-state" data-active={statusActive}>
          {status}
        </span>
      )}
      <p>{description}</p>
    </header>
  );
}
