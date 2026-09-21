import { describe, expect, it, vi } from 'vitest';

import { ApiError } from './api/errors';
import {
  invalidateResearchUsage,
  researchUsageMutation,
  subscribeResearchUsage,
} from './researchUsageEvents';

describe('research usage refresh', () => {
  it('notifies after success, preserves the result and removes unmounted subscribers', async () => {
    const updated = vi.fn();
    const unsubscribe = subscribeResearchUsage(updated);
    try {
      await expect(
        researchUsageMutation(() => Promise.resolve({ admitted: true })),
      ).resolves.toEqual({ admitted: true });
      expect(updated).toHaveBeenCalledOnce();
    } finally {
      unsubscribe();
    }
    invalidateResearchUsage();
    expect(updated).toHaveBeenCalledOnce();
  });

  it('refreshes on uncertain failure without turning a rejected research run into a success', async () => {
    const updated = vi.fn();
    const unsubscribe = subscribeResearchUsage(updated);
    const error = new ApiError(503, 'unavailable', 'The research response was lost.');
    try {
      await expect(researchUsageMutation(() => Promise.reject(error))).rejects.toBe(error);
      expect(updated).toHaveBeenCalledOnce();
    } finally {
      unsubscribe();
    }
  });
});
