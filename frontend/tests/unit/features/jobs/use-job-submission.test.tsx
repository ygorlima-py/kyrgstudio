import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { submitJob } from '@/features/jobs/api/jobs-api'
import { useJobSubmission } from '@/features/jobs/hooks/use-job-submission'
import { userJobsQueryRootKey } from '@/features/jobs/hooks/use-user-jobs'

vi.mock('@/features/jobs/api/jobs-api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/features/jobs/api/jobs-api')>()

  return {
    ...actual,
    submitJob: vi.fn(),
  }
})

const submitJobMock = vi.mocked(submitJob)

describe('useJobSubmission', () => {
  beforeEach(() => {
    submitJobMock.mockResolvedValue({
      job_id: 72,
      run_id: null,
      status: 'uploaded',
      current_step: 'uploaded',
      pipeline_type: 'copy_analysis',
    })
  })

  it('invalidates every cached history page after creating a job', async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    const invalidateQueries = vi.spyOn(queryClient, 'invalidateQueries')
    const wrapper = createWrapper(queryClient)
    const { result } = renderHook(() => useJobSubmission(), { wrapper })

    await act(async () => {
      await result.current.submit({
        pipeline_type: 'copy_analysis',
        source_type: 'video',
        file: new File(['video'], 'reference.mp4', { type: 'video/mp4' }),
        need_correction: false,
      })
    })

    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: userJobsQueryRootKey,
    })
  })
})

function createWrapper(queryClient: QueryClient) {
  return function TestProviders({ children }: PropsWithChildren) {
    return (
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      </MemoryRouter>
    )
  }
}
