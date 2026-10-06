import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useEffect, useState } from 'react';
import { MemoryRouter, useLocation, useNavigate } from 'react-router';
import { expect, it, vi } from 'vitest';
import { ControlPanel, GlobeControls } from './GlobeControls';
import { useGlobePanelRoute } from './useGlobePanelRoute';

it('supports ordinary content and a directly rendered deferred ControlPanel', () => {
  const build = vi.fn(() => <p>Deferred direct content</p>);
  const view = render(
    <ControlPanel label="Direct" icon="layers">
      {build}
    </ControlPanel>,
  );
  expect(screen.getByText('Deferred direct content')).toBeVisible();
  expect(build).toHaveBeenCalledOnce();
  view.rerender(
    <ControlPanel label="Direct" icon="layers">
      <p>Ordinary content</p>
    </ControlPanel>,
  );
  expect(screen.getByText('Ordinary content')).toBeVisible();
  expect(build).toHaveBeenCalledOnce();
});

it('builds only the selected body with current metadata, callbacks and content', async () => {
  const user = userEvent.setup();
  const oldAction = vi.fn();
  const newAction = vi.fn();
  const oldOpen = vi.fn();
  const newOpen = vi.fn();
  const build = vi.fn((version: number, action: () => void) => (
    <button onClick={action}>Action {version}</button>
  ));
  const other = vi.fn(() => <p>Other content</p>);
  const fixture = (version: number, action: () => void, onOpen: () => void) => (
    <GlobeControls layers={null}>
      <ControlPanel
        label="Map style"
        icon="layers"
        caption={`Style ${version}`}
        on={version === 2}
        onOpen={onOpen}
      >
        {() => build(version, action)}
      </ControlPanel>
      <ControlPanel label="Measure" icon="measure">
        {other}
      </ControlPanel>
    </GlobeControls>
  );
  const view = render(fixture(1, oldAction, oldOpen));
  view.rerender(fixture(2, newAction, newOpen));
  expect(build).not.toHaveBeenCalled();
  expect(other).not.toHaveBeenCalled();
  const button = screen.getByRole('button', { name: 'Map style' });
  expect(button).toHaveTextContent('Style 2');
  expect(button).toHaveAttribute('data-on', 'true');
  await user.click(button);
  expect(newOpen).toHaveBeenCalledOnce();
  expect(oldOpen).not.toHaveBeenCalled();
  await user.click(screen.getByRole('button', { name: 'Action 2' }));
  expect(newAction).toHaveBeenCalledOnce();
  expect(oldAction).not.toHaveBeenCalled();
  view.rerender(fixture(3, oldAction, oldOpen));
  expect(screen.getByRole('button', { name: 'Action 3' })).toBeVisible();
  expect(other).not.toHaveBeenCalled();
  expect(oldOpen).not.toHaveBeenCalled();
});

it('keeps the selected component mounted and current when collapsed or behind the chooser', async () => {
  const user = userEvent.setup();
  const mounted = vi.fn();
  const unmounted = vi.fn();
  function Body({ version }: { version: number }) {
    const [draft, setDraft] = useState('');
    useEffect(() => {
      mounted();
      return () => {
        unmounted();
      };
    }, []);
    return (
      <>
        <p>Current {version}</p>
        <input
          aria-label="Retained draft"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
        />
      </>
    );
  }
  const fixture = (version: number) => (
    <GlobeControls layers={null} initial="Map style">
      <ControlPanel label="Map style" icon="layers">
        {() => <Body version={version} />}
      </ControlPanel>
    </GlobeControls>
  );
  const view = render(fixture(1));
  await user.type(screen.getByRole('textbox', { name: 'Retained draft' }), 'Keep this');
  await user.click(screen.getByRole('button', { name: 'Collapse tool' }));
  view.rerender(fixture(2));
  expect(screen.getByText('Current 2')).not.toBeVisible();
  expect(screen.getByLabelText('Retained draft')).toHaveValue('Keep this');
  expect(unmounted).not.toHaveBeenCalled();
  await user.click(screen.getByRole('button', { name: 'Expand tool' }));
  await user.click(screen.getByRole('button', { name: 'Tools' }));
  view.rerender(fixture(3));
  expect(screen.getByText('Current 3')).not.toBeVisible();
  expect(screen.getByLabelText('Retained draft')).toHaveValue('Keep this');
  expect(mounted).toHaveBeenCalledOnce();
  expect(unmounted).not.toHaveBeenCalled();
  await user.click(screen.getByRole('button', { name: 'Close tools' }));
  expect(screen.getByText('Current 3')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Close tool' }));
  expect(unmounted).toHaveBeenCalledOnce();
});

it('does not substitute a different body when the selected catalogue entry disappears', () => {
  const other = vi.fn(() => <p>Other body</p>);
  const selected = vi.fn((version: number) => <p>Selected {version}</p>);
  const fixture = (available: boolean, version: number) => (
    <GlobeControls layers={null} initial="Map style">
      {available && (
        <ControlPanel label="Map style" icon="layers">
          {() => selected(version)}
        </ControlPanel>
      )}
      <ControlPanel label="Measure" icon="measure">
        {other}
      </ControlPanel>
    </GlobeControls>
  );
  const view = render(fixture(true, 1));
  expect(screen.getByText('Selected 1')).toBeVisible();
  selected.mockClear();
  view.rerender(fixture(false, 2));
  expect(screen.queryByRole('region', { name: 'Map style' })).not.toBeInTheDocument();
  expect(selected).not.toHaveBeenCalled();
  expect(other).not.toHaveBeenCalled();
  view.rerender(fixture(true, 3));
  expect(screen.getByText('Selected 3')).toBeVisible();
  expect(other).not.toHaveBeenCalled();
});

it('preserves requested-panel history and Escape focus with deferred bodies', async () => {
  function Fixture() {
    const route = useGlobePanelRoute();
    const location = useLocation();
    const navigate = useNavigate();
    return (
      <>
        <output aria-label="Address">{location.search}</output>
        <button onClick={() => void navigate(-1)}>Back</button>
        <GlobeControls layers={null} {...route}>
          <ControlPanel label="Map style" icon="layers">
            {() => <p>Style body</p>}
          </ControlPanel>
          <ControlPanel label="Measure" icon="measure">
            {() => <p>Measure body</p>}
          </ControlPanel>
        </GlobeControls>
      </>
    );
  }
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={['/?country=GB']}>
      <Fixture />
    </MemoryRouter>,
  );
  await user.click(screen.getByRole('button', { name: 'Map style' }));
  expect(screen.getByLabelText('Address')).toHaveTextContent('country=GB&panel=style');
  expect(screen.getByRole('button', { name: 'Close tool' })).toHaveFocus();
  await user.keyboard('{Escape}');
  expect(screen.getByRole('button', { name: 'Map style' })).toHaveFocus();
  expect(screen.getByLabelText('Address')).toHaveTextContent(/^\?country=GB$/);
  await user.click(screen.getByRole('button', { name: 'Back' }));
  expect(
    within(screen.getByRole('region', { name: 'Map style' })).getByText('Style body'),
  ).toBeVisible();
  expect(screen.queryByText('Measure body')).not.toBeInTheDocument();
});
