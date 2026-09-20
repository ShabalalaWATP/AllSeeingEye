import { fireEvent, render, screen, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { useState } from 'react';
import { MemoryRouter, useLocation, useNavigate, useSearchParams } from 'react-router';
import { expect, it, vi } from 'vitest';
import { mapPanelId, readMapPanel } from '@/lib/mapLayerDirectory';
import { ControlPanel, GlobeControls } from './GlobeControls';

function Draft() {
  const [value, setValue] = useState('');
  return (
    <input
      aria-label="Draft question"
      value={value}
      onChange={(event) => setValue(event.target.value)}
    />
  );
}
function panels() {
  return [
    <ControlPanel key="draw" label="Draw on map" icon="draw">
      <p>Draw options</p>
    </ControlPanel>,
    <ControlPanel key="area" label="Research area" icon="research">
      <Draft />
    </ControlPanel>,
    <ControlPanel key="rf" label="RF link calculator" icon="rf">
      <p>Radio options</p>
    </ControlPanel>,
    <ControlPanel key="measure" label="Measure distance and area" icon="measure">
      <p>Measure options</p>
    </ControlPanel>,
    <ControlPanel key="style" label="Map style" icon="layers">
      <p>Style options</p>
    </ControlPanel>,
  ];
}

it('searches grouped tools, pins a replacement and keeps navigation outside the tool list', async () => {
  const user = userEvent.setup();
  const { unmount } = render(
    <GlobeControls layers={null} navigation={<button>Zoom in</button>}>
      {panels()}
    </GlobeControls>,
  );
  const rail = screen.getByRole('group', { name: 'Map tools' });
  expect(within(rail).queryByRole('button', { name: 'Zoom in' })).not.toBeInTheDocument();
  expect(within(rail).queryByRole('button', { name: 'Map style' })).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Tools' }));
  expect(screen.getByRole('region', { name: 'Radio and terrain' })).toBeVisible();
  expect(screen.getByRole('button', { name: 'Pin Map style' })).toBeDisabled();
  await user.click(screen.getByRole('button', { name: 'Unpin Draw on map' }));
  await user.click(screen.getByRole('button', { name: 'Pin Map style' }));
  expect(within(rail).getByRole('button', { name: 'Map style' })).toBeVisible();
  await user.type(screen.getByRole('searchbox', { name: 'Find a tool' }), 'satellite');
  const chooser = screen.getByRole('region', { name: 'Tools' });
  expect(
    within(chooser).queryByRole('region', { name: 'Radio and terrain' }),
  ).not.toBeInTheDocument();
  await user.click(within(chooser).getByRole('button', { name: 'Map style' }));
  expect(screen.getByText('Style options')).toBeVisible();
  await user.keyboard('{Escape}');
  expect(screen.getByRole('button', { name: 'Tools' })).toHaveFocus();
  unmount();
  render(<GlobeControls layers={null}>{panels()}</GlobeControls>);
  const restored = screen.getByRole('group', { name: 'Map tools' });
  expect(within(restored).getByRole('button', { name: 'Map style' })).toBeVisible();
  expect(within(restored).queryByRole('button', { name: 'Draw on map' })).not.toBeInTheDocument();
});

it('collapses without dropping local edits or notifying the input owner that the tool closed', async () => {
  const user = userEvent.setup();
  const active = vi.fn();
  render(
    <GlobeControls
      layers={null}
      initial="Research area"
      onActiveChange={active}
      activity={<button>Finish drawing</button>}
    >
      {panels()}
    </GlobeControls>,
  );
  await user.type(screen.getByRole('textbox', { name: 'Draft question' }), 'Flood observations');
  active.mockClear();
  await user.click(screen.getByRole('button', { name: 'Collapse tool' }));
  expect(screen.queryByRole('textbox', { name: 'Draft question' })).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Finish drawing' })).toBeVisible();
  expect(active).not.toHaveBeenCalled();
  await user.click(screen.getByRole('button', { name: 'Expand tool' }));
  expect(screen.getByRole('textbox', { name: 'Draft question' })).toHaveValue('Flood observations');
  await user.click(screen.getByRole('button', { name: 'Tools' }));
  await user.keyboard('{Escape}');
  expect(screen.getByRole('textbox', { name: 'Draft question' })).toHaveValue('Flood observations');
  expect(screen.getByRole('button', { name: 'Tools' })).toHaveFocus();
  expect(active).not.toHaveBeenCalled();
});

it('resizes the inspector with the keyboard within defined bounds', async () => {
  const user = userEvent.setup();
  render(
    <GlobeControls layers={null} initial="Draw on map">
      {panels()}
    </GlobeControls>,
  );
  const resize = screen.getByRole('slider', { name: 'Resize tool panel' });
  resize.focus();
  await user.keyboard('{ArrowRight}');
  expect(resize).toHaveAttribute('aria-valuenow', '384');
  await user.keyboard('{End}{ArrowRight}');
  expect(resize).toHaveAttribute('aria-valuenow', '600');
  await user.keyboard('{Home}{ArrowLeft}');
  expect(resize).toHaveAttribute('aria-valuenow', '320');
});

it('reports an empty tool search and finds a display title through keyboard navigation', async () => {
  const user = userEvent.setup();
  render(
    <GlobeControls layers={null}>
      <ControlPanel label="Local reference" title="Field notebook" icon="guide" caption="Notes">
        <p>Reference notes</p>
      </ControlPanel>
    </GlobeControls>,
  );
  await user.click(screen.getByRole('button', { name: 'Tools' }));
  const query = screen.getByRole('searchbox', { name: 'Find a tool' });
  await user.type(query, 'absent tool');
  expect(screen.getByRole('status')).toHaveTextContent('No tools match this search.');
  await user.clear(query);
  await user.type(query, '  FIELD NOTEBOOK  ');
  expect(screen.queryByRole('status')).not.toBeInTheDocument();
  await user.tab();
  expect(
    within(screen.getByRole('region', { name: 'Tools' })).getByRole('button', {
      name: 'Local reference',
    }),
  ).toHaveFocus();
  await user.keyboard('{Enter}');
  expect(screen.getByRole('heading', { name: 'Field notebook' })).toBeVisible();
  expect(screen.getByText('Reference notes')).toBeVisible();
});

it('lets an embedded editor consume Escape before the shell closes the tool', async () => {
  const user = userEvent.setup();
  const navigate = vi.fn();
  render(
    <GlobeControls layers={null} initial="Draw on map" onPanelChange={navigate}>
      <ControlPanel label="Draw on map" icon="draw">
        <input aria-label="Annotation" onKeyDown={(event) => event.preventDefault()} />
      </ControlPanel>
    </GlobeControls>,
  );
  await user.click(screen.getByRole('textbox', { name: 'Annotation' }));
  await user.keyboard('{Escape}');
  expect(screen.getByRole('textbox', { name: 'Annotation' })).toBeVisible();
  expect(navigate).not.toHaveBeenCalled();
  fireEvent.keyDown(document, { key: 'Escape' });
  expect(screen.queryByRole('textbox', { name: 'Annotation' })).not.toBeInTheDocument();
  expect(navigate).toHaveBeenCalledExactlyOnceWith(null);
});

it('supports functional panel children and expands a collapsed tool from its external launcher', async () => {
  const user = userEvent.setup();
  render(
    <GlobeControls
      layers={(open) => <button onClick={() => open('Draw on map')}>Open drawing editor</button>}
    >
      {(open) => (
        <ControlPanel label="Draw on map" icon="draw">
          <button onClick={() => open('Draw on map')}>Finish editing</button>
        </ControlPanel>
      )}
    </GlobeControls>,
  );
  await user.click(screen.getByRole('button', { name: 'Open drawing editor' }));
  expect(screen.getByRole('button', { name: 'Finish editing' })).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Collapse tool' }));
  await user.click(screen.getByRole('button', { name: 'Open drawing editor' }));
  expect(screen.getByRole('button', { name: 'Finish editing' })).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Finish editing' }));
  expect(screen.queryByRole('button', { name: 'Finish editing' })).not.toBeInTheDocument();
});

it.each(['close button', 'Escape'])(
  'returns focus to Tools after a removed launcher (%s)',
  async (action) => {
    const user = userEvent.setup();
    const fixture = (showLauncher: boolean) => (
      <GlobeControls
        layers={(open) =>
          showLauncher && (
            <button onClick={(event) => open('Draw on map', event.currentTarget)}>
              Edit selection
            </button>
          )
        }
      >
        {panels()}
      </GlobeControls>
    );
    const { rerender } = render(fixture(true));
    await user.click(screen.getByRole('button', { name: 'Edit selection' }));
    rerender(fixture(false));
    if (action === 'close button')
      await user.click(screen.getByRole('button', { name: 'Close tool' }));
    else await user.keyboard('{Escape}');
    expect(screen.queryByText('Draw options')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Tools' })).toHaveFocus();
  },
);

function RouterFixture() {
  const [params, setParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  return (
    <>
      <button onClick={() => void navigate('/?panel=rf&area=kept')}>Search radio</button>
      <button onClick={() => void navigate(-1)}>Back</button>
      <button onClick={() => void navigate(1)}>Forward</button>
      <output aria-label="Current query">{location.search}</output>
      <GlobeControls
        layers={null}
        requestedPanel={readMapPanel(params)}
        requestKey={location.key}
        onPanelChange={(label) => {
          const next = new URLSearchParams(params);
          if (label) next.set('panel', mapPanelId(label) ?? label);
          else next.delete('panel');
          setParams(next);
        }}
      >
        {panels()}
      </GlobeControls>
    </>
  );
}

it('synchronises search, in-map navigation and browser history without losing unrelated parameters', async () => {
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={['/?panel=Draw%20on%20map&area=kept']}>
      <RouterFixture />
    </MemoryRouter>,
  );
  expect(screen.getByText('Draw options')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Search radio' }));
  expect(screen.getByText('Radio options')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Back' }));
  expect(screen.getByText('Draw options')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Forward' }));
  expect(screen.getByText('Radio options')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Research area' }));
  expect(screen.getByLabelText('Current query')).toHaveTextContent('panel=area&area=kept');
  await user.click(screen.getByRole('button', { name: 'Close tool' }));
  expect(screen.getByLabelText('Current query')).toHaveTextContent('?area=kept');
  expect(screen.queryByRole('textbox', { name: 'Draft question' })).not.toBeInTheDocument();
});
