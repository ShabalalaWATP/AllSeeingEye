import { render, screen, waitFor, within } from '@testing-library/react';
import { useState } from 'react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { initialCapabilitiesState, useCapabilitiesStore } from '@/stores/capabilities';
import { useGlobeStore } from '@/stores/globe';
import { server } from '@/test/server';

import { BaseLayerToolbar } from './BaseLayerToolbar';

describe('BaseLayerToolbar', () => {
  it('keeps embedded choices open and lets the enclosing drawer handle Escape', async () => {
    const escape = vi.fn();
    const onChange = vi.fn();
    const { container } = render(
      <BaseLayerToolbar value="satellite" embedded osAvailable={false} onChange={onChange} />,
    );
    expect(screen.queryByRole('button', { name: /Map style:/ })).not.toBeInTheDocument();
    expect(screen.getAllByRole('radio')).toHaveLength(8);
    expect(screen.getByRole('radio', { name: 'OS Road' })).toHaveAccessibleDescription(
      /An administrator must configure/,
    );
    expect(screen.getByText(/swatches are illustrative/)).toBeVisible();
    expect(container.querySelector('img, video, iframe')).toBeNull();
    const user = userEvent.setup();
    await user.click(screen.getByRole('radio', { name: 'Dark' }));
    expect(onChange).toHaveBeenCalledWith('dark');
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') escape();
    };
    document.addEventListener('keydown', onKeyDown);
    try {
      await user.keyboard('{Escape}');
    } finally {
      document.removeEventListener('keydown', onKeyDown);
    }
    expect(escape).toHaveBeenCalledOnce();
    expect(screen.getByRole('radio', { name: 'Satellite' })).toBeVisible();
    expect(screen.getByRole('link', { name: 'Imagery licence' })).toBeVisible();
  });

  it('starts compact and opens a labelled group with the current choice', async () => {
    const onChange = vi.fn();
    render(<BaseLayerToolbar value="hybrid" osAvailable={false} onChange={onChange} />);
    const trigger = screen.getByRole('button', { name: 'Map style: Hybrid' });
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByRole('radio')).not.toBeInTheDocument();
    await userEvent.click(trigger);
    const group = screen.getByRole('group', { name: 'Base layer' });
    expect(within(group).getAllByRole('radio')).toHaveLength(8);
    expect(within(group).getByRole('radio', { name: 'Hybrid' })).toBeChecked();
    expect(within(group).getByRole('radio', { name: 'Dark' })).not.toBeChecked();
    await userEvent.click(within(group).getByRole('radio', { name: 'Satellite' }));
    expect(onChange).toHaveBeenCalledWith('satellite');
    expect(screen.getByText(/2024 satellite imagery/)).toBeInTheDocument();
    expect(screen.getByText(/Non-commercial use only/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Imagery licence' })).toHaveAttribute(
      'href',
      'https://creativecommons.org/licenses/by-nc-sa/4.0/',
    );
    await userEvent.click(trigger);
    expect(screen.queryByRole('radio')).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Imagery licence' })).toBeVisible();
  });

  it('keeps unavailable OS choices discoverable and explains the missing connection', async () => {
    const onChange = vi.fn();
    render(<BaseLayerToolbar value="dark" osAvailable={false} onChange={onChange} />);
    await userEvent.click(screen.getByRole('button', { name: 'Map style: Dark' }));
    const osRoad = screen.getByRole('radio', { name: 'OS Road' });
    expect(osRoad).toBeDisabled();
    expect(osRoad).toHaveAccessibleDescription(/An administrator must configure/);
    await userEvent.click(osRoad);
    expect(onChange).not.toHaveBeenCalled();
    expect(screen.getByRole('radio', { name: 'Streets' })).toBeEnabled();
    expect(screen.getByRole('radio', { name: 'Light' })).toBeEnabled();
    expect(screen.getByText('Connection required')).toBeInTheDocument();
    await userEvent.click(screen.getByText('How to enable OS maps'));
    expect(screen.getByText('ASE_OS_MAPS_KEY')).toBeVisible();
    expect(screen.getByRole('link', { name: 'OS Data Hub setup guide' })).toHaveAttribute(
      'href',
      'https://docs.os.uk/os-apis/accessing-os-apis/os-maps-api/getting-started',
    );
  });

  it('distinguishes a failed check from missing configuration and supports retry', async () => {
    const retry = vi.fn();
    const { rerender } = render(
      <BaseLayerToolbar
        value="dark"
        initialExpanded
        osAvailable={false}
        osError="Unavailable"
        onCheckOs={retry}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByRole('alert')).toHaveTextContent('Configuration check failed');
    expect(screen.queryByText('Connection required')).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Check configuration again' }));
    expect(retry).toHaveBeenCalledOnce();
    rerender(
      <BaseLayerToolbar
        value="dark"
        initialExpanded
        osAvailable={false}
        osChecking
        onCheckOs={retry}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByRole('status')).toHaveTextContent('Checking');
    expect(screen.getByRole('button', { name: 'Check configuration again' })).toBeDisabled();
    expect(screen.queryByText('How to enable OS maps')).not.toBeInTheDocument();
  });

  it('enables the OS styles with honest coverage when the server can proxy them', async () => {
    render(<BaseLayerToolbar value="os_outdoor" osAvailable onChange={vi.fn()} />);
    await userEvent.click(screen.getByRole('button', { name: 'Map style: OS Outdoor' }));
    expect(screen.getByRole('radio', { name: 'OS Outdoor' })).toBeEnabled();
    expect(screen.getByRole('radio', { name: 'OS Outdoor' })).toBeChecked();
    expect(screen.getByText('Great Britain · zoom 7–16')).toBeInTheDocument();
    expect(screen.getByText(/Zoom into Great Britain/)).toBeInTheDocument();
    expect(screen.queryByText(/OS maps are unavailable/)).not.toBeInTheDocument();
    expect(screen.getByText(/does not test tile delivery/)).toBeInTheDocument();
  });

  it('supports native arrow selection and Escape returns focus to the trigger', async () => {
    function ControlledPicker() {
      const [value, setValue] = useState<'dark' | 'streets' | 'light'>('dark');
      return (
        <BaseLayerToolbar
          value={value}
          osAvailable={false}
          onChange={(next) => {
            if (next === 'dark' || next === 'streets' || next === 'light') setValue(next);
          }}
        />
      );
    }
    const user = userEvent.setup();
    render(<ControlledPicker />);
    await user.tab();
    await user.keyboard('{Enter}');
    await user.tab();
    expect(screen.getByRole('radio', { name: 'Dark' })).toHaveFocus();
    await user.keyboard('{ArrowRight}');
    expect(screen.getByRole('radio', { name: 'Streets' })).toBeChecked();
    expect(screen.getByRole('radio', { name: 'Streets' })).toHaveFocus();
    await user.keyboard('{Escape}');
    expect(screen.getByRole('button', { name: 'Map style: Streets' })).toHaveFocus();
    expect(screen.queryByRole('radio')).not.toBeInTheDocument();
  });
});

