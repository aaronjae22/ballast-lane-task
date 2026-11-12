import { Group, Pagination } from '@mantine/core'
import { pageSize } from '../filters'

interface TaskPaginationProps {
  /** Tasks across every page, from the API's count. */
  count: number
  page: number
  onChange: (page: number) => void
}

/** Page buttons below the list, or nothing when every task fits on one page. */
export function TaskPagination({ count, page, onChange }: TaskPaginationProps) {
  const pages = Math.ceil(count / pageSize)
  if (pages <= 1) return null
  return (
    <Group justify="center">
      <Pagination
        total={pages}
        value={page}
        onChange={onChange}
        siblings={1}
        boundaries={1}
        getControlProps={(control) =>
          control === 'previous'
            ? { 'aria-label': 'Previous page' }
            : control === 'next'
              ? { 'aria-label': 'Next page' }
              : {}
        }
      />
    </Group>
  )
}
