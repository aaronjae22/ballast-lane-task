import { describe, expect, it } from 'vitest'
import { checkConsole, expectConsole } from './console'

describe('the console guard', () => {
  it('reports a warning or error the test did not declare', () => {
    console.error('Each child in a list should have a unique "key" prop.')
    console.warn('deprecated')

    expect(() => {
      checkConsole()
    }).toThrow(/console\.error: Each child.*\n.*console\.warn: deprecated/)
  })

  it('lets a declared message through', () => {
    expectConsole('error', /boom/)

    console.error(new Error('boom'))

    expect(() => {
      checkConsole()
    }).not.toThrow()
  })

  it('reports a declared message that never came', () => {
    expectConsole('warn', /never logged/)

    expect(() => {
      checkConsole()
    }).toThrow(/expected console\.warn matching \/never logged\/ was never logged/)
  })
})
