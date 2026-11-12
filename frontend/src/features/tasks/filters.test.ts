import { describe, expect, it } from 'vitest'
import {
  changeFilters,
  noFilters,
  pageSize,
  parseTaskFilters,
  toApiQuery,
  toSearchParams,
  type TaskFilters,
} from './filters'

function parse(query: string) {
  return parseTaskFilters(new URLSearchParams(query))
}

const everything: TaskFilters = {
  status: ['to_do', 'done'],
  due_after: '2026-11-01',
  due_before: '2026-11-30',
  overdue: true,
  assignee: 'me',
  search: 'invoice',
  ordering: '-due_date',
  page: 3,
}

describe('parseTaskFilters', () => {
  it('reads every filter the API takes, under its own name', () => {
    const query =
      'status=to_do&status=done&due_after=2026-11-01&due_before=2026-11-30&overdue=true' +
      '&assignee=me&search=invoice&ordering=-due_date&page=3'

    expect(parse(query)).toEqual({ filters: everything, ignored: [] })
  })

  it('without parameters, nothing is filtered', () => {
    expect(parse('')).toEqual({ filters: noFilters, ignored: [] })
  })

  it('reads a user id as the assignee, and overdue=false', () => {
    const { filters } = parse('assignee=7&overdue=false')

    expect(filters.assignee).toBe(7)
    expect(filters.overdue).toBe(false)
  })

  it('keeps statuses in workflow order, once each', () => {
    expect(parse('status=done&status=to_do&status=done').filters.status).toEqual(['to_do', 'done'])
  })

  it('trims the search', () => {
    expect(parse('search=%20%20invoice%20').filters.search).toBe('invoice')
  })

  it.each([
    ['status=nope', 'status'],
    ['due_after=2026-02-30', 'due_after'],
    ['due_before=12/11/2026', 'due_before'],
    ['overdue=yes', 'overdue'],
    ['assignee=someone', 'assignee'],
    ['assignee=0', 'assignee'],
    ['assignee=99999999999999999999', 'assignee'],
    ['ordering=title', 'ordering'],
    ['page=0', 'page'],
    ['page=two', 'page'],
  ])('ignores %s from a shared link, and reports it', (query, name) => {
    expect(parse(query)).toEqual({ filters: noFilters, ignored: [name] })
  })

  it('keeps the valid values next to an invalid one', () => {
    expect(parse('status=to_do&status=nope&page=x&search=report')).toEqual({
      filters: { ...noFilters, status: ['to_do'], search: 'report' },
      ignored: ['status', 'page'],
    })
  })

  it('treats an empty value as no filter, as the API does (ADR 0013)', () => {
    expect(parse('status=&due_after=&overdue=&assignee=&search=%20&ordering=&page=')).toEqual({
      filters: noFilters,
      ignored: [],
    })
  })

  it("ignores parameters that aren't filters, without reporting them", () => {
    expect(parse('utm_source=mail')).toEqual({ filters: noFilters, ignored: [] })
  })
})

describe('toSearchParams', () => {
  it('writes every filter so that parsing it gives the same filters back', () => {
    expect(parseTaskFilters(toSearchParams(everything))).toEqual({
      filters: everything,
      ignored: [],
    })
  })

  it('repeats status, as the API reads it', () => {
    expect(toSearchParams({ ...noFilters, status: ['to_do', 'done'] }).toString()).toBe(
      'status=to_do&status=done',
    )
  })

  it('leaves out the defaults, so an unfiltered list has a bare URL', () => {
    expect(toSearchParams(noFilters).toString()).toBe('')
    expect(toSearchParams({ ...noFilters, page: 1 }).toString()).toBe('')
  })

  it('leaves the page size out: the list chooses it, not the link', () => {
    expect(toSearchParams(everything).has('page_size')).toBe(false)
  })
})

describe('toApiQuery', () => {
  it('passes each filter to the API in its own format', () => {
    expect(toApiQuery(everything)).toEqual({
      status: ['to_do', 'done'],
      due_after: '2026-11-01',
      due_before: '2026-11-30',
      overdue: 'true',
      assignee: 'me',
      search: 'invoice',
      ordering: ['-due_date'],
      page: 3,
      page_size: pageSize,
    })
  })

  it('sends a user id as text, and nothing for the defaults but the page size', () => {
    expect(toApiQuery({ ...noFilters, assignee: 7 })).toEqual({
      assignee: '7',
      page_size: pageSize,
    })
    expect(toApiQuery(noFilters)).toEqual({ page_size: pageSize })
  })
})

describe('changeFilters', () => {
  it('goes back to page 1 when a filter changes', () => {
    expect(changeFilters(everything, { overdue: null })).toEqual({
      ...everything,
      overdue: null,
      page: 1,
    })
  })

  it('keeps the other filters when only the page changes', () => {
    expect(changeFilters(everything, { page: 4 })).toEqual({ ...everything, page: 4 })
  })
})
