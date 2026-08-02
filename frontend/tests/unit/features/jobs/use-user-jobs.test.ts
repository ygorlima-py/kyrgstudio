import { describe, expect, it } from 'vitest'

import type { JobListResponse } from '@/features/jobs/api/jobs-api'
import { shouldPollUserJobs, userJobsQueryKey } from '@/features/jobs/hooks/use-user-jobs'

describe('useUserJobs query behavior', () => {
  it('includes every filter and page boundary in the cache key', () => {
    expect(
      userJobsQueryKey({
        jobId: 17,
        status: 'completed',
        pipelineType: 'copy_adaptation',
        limit: 20,
        offset: 40,
      }),
    ).toEqual([
      'jobs',
      'list',
      {
        jobId: 17,
        status: 'completed',
        pipelineType: 'copy_adaptation',
        limit: 20,
        offset: 40,
      },
    ])
  })

  it('polls pages with uploaded or running jobs', () => {
    expect(shouldPollUserJobs(createPage(['completed', 'running']))).toBe(true)
    expect(shouldPollUserJobs(createPage(['uploaded']))).toBe(true)
  })

  it('stops polling when every job reaches a terminal state', () => {
    expect(shouldPollUserJobs(createPage(['completed', 'failed']))).toBe(false)
    expect(shouldPollUserJobs(createPage([]))).toBe(false)
    expect(shouldPollUserJobs(undefined)).toBe(false)
  })
})

function createPage(statuses: readonly string[]): JobListResponse {
  return {
    items: statuses.map((status, index) => ({
      job_id: index + 1,
      run_id: null,
      pipeline_type: 'copy_analysis',
      status,
      current_step: status,
      created_at: '2026-08-02T12:00:00Z',
      started_at: null,
      finished_at: null,
      execution_time_seconds: null,
      error: null,
    })),
    limit: 20,
    offset: 0,
    has_more: false,
  }
}
