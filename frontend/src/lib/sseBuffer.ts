/** A fixed-size byte buffer: each incoming byte is scanned once, including partial frames. */
export const MAX_SSE_FRAME_BYTES = 1_048_576;

export class SseFrameBuffer {
  private readonly bytes = new Uint8Array(MAX_SSE_FRAME_BYTES);
  private length = 0;
  private newline = false;
  private readonly decoder = new TextDecoder();

  *push(chunk: Uint8Array): Generator<string> {
    for (const byte of chunk) {
      if (this.length === this.bytes.length) throw new Error('SSE frame exceeds the byte limit.');
      this.bytes[this.length++] = byte;
      if (byte === 10 && this.newline) {
        const frame = this.decoder.decode(this.bytes.subarray(0, this.length));
        this.length = 0;
        this.newline = false;
        yield frame;
      } else if (byte === 10) this.newline = true;
      else if (byte !== 13) this.newline = false;
    }
  }
}
