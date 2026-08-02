import { useQuery } from '@tanstack/react-query'

import type { ApiError } from '@/shared/api'

import {
  DEFAULT_USER_JOBS_LIMIT,
  DEFAULT_USER_JOBS_OFFSET,
  listUserJobs,
  type JobListResponse,
  type ListUserJobsOptions,
} from '../api/jobs-api'
import { isActiveJobStatus } from '../config/job-status'

const USER_JOBS_POLL_INTERVAL_MS = 2_500

/** Root key used to invalidate every cached page of the user's job list. */
export const userJobsQueryRootKey = ['jobs', 'list'] as const

export interface UseUserJobsOptions {
  readonly limit?: ListUserJobsOptions['limit']
  readonly offset?: ListUserJobsOptions['offset']
}

/** Stable cache key for one page of the authenticated user's jobs. */
export function userJobsQueryKey(options: UseUserJobsOptions = {}) {
  const limit = options.limit ?? DEFAULT_USER_JOBS_LIMIT
  const offset = options.offset ?? DEFAULT_USER_JOBS_OFFSET

  return [...userJobsQueryRootKey, { limit, offset }] as const
}

/**
 * Keep the authenticated user's selected job page synchronized.
 *
 * Polling runs only while the page contains an uploaded or running job and
 * stops as soon as every returned job reaches a terminal state.
 */
export function useUserJobs(options: UseUserJobsOptions = {}) {
  const limit = options.limit ?? DEFAULT_USER_JOBS_LIMIT
  const offset = options.offset ?? DEFAULT_USER_JOBS_OFFSET

  return useQuery<JobListResponse, ApiError>({
    queryKey: userJobsQueryKey({ limit, offset }),
    queryFn: ({ signal }) => listUserJobs({ limit, offset, signal }),
    refetchInterval: (query) =>
      query.state.data?.items.some((job) => isActiveJobStatus(job.status)) === true
        ? USER_JOBS_POLL_INTERVAL_MS
        : false,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
    retry: (failureCount, error) => error.retryable && failureCount < 2,
    staleTime: 0,
  })
}
