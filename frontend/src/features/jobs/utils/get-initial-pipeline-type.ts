import {
  pipelineTypeSchema,
  type PipelineType,
} from '../schemas/job-creation-schema'

const PIPELINE_QUERY_PARAMETER = 'pipeline'

/**
 * Reads a valid initial pipeline selection from the dashboard URL.
 */
export function getInitialPipelineType(
  searchParams: URLSearchParams,
): PipelineType | undefined {
  const result = pipelineTypeSchema.safeParse(
    searchParams.get(PIPELINE_QUERY_PARAMETER),
  )

  return result.success ? result.data : undefined
}