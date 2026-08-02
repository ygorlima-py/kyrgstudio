import { useQuery } from '@tanstack/react-query'

import { getJobResult } from '@/features/jobs'
import type { ApiError } from '@/shared/api'

import {
  AdaptationResultValidationError,
  normalizeAdaptationResult,
  type NormalizedAdaptationResult,
} from '../utils/normalize-adaptation-result'

export type AdaptationJobResultQueryError = ApiError | AdaptationResultValidationError

/** Stable cache key for a normalized copy-adaptation result. */
export function adaptationJobResultQueryKey(jobId: number) {
  return ['jobs', jobId, 'result', 'copy-adaptation'] as const
}

/**
 * Load and validate a completed copy-adaptation result.
 *
 * Controlled 404 and 409 responses remain available through the query error
 * state. Completed results are cached indefinitely and are never polled.
 */
export function useAdaptationResult(jobId: number) {
  return useQuery<NormalizedAdaptationResult, AdaptationJobResultQueryError>({
    queryKey: adaptationJobResultQueryKey(jobId),
    queryFn: async ({ signal }) => {
      const response = await getJobResult(jobId, { signal })

      if (response.pipeline_type !== 'copy_adaptation') {
        throw new AdaptationResultValidationError()
      }

      return normalizeAdaptationResult(response.output)
    },
    refetchInterval: false,
    refetchOnWindowFocus: false,
    retry: (failureCount, error) => 'retryable' in error && error.retryable && failureCount < 2,
    staleTime: Number.POSITIVE_INFINITY,
  })
}
