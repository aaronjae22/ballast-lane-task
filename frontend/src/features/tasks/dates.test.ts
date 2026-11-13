import { describe, expect, it } from 'vitest'
import { formatDay, formatTimestamp, isDay } from './dates'

describe('the test run', () => {
  it('runs behind UTC, so a due date read as midnight UTC would show the day before', () => {
    // vite.config.ts sets TZ. Without it, these tests would pass even with that bug.
    expect(new Date(Date.UTC(2026, 10, 12)).getDate()).toBe(11)
  })
})

describe('formatDay', () => {
  it('shows the day itself, not the day before', () => {
    expect(formatDay('2026-11-12')).toBe('Nov 12, 2026')
  })

  it('shows the first and the last day of a year as they are', () => {
    expect(formatDay('2026-01-01')).toBe('Jan 1, 2026')
    expect(formatDay('2026-12-31')).toBe('Dec 31, 2026')
  })
})

describe('formatTimestamp', () => {
  // Timestamps are instants, unlike due dates, so they show in the browser's time zone, which
  // is Los Angeles in this run (ADR 0018).
  it("shows an instant in the browser's time zone", () => {
    expect(formatTimestamp('2026-11-12T17:05:00Z')).toBe('Nov 12, 2026, 9:05 AM')
  })

  it("shows the browser's day for an instant just after midnight UTC", () => {
    expect(formatTimestamp('2026-11-13T02:30:00Z')).toBe('Nov 12, 2026, 6:30 PM')
  })
})

describe('isDay', () => {
  it.each(['2026-11-12', '2028-02-29'])('accepts %s', (text) => {
    expect(isDay(text)).toBe(true)
  })

  it.each(['2026-02-29', '2026-13-01', '2026-11-1', '12/11/2026', ''])('rejects "%s"', (text) => {
    expect(isDay(text)).toBe(false)
  })
})
