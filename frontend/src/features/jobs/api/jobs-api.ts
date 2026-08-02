import type {
  AxiosProgressEvent,
  AxiosRequestConfig,
} from 'axios'

import type { UserProfileData } from '@/features/user-profile/schemas/user-profile-schema'
import {
  apiClient,
  type ApiOperations,
  type ApiRequestOptions,
  type JobResultResponse,
  type JobStatusResponse,
  type JobSubmissionResponse,
  type UploadProgress,
  type UploadRequestOptions,
} from '@/shared/api'

import type {
  SourceType,
} from '../schemas/job-creation-schema'

interface BaseJobRequestMetadata {
  readonly source_type: SourceType
  readonly language?: string
  readonly need_correction: boolean
}

export interface CopyAnalysisJobRequestMetadata
  extends BaseJobRequestMetadata {
  readonly pipeline_type: 'copy_analysis'
}

export interface CopyAdaptationJobRequestMetadata
  extends BaseJobRequestMetadata {
  readonly pipeline_type: 'copy_adaptation'
  readonly user_profile: UserProfileData
}

export type JobRequestMetadata =
  | CopyAnalysisJobRequestMetadata
  | CopyAdaptationJobRequestMetadata

export interface SubmitJobRequest {
  readonly file: File
  readonly metadata: JobRequestMetadata
  readonly idempotencyKey: string
}

type ListUserJobsOperation = ApiOperations['list_jobs_v1_jobs_get']

type ListUserJobsQuery = NonNullable<ListUserJobsOperation['parameters']['query']>

export type JobListResponse = ListUserJobsOperation['responses'][200]['content']['application/json']

export interface ListUserJobsOptions extends ApiRequestOptions {
  readonly limit?: ListUserJobsQuery['limit']
  readonly offset?: ListUserJobsQuery['offset']
}

export const DEFAULT_USER_JOBS_LIMIT = 20
export const DEFAULT_USER_JOBS_OFFSET = 0
const MAX_USER_JOBS_LIMIT = 100

/**
 * Uploads a media file and its pipeline configuration as multipart data.
 */
export async function submitJob(
  request: SubmitJobRequest,
  options: UploadRequestOptions = {},
): Promise<JobSubmissionResponse> {
  const idempotencyKey = request.idempotencyKey.trim()

  if (!idempotencyKey) {
    throw new TypeError('Job idempotency key is required.')
  }

  const formData = new FormData()

  formData.append('file', request.file, request.file.name)
  formData.append('request', JSON.stringify(request.metadata))

  const requestConfig: AxiosRequestConfig<FormData> = {
    headers: {
      'Idempotency-Key': idempotencyKey,
    },
  }

  if (options.signal !== undefined) {
    requestConfig.signal = options.signal
  }

  if (options.onUploadProgress !== undefined) {
    requestConfig.onUploadProgress = (event) => {
      options.onUploadProgress?.(normalizeUploadProgress(event))
    }
  }

  const response = await apiClient.post<JobSubmissionResponse>(
    '/jobs',
    formData,
    requestConfig,
  )

  return response.data
}

/** Fetch the latest public state of one job owned by the current user. */
export async function getJobStatus(
  jobId: number,
  options: ApiRequestOptions = {},
): Promise<JobStatusResponse> {
  if (!Number.isSafeInteger(jobId) || jobId <= 0) {
    throw new TypeError('Job id must be a positive integer.')
  }

  const requestConfig: AxiosRequestConfig = {}

  if (options.signal !== undefined) {
    requestConfig.signal = options.signal
  }

  const response = await apiClient.get<JobStatusResponse>(
    `/jobs/${jobId}`,
    requestConfig,
  )

  return response.data
}

/** Fetch the completed public result of one job owned by the current user. */
export async function getJobResult(
  jobId: number,
  options: ApiRequestOptions = {},
): Promise<JobResultResponse> {
  if (!Number.isSafeInteger(jobId) || jobId <= 0) {
    throw new TypeError('Job id must be a positive integer.')
  }

  const requestConfig: AxiosRequestConfig = {}

  if (options.signal !== undefined) {
    requestConfig.signal = options.signal
  }

  const response = await apiClient.get<JobResultResponse>(
    `/jobs/${jobId}/result`,
    requestConfig,
  )

  return response.data
}

/** Fetch one page of jobs owned by the authenticated user. */
export async function listUserJobs(options: ListUserJobsOptions = {}): Promise<JobListResponse> {
  const limit = options.limit ?? DEFAULT_USER_JOBS_LIMIT
  const offset = options.offset ?? DEFAULT_USER_JOBS_OFFSET

  validateUserJobsPagination(limit, offset)

  const requestConfig: AxiosRequestConfig = {
    params: {
      limit,
      offset,
    } satisfies ListUserJobsQuery,
  }

  if (options.signal !== undefined) {
    requestConfig.signal = options.signal
  }

  const response = await apiClient.get<JobListResponse>('/jobs', requestConfig)

  return response.data
}

function validateUserJobsPagination(limit: number, offset: number): void {
  if (!Number.isSafeInteger(limit) || limit <= 0 || limit > MAX_USER_JOBS_LIMIT) {
    throw new TypeError(`Job list limit must be an integer between 1 and ${MAX_USER_JOBS_LIMIT}.`)
  }

  if (!Number.isSafeInteger(offset) || offset < 0) {
    throw new TypeError('Job list offset must be a non-negative integer.')
  }
}

function normalizeUploadProgress(
  event: AxiosProgressEvent,
): UploadProgress {
  const totalBytes =
    typeof event.total === 'number' &&
    Number.isFinite(event.total) &&
    event.total > 0
      ? event.total
      : null

  const percentage =
    totalBytes === null
      ? null
      : Math.min(
          100,
          Math.round((event.loaded / totalBytes) * 100),
        )

  return {
    loadedBytes: event.loaded,
    totalBytes,
    percentage,
  }
}
