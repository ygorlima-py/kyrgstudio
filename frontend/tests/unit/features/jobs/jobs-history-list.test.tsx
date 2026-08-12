import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { JobsHistoryList } from '@/features/jobs/components/jobs-history-list'
import type { JobStatusResponse } from '@/shared/api'
import { i18n } from '@/shared/i18n/i18n'

describe('JobsHistoryList', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
  })

  it('distinguishes an empty history from a filtered search without results', () => {
    const { rerender } = renderHistoryList()

    expect(screen.getByRole('heading', { name: 'No projects yet' })).toBeInTheDocument()

    rerender(
      <MemoryRouter>
        <JobsHistoryList {...defaultProps} hasActiveFilters />
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { name: 'No matching projects' })).toBeInTheDocument()
  })

  it('opens completed jobs as results and other jobs as status pages', () => {
    renderHistoryList({
      jobs: [
        createJob(11, 'completed', 'copy_analysis'),
        createJob(12, 'running', 'copy_adaptation'),
        createJob(13, 'failed', 'copy_analysis'),
      ],
    })

    expect(screen.getByRole('link', { name: /project 11, Completed/ })).toHaveAttribute(
      'href',
      '/app/jobs/11/result',
    )
    expect(screen.getByRole('link', { name: /project 12, Processing/ })).toHaveAttribute(
      'href',
      '/app/jobs/12',
    )
    expect(screen.getByRole('link', { name: /project 13, Failed/ })).toHaveAttribute(
      'href',
      '/app/jobs/13',
    )
  })

  it('provides keyboard-operable pagination with an announced page number', async () => {
    const user = userEvent.setup()
    const onNextPage = vi.fn()
    const onPreviousPage = vi.fn()

    renderHistoryList({
      currentPage: 2,
      hasMore: true,
      jobs: [createJob(21, 'completed', 'copy_analysis')],
      onNextPage,
      onPreviousPage,
    })

    expect(screen.getByRole('navigation', { name: 'Project history pages' })).toBeInTheDocument()
    expect(screen.getByText('Page 2')).toHaveAttribute('aria-live', 'polite')

    const previousButton = screen.getByRole('button', { name: 'Previous' })
    previousButton.focus()
    await user.keyboard('{Enter}')
    await user.click(screen.getByRole('button', { name: 'Next' }))

    expect(onPreviousPage).toHaveBeenCalledOnce()
    expect(onNextPage).toHaveBeenCalledOnce()
  })

  it('exposes a retry action when loading the history fails', async () => {
    const user = userEvent.setup()
    const onRetry = vi.fn()

    renderHistoryList({ isError: true, onRetry })
    await user.click(screen.getByRole('button', { name: 'Try again' }))

    expect(onRetry).toHaveBeenCalledOnce()
  })
})

const defaultProps = {
  currentPage: 1,
  hasActiveFilters: false,
  hasMore: false,
  isError: false,
  isLoading: false,
  jobs: [],
  onClearFilters: vi.fn(),
  onNextPage: vi.fn(),
  onPreviousPage: vi.fn(),
  onRetry: vi.fn(),
} as const

function renderHistoryList(overrides: Partial<Parameters<typeof JobsHistoryList>[0]> = {}) {
  return render(
    <MemoryRouter>
      <JobsHistoryList {...defaultProps} {...overrides} />
    </MemoryRouter>,
  )
}

function createJob(
  jobId: number,
  status: string,
  pipelineType: JobStatusResponse['pipeline_type'],
): JobStatusResponse {
  return {
    job_id: jobId,
    run_id: null,
    pipeline_type: pipelineType,
    status,
    current_step: status,
    created_at: '2026-08-02T12:00:00Z',
    started_at: null,
    finished_at: status === 'completed' || status === 'failed' ? '2026-08-02T12:02:00Z' : null,
    execution_time_seconds: null,
    error: null,
  }
}
