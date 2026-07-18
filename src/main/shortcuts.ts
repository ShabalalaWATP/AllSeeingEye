import { globalShortcut } from 'electron'

export interface ShortcutActions {
  analyse: () => void
  toggleVisibility: () => void
  togglePause: () => void
}

// Note: pause is Ctrl+Alt+P, not Ctrl+Shift+P, which would steal the VS Code
// command palette system-wide. A failed registration (another app owns the
// combination) is logged and non-fatal: every action also has a UI control.
const BINDINGS: ReadonlyArray<[string, keyof ShortcutActions]> = [
  ['Control+Shift+R', 'analyse'],
  ['Control+Shift+Space', 'toggleVisibility'],
  ['Control+Alt+P', 'togglePause']
]

export function registerShortcuts(actions: ShortcutActions): void {
  for (const [accelerator, action] of BINDINGS) {
    const ok = globalShortcut.register(accelerator, actions[action])
    if (!ok) console.warn(`[shortcuts] could not register ${accelerator}`)
  }
}

export function unregisterShortcuts(): void {
  globalShortcut.unregisterAll()
}
