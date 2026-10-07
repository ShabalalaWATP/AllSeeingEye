/**
 * Chapter 1b: the controls around the globe. Global filters as chip rows, then every
 * map setup and planning tool from the app's layer directory, revealed in a stagger.
 */
import { GLOBAL_FILTERS, MAP_TOOLS } from '../content/observe';
import { Reveal } from '../motion/Reveal';
import { ScrollChapter } from '../motion/ScrollChapter';

export function ToolsChapter() {
  return (
    <ScrollChapter id="tools" label="Filters and map tools" className="story-tools">
      <div className="story-wrap">
        <Reveal>
          <p className="story-eyebrow">Filters and tools</p>
          <h2 className="story-title">Cut the picture down to what matters.</h2>
          <p className="story-lead">
            Filter by time, place, location quality or a collection plan, replay the last hours
            event by event, then measure, draw and plan on the same map.
          </p>
        </Reveal>
        <dl className="filter-table">
          {GLOBAL_FILTERS.map((filter, index) => (
            <Reveal key={filter.label} order={index} className="filter-row">
              <dt>{filter.label}</dt>
              <dd>
                <ul className="chip-row">
                  {filter.values.map((value) => (
                    <li key={value} className="chip">
                      {value}
                    </li>
                  ))}
                </ul>
              </dd>
            </Reveal>
          ))}
        </dl>
        <ul className="tool-grid" aria-label="Map tools">
          {MAP_TOOLS.map((tool, index) => (
            <Reveal as="li" key={tool.id} order={index % 6} className="tool-card">
              <h3>{tool.label}</h3>
              <p>{tool.description}</p>
            </Reveal>
          ))}
        </ul>
      </div>
    </ScrollChapter>
  );
}
