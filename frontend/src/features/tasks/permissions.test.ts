import { describe, expect, it } from 'vitest'
import { users } from '../../test/handlers'
import { aTask, summaryOf } from '../../test/tasks'
import { can, transitionsFrom, type Action, type Transition } from './permissions'

// The permission matrix of spec section 3, row for row as backend/tests/unit/permission_matrix.py
// has it. A change to one needs the same change to the other (ADR 0018, AGENTS.md). The API
// answers "anyone else" with 404; here they simply get no action.

const roles = ['owner', 'assignee', 'admin', 'anyone else'] as const
type Role = (typeof roles)[number]

// prettier-ignore
const matrix: Record<Action, [boolean, boolean, boolean, boolean]> = {
  //              owner  assignee admin  anyone else
  view:          [true,  true,    true,  false],
  edit:          [true,  false,   true,  false],
  assign:        [true,  false,   true,  false],
  change_status: [true,  true,    true,  false],
  delete:        [true,  false,   true,  false],
}

// alice owns the task and bob is its assignee; carol is neither.
const task = aTask({ owner: summaryOf(users.alice), assignee: summaryOf(users.bob) })
const admin = { id: 99, is_admin: true }
const userFor: Record<Role, { id: number; is_admin: boolean }> = {
  owner: users.alice,
  assignee: users.bob,
  admin,
  'anyone else': users.carol,
}

const cells = (Object.entries(matrix) as [Action, boolean[]][]).flatMap(([action, row]) =>
  roles.map((role, column) => [action, role, row[column]] as const),
)

describe('the permission matrix', () => {
  it.each(cells)('%s by the %s: %s', (action, role, allowed) => {
    expect(can(userFor[role], task, action)).toBe(allowed)
  })
})

describe('people in more than one role', () => {
  const actions = Object.keys(matrix) as Action[]

  it('an owner who is also the assignee may do everything', () => {
    const own = aTask({ owner: summaryOf(users.alice), assignee: summaryOf(users.alice) })

    expect(actions.filter((action) => can(users.alice, own, action))).toEqual(actions)
  })

  it('an admin may do everything to an unassigned task someone else owns', () => {
    const unassigned = aTask({ owner: summaryOf(users.bob), assignee: null })

    expect(actions.filter((action) => can(admin, unassigned, action))).toEqual(actions)
  })

  it('nobody is the assignee of an unassigned task', () => {
    const unassigned = aTask({ owner: summaryOf(users.alice), assignee: null })

    expect(actions.filter((action) => can(users.bob, unassigned, action))).toEqual([])
  })
})

describe('before the signed-in user has loaded', () => {
  it('nothing is offered', () => {
    expect((Object.keys(matrix) as Action[]).some((action) => can(undefined, task, action))).toBe(
      false,
    )
  })
})

// The status transitions of spec section 3, as _TRANSITIONS in backend/tasks/domain/task.py
// has them: which buttons a task shows. The API still answers any other move with 409.
describe('the transitions each status offers', () => {
  it.each([
    ['to_do', ['start', 'complete']],
    ['in_progress', ['complete']],
    ['done', ['reopen']],
  ] as const)('%s: %j', (status, transitions: readonly Transition[]) => {
    expect(transitionsFrom(status)).toEqual(transitions)
  })
})
