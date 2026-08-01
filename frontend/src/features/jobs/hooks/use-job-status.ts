import { useQuery } from '@tanstack/react-query'

import type { ApiError, JobStatusResponse } from '@/shared/api'

import { getJobStatus } from '../api/jobs-api'
import { isActiveJobStatus } from '../config/job-status'

const JOB_STATUS_POLL_INTERVAL_MS = 2_500

/** Stable query key used by status pages and future job cache invalidation. */
export function jobStatusQueryKey(jobId: number) {
  return ['jobs', jobId, 'status'] as const
}

/**
 * Keep an active job synchronized with the persisted backend state.
 *
 * Polling stops automatically for completed or failed jobs. TanStack Query
 * keeps the latest successful response visible during temporary refresh
 * failures and forwards AbortSignal to Axios when the observer is removed.
 */
export function useJobStatus(jobId: number) {
  return useQuery<JobStatusResponse, ApiError>({
    queryKey: jobStatusQueryKey(jobId),
    queryFn: ({ signal }) => getJobStatus(jobId, { signal }),
    refetchInterval: (query) =>
      isActiveJobStatus(query.state.data?.status)
        ? JOB_STATUS_POLL_INTERVAL_MS
        : false,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
    retry: (failureCount, error) =>
      error.retryable && failureCount < 2,
    staleTime: 0,
  })
}
