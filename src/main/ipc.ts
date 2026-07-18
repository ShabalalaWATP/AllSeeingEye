import { ipcMain } from 'electron'
import { z } from 'zod'
import { ANALYSIS_MODES, MAX_TEXT_LENGTH, WINDOW_MODE_NAMES } from '../shared/types'
import { PrefsUpdateSchema } from './core/prefs-schema'
import type { AnalysisController } from './analysis'
import type { PrefsStore } from './prefs'

const TextRequestSchema = z
  .object({
    text: z.string().min(1).max(MAX_TEXT_LENGTH),
    mode: z.enum(ANALYSIS_MODES)
  })
  .strict()

const WindowModeSchema = z.enum(WINDOW_MODE_NAMES)

/** Every argument crossing the bridge is validated here before use. */
export function registerIpc(controller: AnalysisController, prefs: PrefsStore): void {
  ipcMain.handle('analysis:screen', () => controller.runScreen())

  ipcMain.handle('analysis:text', (_event, raw: unknown) => {
    const parsed = TextRequestSchema.safeParse(raw)
    if (!parsed.success) return
    return controller.runText(parsed.data.text, parsed.data.mode)
  })

  ipcMain.handle('window:set-mode', (_event, raw: unknown) => {
    const parsed = WindowModeSchema.safeParse(raw)
    if (parsed.success) controller.setWindowMode(parsed.data)
  })

  ipcMain.handle('prefs:get', () => prefs.get())

  ipcMain.handle('prefs:update', (_event, raw: unknown) => {
    const parsed = PrefsUpdateSchema.safeParse(raw)
    if (parsed.success) {
      prefs.set(parsed.data)
      controller.push()
    }
    return prefs.get()
  })

  ipcMain.handle('app:toggle-pause', () => controller.togglePause())
  ipcMain.handle('app:dismiss', () => controller.dismiss())
  ipcMain.handle('app:collapse', () => controller.collapse())
  ipcMain.handle('app:quit', () => controller.quit())
  ipcMain.handle('state:request', () => controller.push())
}