describe('globe store base layer', () => {
  it('starts hybrid and remembers the choice', () => {
    expect(useGlobeStore.getState().baseLayer).toBe('hybrid');
    useGlobeStore.getState().setBaseLayer('os_light');
    expect(useGlobeStore.getState().baseLayer).toBe('os_light');
  });
});

describe('capabilities store', () => {
  beforeEach(() => {
    useCapabilitiesStore.setState({ ...initialCapabilitiesState });
  });

  it('loads once, preserves failure state and allows a retry after failure', async () => {
    let requests = 0;
    server.use(
      http.get('/api/capabilities', () => {
        requests += 1;
        return HttpResponse.json({ os_maps: true, os_layers: ['Road_3857'] });
      }),
    );
    await useCapabilitiesStore.getState().load();
    await useCapabilitiesStore.getState().load();
    expect(requests).toBe(1);
    expect(useCapabilitiesStore.getState()).toMatchObject({ osMaps: true, loaded: true });

    useCapabilitiesStore.setState({ ...initialCapabilitiesState });
    server.use(
      http.get('/api/capabilities', () =>
        HttpResponse.json({ error: { code: 'x', message: 'down' } }, { status: 500 }),
      ),
    );
    await useCapabilitiesStore.getState().load();
    expect(useCapabilitiesStore.getState()).toMatchObject({
      osMaps: false,
      loaded: false,
      loading: false,
    });
    expect(useCapabilitiesStore.getState().error).toBeTruthy();
    server.use(
      http.get('/api/capabilities', () =>
        HttpResponse.json({ os_maps: true, os_layers: ['Road_3857'] }),
      ),
    );
    await useCapabilitiesStore.getState().load();
    expect(useCapabilitiesStore.getState()).toMatchObject({
      osMaps: true,
      loaded: true,
      loading: false,
      error: null,
    });
  });

  it('refreshes a previously unconfigured server and does not overlap requests', async () => {
    await useCapabilitiesStore.getState().load();
    expect(useCapabilitiesStore.getState().osMaps).toBe(false);
    let release!: () => void;
    let requests = 0;
    const barrier = new Promise<void>((resolve) => {
      release = resolve;
    });
    server.use(
      http.get('/api/capabilities', async () => {
        requests += 1;
        await barrier;
        return HttpResponse.json({ os_maps: true, os_layers: ['Road_3857'] });
      }),
    );
    const pending = useCapabilitiesStore.getState().load(true);
    await waitFor(() => expect(requests).toBe(1));
    await useCapabilitiesStore.getState().load(true);
    expect(useCapabilitiesStore.getState().loading).toBe(true);
    expect(requests).toBe(1);
    release();
    await pending;
    expect(useCapabilitiesStore.getState()).toMatchObject({
      osMaps: true,
      loaded: true,
      loading: false,
      error: null,
    });
  });
});
