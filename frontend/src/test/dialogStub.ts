import { cleanup } from '@testing-library/react';
import { afterEach, beforeEach } from 'vitest';

/**
 * jsdom has no native dialog top layer, so `showModal` and `close` are stubbed. The stub
 * deliberately moves no focus: components must place initial focus themselves, which is
 * what the confirmation tests assert. Real browser checks cover the native focus trap.
 */
export function installDialogStub(): void {
  beforeEach(() => {
    Object.defineProperty(HTMLDialogElement.prototype, 'showModal', {
      configurable: true,
      value: function (this: HTMLDialogElement) {
        this.open = true;
      },
    });
    Object.defineProperty(HTMLDialogElement.prototype, 'close', {
      configurable: true,
      value: function (this: HTMLDialogElement) {
        this.open = false;
      },
    });
  });

  afterEach(() => {
    // Unmount while the stubs still exist, so an open dialog can close.
    cleanup();
    Reflect.deleteProperty(HTMLDialogElement.prototype, 'showModal');
    Reflect.deleteProperty(HTMLDialogElement.prototype, 'close');
  });
}
