import { useCallback, useEffect, useMemo } from 'react'
import { useSearchParams } from 'react-router'

import type { JobListPipelineType, JobListStatus } from '../api/jobs-api'

export const JOBS_HISTORY_PAGE_SIZE = 20

const JOB_STATUS_VALUES = [
  'pending',
  'uploaded',
  'running',
  'completed',
  'failed',
] as const satisfies readonly JobListStatus[]

const PIPELINE_TYPE_VALUES = [
  'copy_analysis',
  'copy_adaptation',
] as const satisfies readonly JobListPipelineType[]

const MAX_HISTORY_PAGE = Math.floor(Number.MAX_SAFE_INTEGER / JOBS_HISTORY_PAGE_SIZE)

export interface JobsHistoryFilters {
  readonly jobId: number | undefined
  readonly status: JobListStatus | undefined
  readonly pipelineType: JobListPipelineType | undefined
  readonly page: number
  readonly limit: number
  readonly offset: number
  readonly hasActiveFilters: boolean
}

export interface JobsHistoryFilterActions {
  readonly setJobId: (jobId: number | undefined) => void
  readonly setStatus: (status: JobListStatus | undefined) => void
  readonly setPipelineType: (pipelineType: JobListPipelineType | undefined) => void
  readonly setPage: (page: number) => void
  readonly clearFilters: () => void
}

export interface UseJobsHistoryFiltersResult extends JobsHistoryFilters, JobsHistoryFilterActions {}

/**
 * Keep history filters and pagination synchronized with the browser URL.
 *
 * Defaults are omitted from the query string, producing stable, shareable
 * addresses without maintaining a second copy of filter state in memory.
 */
export function useJobsHistoryFilters(): UseJobsHistoryFiltersResult {
  const [searchParams, setSearchParams] = useSearchParams()

  const filters = useMemo(() => readFilters(searchParams), [searchParams])
  const canonicalSearch = useMemo(() => buildSearchParams(filters).toString(), [filters])

  useEffect(() => {
    if (searchParams.toString() !== canonicalSearch) {
      setSearchParams(canonicalSearch, { replace: true })
    }
  }, [canonicalSearch, searchParams, setSearchParams])

  const setJobId = useCallback(
    (jobId: number | undefined) => {
      if (jobId !== undefined && (!Number.isSafeInteger(jobId) || jobId <= 0)) {
        throw new TypeError('Job id must be a positive integer.')
      }

      setSearchParams(buildSearchParams({ ...filters, jobId, page: 1 }))
    },
    [filters, setSearchParams],
  )

  const setStatus = useCallback(
    (status: JobListStatus | undefined) => {
      setSearchParams(buildSearchParams({ ...filters, status, page: 1 }))
    },
    [filters, setSearchParams],
  )

  const setPipelineType = useCallback(
    (pipelineType: JobListPipelineType | undefined) => {
      setSearchParams(buildSearchParams({ ...filters, pipelineType, page: 1 }))
    },
    [filters, setSearchParams],
  )

  const setPage = useCallback(
    (page: number) => {
      if (!Number.isSafeInteger(page) || page <= 0 || page > MAX_HISTORY_PAGE) {
        throw new TypeError('History page must be a positive integer.')
      }

      setSearchParams(buildSearchParams({ ...filters, page }))
    },
    [filters, setSearchParams],
  )

  const clearFilters = useCallback(() => {
    setSearchParams(new URLSearchParams())
  }, [setSearchParams])

  return {
    ...filters,
    clearFilters,
    setJobId,
    setPage,
    setPipelineType,
    setStatus,
  }
}

function readFilters(searchParams: URLSearchParams): JobsHistoryFilters {
  const jobId = readPositiveInteger(searchParams.get('job_id'))
  const page = readPage(searchParams.get('page'))
  const status = readJobStatus(searchParams.get('status'))
  const pipelineType = readPipelineType(searchParams.get('pipeline_type'))

  return {
    jobId,
    status,
    pipelineType,
    page,
    limit: JOBS_HISTORY_PAGE_SIZE,
    offset: (page - 1) * JOBS_HISTORY_PAGE_SIZE,
    hasActiveFilters: jobId !== undefined || status !== undefined || pipelineType !== undefined,
  }
}

function buildSearchParams(
  filters: Pick<JobsHistoryFilters, 'jobId' | 'page' | 'pipelineType' | 'status'>,
): URLSearchParams {
  const searchParams = new URLSearchParams()

  if (filters.jobId !== undefined) {
    searchParams.set('job_id', String(filters.jobId))
  }

  if (filters.status !== undefined) {
    searchParams.set('status', filters.status)
  }

  if (filters.pipelineType !== undefined) {
    searchParams.set('pipeline_type', filters.pipelineType)
  }

  if (filters.page > 1) {
    searchParams.set('page', String(filters.page))
  }

  return searchParams
}

function readPositiveInteger(value: string | null): number | undefined {
  if (value === null || !/^\d+$/.test(value)) {
    return undefined
  }

  const parsedValue = Number(value)

  return Number.isSafeInteger(parsedValue) && parsedValue > 0 ? parsedValue : undefined
}

function readPage(value: string | null): number {
  const page = readPositiveInteger(value)

  return page !== undefined && page <= MAX_HISTORY_PAGE ? page : 1
}

function readJobStatus(value: string | null): JobListStatus | undefined {
  return JOB_STATUS_VALUES.find((status) => status === value)
}

function readPipelineType(value: string | null): JobListPipelineType | undefined {
  return PIPELINE_TYPE_VALUES.find((pipelineType) => pipelineType === value)
}
