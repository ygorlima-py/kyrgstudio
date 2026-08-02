import { useQuery } from '@tanstack/react-query'

import { getJobResult } from '@/features/jobs'
import type { ApiError } from '@/shared/api'

import {
  AnalysisResultValidationError,
  normalizeAnalysisResult,
  normalizePublicTranscription,
  type NormalizedAnalysisResult,
  type NormalizedTranscription,
} from '../utils/normalize-analysis-result'

export type JobResultQueryError = ApiError | AnalysisResultValidationError

export interface NormalizedCopyAnalysisJobResult {
  readonly analysis: NormalizedAnalysisResult
  readonly transcription: NormalizedTranscription | null
}

/** Stable cache key for the completed result of a persisted job. */
export function jobResultQueryKey(jobId: number) {
  return ['jobs', jobId, 'result'] as const
}

/**
 * Load and validate a completed copy-analysis result.
 *
 * The endpoint returns 404 when the job is absent or belongs to another user,
 * and 409 when processing has not finished. Those controlled API errors remain
 * available to the route through the query state. Completed results are cached
 * indefinitely and are never polled.
 */
export function useJobResult(jobId: number) {
  return useQuery<NormalizedCopyAnalysisJobResult, JobResultQueryError>({
    queryKey: jobResultQueryKey(jobId),
    queryFn: async ({ signal }) => {
      const response = await getJobResult(jobId, { signal })

      if (response.pipeline_type !== 'copy_analysis') {
        throw new AnalysisResultValidationError()
      }

      return {
        analysis: normalizeAnalysisResult(response.output.copy_analysis),
        transcription: normalizePublicTranscription(response.output.transcription),
      }
    },
    refetchOnWindowFocus: false,
    retry: (failureCount, error) => 'retryable' in error && error.retryable && failureCount < 2,
    staleTime: Number.POSITIVE_INFINITY,
  })
}
