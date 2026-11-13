import { describe, expect, it } from 'vitest'
import { listPathFrom } from './listLink'

// "Back to tasks" returns to the list as the user left it: its filters, order and page travel
// in the location state of the links from the list (spec section 8: filters live in the URL).
describe('listPathFrom', () => {
  it.each([
    ['?status=to_do&page=2', '/tasks?status=to_do&page=2'],
    ['?search=invoice', '/tasks?search=invoice'],
    ['', '/tasks'],
  ])('a list search of "%s" goes back to %s', (list, path) => {
    expect(listPathFrom({ list })).toBe(path)
  })

  // History state can hold anything, so only a search is taken: never a path or another site.
  it.each([
    ['no state', undefined],
    ['null', null],
    ['state from somewhere else', { from: '/login' }],
    ['a list that is not text', { list: 5 }],
    ['a path', { list: '/admin' }],
    ['another site', { list: '//evil.example' }],
  ])('%s goes back to the plain list', (_, state) => {
    expect(listPathFrom(state)).toBe('/tasks')
  })
})
