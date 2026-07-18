export class CaptureError extends Error {
  constructor(message = 'screen capture failed') {
    super(message)
    this.name = 'CaptureError'
  }
}

export class MissingKeyError extends Error {
  constructor() {
    super('OPENAI_API_KEY is not configured')
    this.name = 'MissingKeyError'
  }
}

export class BadResponseError extends Error {
  constructor(message = 'model returned an unexpected format') {
    super(message)
    this.name = 'BadResponseError'
  }
}
