import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import QuitButton from '../src/renderer/src/components/QuitButton'

describe('QuitButton', () => {
  it('renders an explicit, accessible application quit control', () => {
    const markup = renderToStaticMarkup(createElement(QuitButton, { className: 'test-location' }))

    expect(markup).toContain('aria-label="Quit AllSeeingEye"')
    expect(markup).toContain('title="Quit AllSeeingEye"')
    expect(markup).toContain('app-quit')
    expect(markup).toContain('test-location')
    expect(markup).toContain('×')
  })
})
