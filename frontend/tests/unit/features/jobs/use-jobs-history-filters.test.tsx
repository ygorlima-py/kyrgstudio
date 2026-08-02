import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, useLocation } from 'react-router'
import { describe, expect, it } from 'vitest'

import { useJobsHistoryFilters } from '@/features/jobs/hooks/use-jobs-history-filters'

describe('useJobsHistoryFilters', () => {
  it('reads combined filters and pagination from the URL', () => {
    renderHistoryFilters('/app/jobs?job_id=41&status=running&pipeline_type=copy_adaptation&page=3')

    expect(screen.getByTestId('job-id')).toHaveTextContent('41')
    expect(screen.getByTestId('status')).toHaveTextContent('running')
    expect(screen.getByTestId('pipeline-type')).toHaveTextContent('copy_adaptation')
    expect(screen.getByTestId('page')).toHaveTextContent('3')
    expect(screen.getByTestId('offset')).toHaveTextContent('40')
  })

  it('returns to the first page when a filter changes', async () => {
    const user = userEvent.setup()

    renderHistoryFilters('/app/jobs?pipeline_type=copy_analysis&page=4')
    await user.click(screen.getByRole('button', { name: 'Filter running jobs' }))

    expect(screen.getByTestId('page')).toHaveTextContent('1')
    expect(screen.getByTestId('location-search')).toHaveTextContent(
      '?status=running&pipeline_type=copy_analysis',
    )
  })

  it('calculates the next page offset while preserving filters', async () => {
    const user = userEvent.setup()

    renderHistoryFilters('/app/jobs?status=completed')
    await user.click(screen.getByRole('button', { name: 'Next page' }))

    expect(screen.getByTestId('page')).toHaveTextContent('2')
    expect(screen.getByTestId('offset')).toHaveTextContent('20')
    expect(screen.getByTestId('location-search')).toHaveTextContent('?status=completed&page=2')
  })

  it('clears filters and pagination together', async () => {
    const user = userEvent.setup()

    renderHistoryFilters('/app/jobs?job_id=9&status=failed&page=2')
    await user.click(screen.getByRole('button', { name: 'Clear history filters' }))

    expect(screen.getByTestId('location-search')).toBeEmptyDOMElement()
    expect(screen.getByTestId('page')).toHaveTextContent('1')
    expect(screen.getByTestId('has-filters')).toHaveTextContent('false')
  })

  it('removes unsupported and malformed query parameters', async () => {
    renderHistoryFilters('/app/jobs?job_id=nope&status=unknown&page=-2&unexpected=value')

    await waitFor(() => {
      expect(screen.getByTestId('location-search')).toBeEmptyDOMElement()
    })
  })
})

function renderHistoryFilters(initialEntry: string) {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <HistoryFiltersHarness />
    </MemoryRouter>,
  )
}

function HistoryFiltersHarness() {
  const filters = useJobsHistoryFilters()
  const location = useLocation()

  return (
    <>
      <output data-testid="job-id">{filters.jobId ?? 'none'}</output>
      <output data-testid="status">{filters.status ?? 'none'}</output>
      <output data-testid="pipeline-type">{filters.pipelineType ?? 'none'}</output>
      <output data-testid="page">{filters.page}</output>
      <output data-testid="offset">{filters.offset}</output>
      <output data-testid="has-filters">{String(filters.hasActiveFilters)}</output>
      <output data-testid="location-search">{location.search}</output>

      <button onClick={() => filters.setStatus('running')} type="button">
        Filter running jobs
      </button>
      <button onClick={() => filters.setPage(filters.page + 1)} type="button">
        Next page
      </button>
      <button onClick={filters.clearFilters} type="button">
        Clear history filters
      </button>
    </>
  )
}
