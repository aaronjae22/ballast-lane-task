import { Group, Select, TextInput } from '@mantine/core'
import { useDebouncedCallback } from '@mantine/hooks'
import { useState } from 'react'
import type { Ordering, TaskFilters as Filters } from '../filters'
import type { TaskFiltersState } from '../hooks/useTaskFilters'

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

/** The controls above the list. Each one writes to the URL; none keeps a filter of its own. */
export function TaskFilters({ filters, setFilters }: TaskFiltersProps) {
  return (
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
    </Group>
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
