import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import type { AiEffectiveModel as Model } from '@/lib/api/aiUsage';

import { AiEffectiveModel } from './AiEffectiveModel';

function model(overrides: Partial<Model> = {}): Model {
  return {
    policy: 'global',
    profile_id: '55555555-5555-4555-8555-555555555555',
    profile_name: 'Luna',
    model: 'gpt-5.6-luna',
    provider: 'openai_compatible',
    reasoning_effort: 'max',
    mechanical_effort: 'medium',
    unavailable: null,
    ...overrides,
  };
}

describe('AiEffectiveModel', () => {
  it('renders nothing when the server sent no model', () => {
    const { container } = render(<AiEffectiveModel model={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('names the routing that chose the connection', () => {
    render(<AiEffectiveModel model={model()} />);
    expect(screen.getByText(/Global connection/)).toBeInTheDocument();
    expect(screen.getByText(/lowered to medium for mechanical work/)).toBeInTheDocument();
  });

  it('says nothing about a cap when the effort is unchanged', () => {
    render(<AiEffectiveModel model={model({ mechanical_effort: 'max' })} />);
    expect(screen.queryByText(/lowered to/)).not.toBeInTheDocument();
  });

  it('falls back to the provider default and an unnamed profile', () => {
    render(
      <AiEffectiveModel
        model={model({
          profile_name: '',
          policy: null,
          reasoning_effort: null,
          mechanical_effort: null,
        })}
      />,
    );
    expect(screen.getByText(/Reasoning effort provider default/)).toBeInTheDocument();
    expect(screen.queryByText(/·\s*Luna/)).not.toBeInTheDocument();
  });

  it('shows the routing reason instead of a model when none is usable', () => {
    render(<AiEffectiveModel model={model({ unavailable: 'No global model is assigned.' })} />);
    expect(screen.getByRole('status')).toHaveTextContent('No global model is assigned.');
    expect(screen.queryByText('gpt-5.6-luna')).not.toBeInTheDocument();
  });
});
