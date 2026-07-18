/** Prevents overlapping analysis requests. One in flight at a time. */
export class AnalysisGate {
  private busy = false

  tryAcquire(): boolean {
    if (this.busy) return false
    this.busy = true
    return true
  }

  release(): void {
    this.busy = false
  }

  get isBusy(): boolean {
    return this.busy
  }
}
