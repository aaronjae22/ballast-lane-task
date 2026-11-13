/** The location state a link from the list carries: the list's search, such as "?status=done". */
export interface FromList {
  list: string
}

export function listPathFrom(_state: unknown): string {
  throw new Error('not implemented')
}
