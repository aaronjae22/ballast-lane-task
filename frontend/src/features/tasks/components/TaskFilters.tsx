import {
  Button,
  Chip,
  Collapse,
  Group,
  SegmentedControl,
  Select,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
} from '@mantine/core'
import { DatePickerInput } from '@mantine/dates'
import { useDebouncedCallback, useDisclosure } from '@mantine/hooks'
import { useId, useState, type ReactNode } from 'react'
import { useActiveUsers } from '../../users/hooks/useActiveUsers'
import { statuses, type Ordering, type TaskFilters as Filters } from '../filters'
import type { TaskFiltersState } from '../hooks/useTaskFilters'
import { useWideScreen } from '../hooks/useWideScreen'
import { statusLabels } from './TaskStatusBadge'

// The API's default order is the soonest due date (ADR 0014), so that choice sends nothing.
const defaultOrdering = 'due_date'
const orderingOptions: { value: Ordering; label: string }[] = [
  { value: 'due_date', label: 'Due date, soonest first' },
  { value: '-due_date', label: 'Due date, latest first' },
  { value: '-created_at', label: 'Newest first' },
  { value: 'created_at', label: 'Oldest first' },
  { value: 'status', label: 'Status, to do first' },
  { value: '-status', label: 'Status, done first' },
]

interface TaskFiltersProps {
  filters: Filters
  setFilters: TaskFiltersState['setFilters']
}

/**
 * The controls above the list. Each one writes to the URL; none keeps a filter of its own.
 * Search and order always show. Below the `sm` breakpoint the filters fold behind a button
 * that counts the active ones, so the list isn't pushed off a phone's screen (ADR 0018).
 */
export function TaskFilters({ filters, setFilters }: TaskFiltersProps) {
  const wide = useWideScreen()
  const [opened, { toggle }] = useDisclosure(false)
  const panelId = useId()
  const active = [
    filters.status.length > 0,
    filters.due_after !== null,
    filters.due_before !== null,
    filters.overdue !== null,
    filters.assignee !== null,
  ].filter(Boolean).length
  const fields = <FilterFields filters={filters} setFilters={setFilters} />

  return (
    <Stack gap="sm">
      <Group align="flex-end" gap="sm" wrap="wrap">
        <SearchBox
          value={filters.search}
          onSearch={(search) => {
            if (search === filters.search) return
            // Starting a search adds a history entry, so Back undoes it. Refining or clearing
            // one replaces that entry, so Back doesn't step through every pause in typing.
            setFilters({ search }, { replace: filters.search !== '' })
          }}
        />
        <Select
          label="Order"
          data={orderingOptions}
          value={filters.ordering ?? defaultOrdering}
          allowDeselect={false}
          onChange={(value) => {
            const ordering = orderingOptions.find((option) => option.value === value)?.value
            if (ordering === undefined) return
            setFilters({ ordering: ordering === defaultOrdering ? null : ordering })
          }}
          w={{ base: '100%', xs: 240 }}
        />
        {!wide && (
          <Button variant="default" onClick={toggle} aria-expanded={opened} aria-controls={panelId}>
            {active > 0 ? `Filters (${String(active)})` : 'Filters'}
          </Button>
        )}
      </Group>
      {wide ? (
        fields
      ) : (
        <Collapse expanded={opened} id={panelId}>
          {fields}
        </Collapse>
      )}
    </Stack>
  )
}

function FilterFields({ filters, setFilters }: TaskFiltersProps) {
  const users = useActiveUsers()
  const assignees = [
    { value: 'me', label: 'Me' },
    ...(users.data ?? []).map((user) => ({ value: String(user.id), label: user.name })),
  ]
  // A link can name a user who isn't active any more, or isn't in the list yet: still show
  // the value, rather than an empty box that hides an active filter (ADR 0018).
  const assignee = filters.assignee === null ? null : String(filters.assignee)
  if (assignee !== null && !assignees.some((option) => option.value === assignee)) {
    assignees.push({ value: assignee, label: `User #${assignee}` })
  }

  return (
    <SimpleGrid cols={{ base: 1, xs: 2, md: 3 }} spacing="sm">
      <Field label="Status">
        <Chip.Group
          multiple
          value={filters.status}
          onChange={(values) => {
            setFilters({ status: statuses.filter((status) => values.includes(status)) })
          }}
        >
          <Group gap="xs">
            {statuses.map((status) => (
              <Chip key={status} value={status} size="sm">
                {statusLabels[status]}
              </Chip>
            ))}
          </Group>
        </Chip.Group>
      </Field>
      <Field label="Overdue">
        <SegmentedControl
          fullWidth
          data={[
            { value: 'any', label: 'Any' },
            { value: 'true', label: 'Overdue' },
            { value: 'false', label: 'Not overdue' },
          ]}
          value={filters.overdue === null ? 'any' : String(filters.overdue)}
          onChange={(value) => {
            setFilters({ overdue: value === 'any' ? null : value === 'true' })
          }}
        />
      </Field>
      <Select
        label="Assignee"
        placeholder="Anyone"
        clearable
        data={assignees}
        value={assignee}
        onChange={(value) => {
          setFilters({ assignee: value === null ? null : value === 'me' ? 'me' : Number(value) })
        }}
      />
      {/* Due dates stay YYYY-MM-DD strings from the picker to the API (ADR 0018). */}
      <DatePickerInput
        label="Due from"
        placeholder="Any day"
        clearable
        clearButtonProps={{ 'aria-label': 'Clear due from' }}
        valueFormat="MMM D, YYYY"
        value={filters.due_after}
        onChange={(due_after) => {
          setFilters({ due_after })
        }}
      />
      <DatePickerInput
        label="Due until"
        placeholder="Any day"
        clearable
        clearButtonProps={{ 'aria-label': 'Clear due until' }}
        valueFormat="MMM D, YYYY"
        value={filters.due_before}
        onChange={(due_before) => {
          setFilters({ due_before })
        }}
      />
    </SimpleGrid>
  )
}

/** A labelled group of controls that have no label of their own, such as chips. */
function Field({ label, children }: { label: string; children: ReactNode }) {
  const labelId = useId()
  return (
    <Stack gap={4} role="group" aria-labelledby={labelId}>
      <Text id={labelId} size="sm" fw={500}>
        {label}
      </Text>
      {children}
    </Stack>
  )
}

/** A text box whose value goes to the URL 300 ms after typing stops. */
function SearchBox({ value, onSearch }: { value: string; onSearch: (search: string) => void }) {
  const [text, setText] = useState(value)
  // When the URL's search changes without typing (Back, Clear filters), the box follows it.
  // Set during render, React's pattern for state that follows a prop, so it never lags a frame.
  const [shown, setShown] = useState(value)
  if (value !== shown) {
    setShown(value)
    if (value !== text.trim()) setText(value)
  }
  // Each keystroke notes the URL's search it was typed over. If the URL has moved since
  // (Back, Clear filters), the user has left that search, so it's dropped instead of written
  // back over their navigation. The debounced callback always sees the latest `value`.
  const search = useDebouncedCallback((next: string, typedOver: string) => {
    if (typedOver !== value) return
    onSearch(next.trim())
  }, 300)

  return (
    <TextInput
      label="Search titles"
      type="search"
      value={text}
      onChange={(event) => {
        setText(event.currentTarget.value)
        search(event.currentTarget.value, value)
      }}
      style={{ flex: '1 1 220px' }}
    />
  )
}
