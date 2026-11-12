// Due dates are plain days, YYYY-MM-DD, and never become a Date in the browser's time zone
// (ADR 0018).

const dayPattern = /^(\d{4})-(\d{2})-(\d{2})$/

/** Whether text is a real calendar day as YYYY-MM-DD: 2026-02-30 isn't. */
export function isDay(text: string): boolean {
  const match = dayPattern.exec(text)
  if (!match) return false
  const [year, month, day] = match.slice(1).map(Number) as [number, number, number]
  // Date.UTC rolls an impossible day over into the next month, so a round trip catches it.
  const date = new Date(Date.UTC(year, month - 1, day))
  return (
    date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day
  )
}
