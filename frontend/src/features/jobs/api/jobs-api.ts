import axios from 'axios'
import type { AxiosProgressEvent, AxiosRequestConfig } from 'axios'

import type { UserProfileData } from '@/features/user-profile/schemas/user-profile-schema'
import {
  apiClient,
  type ApiOperations,
  type ApiRequestOptions,
  type JobResultResponse,
  type JobStatusResponse,
  type JobSubmissionResponse,
  type PresignedUploadRequest,
  type PresignedUploadResponse,
  type UploadProgress,
  type UploadRequestOptions,
} from '@/shared/api'

import type { SourceType } from '../schemas/job-creation-schema'

interface BaseJobRequestMetadata {
  readonly source_type: SourceType
  readonly language?: string
  readonly need_correction: boolean
}

export interface CopyAnalysisJobRequestMetadata extends BaseJobRequestMetadata {
  readonly pipeline_type: 'copy_analysis'
}

export interface CopyAdaptationJobRequestMetadata extends BaseJobRequestMetadata {
  readonly pipeline_type: 'copy_adaptation'
  readonly user_profile: UserProfileData
}

export type JobRequestMetadata = CopyAnalysisJobRequestMetadata | CopyAdaptationJobRequestMetadata

export interface SubmitJobRequest {
  readonly file: File
  readonly metadata: JobRequestMetadata
  readonly idempotencyKey: string
}

type ListUserJobsOperation = ApiOperations['list_jobs_v1_jobs_get']

type ListUserJobsQuery = NonNullable<ListUserJobsOperation['parameters']['query']>

export type JobListResponse = ListUserJobsOperation['responses'][200]['content']['application/json']
export type JobListStatus = NonNullable<ListUserJobsQuery['status']>
export type JobListPipelineType = NonNullable<ListUserJobsQuery['pipeline_type']>

export interface ListUserJobsOptions extends ApiRequestOptions {
  readonly jobId?: NonNullable<ListUserJobsQuery['job_id']>
  readonly status?: JobListStatus
  readonly pipelineType?: JobListPipelineType
  readonly limit?: ListUserJobsQuery['limit']
  readonly offset?: ListUserJobsQuery['offset']
}

export const DEFAULT_USER_JOBS_LIMIT = 20
export const DEFAULT_USER_JOBS_OFFSET = 0
const MAX_USER_JOBS_LIMIT = 100

/**
 * Prepares, uploads, and confirms a media file through object storage.
 *
 * Authentication is intentionally limited to the API calls. The signed PUT
 * uses the standalone Axios transport so browser cookies and bearer headers
 * are never sent to the storage provider.
 */
export async function submitJob(
  request: SubmitJobRequest,
  options: UploadRequestOptions = {},
): Promise<JobSubmissionResponse> {
  const idempotencyKey = request.idempotencyKey.trim()

  if (!idempotencyKey) {
    throw new TypeError('Job idempotency key is required.')
  }

  const prepareRequestConfig: AxiosRequestConfig = {
    headers: {
      'Idempotency-Key': idempotencyKey,
    },
  }

  if (options.signal !== undefined) {
    prepareRequestConfig.signal = options.signal
  }

  const uploadRequest: PresignedUploadRequest = {
    pipeline: toPresignedPipeline(request.metadata),
    filename: request.file.name,
    content_type: request.file.type,
    size_bytes: request.file.size,
  }

  const prepareResponse = await apiClient.post<PresignedUploadResponse>(
    '/jobs/upload-url',
    uploadRequest,
    prepareRequestConfig,
  )

  const uploadConfig: AxiosRequestConfig<File> = {
    headers: {
      'Content-Type': request.file.type,
    },
    withCredentials: false,
  }

  if (options.signal !== undefined) {
    uploadConfig.signal = options.signal
  }

  if (options.onUploadProgress !== undefined) {
    uploadConfig.onUploadProgress = (event) => {
      options.onUploadProgress?.(normalizeUploadProgress(event))
    }
  }

  await axios.put(prepareResponse.data.upload_url, request.file, uploadConfig)

  options.onUploadProgress?.({
    loadedBytes: request.file.size,
    totalBytes: request.file.size,
    percentage: 100,
  })

  const confirmRequestConfig: AxiosRequestConfig = {}

  if (options.signal !== undefined) {
    confirmRequestConfig.signal = options.signal
  }

  const confirmResponse = await apiClient.post<JobSubmissionResponse>(
    `/jobs/${prepareResponse.data.job_id}/upload/complete`,
    undefined,
    confirmRequestConfig,
  )

  return confirmResponse.data
}

function toPresignedPipeline(metadata: JobRequestMetadata): PresignedUploadRequest['pipeline'] {
  const commonMetadata = {
    source_type: metadata.source_type,
    need_correction: metadata.need_correction,
    ...(metadata.language !== undefined ? { language: metadata.language } : {}),
  }

  if (metadata.pipeline_type === 'copy_analysis') {
    return {
      ...commonMetadata,
      pipeline_type: 'copy_analysis',
    }
  }

  const profile = metadata.user_profile

  return {
    ...commonMetadata,
    pipeline_type: 'copy_adaptation',
    user_profile: {
      product_or_solution: profile.product_or_solution,
      target_audience: profile.target_audience,
      core_problem: profile.core_problem,
      core_desire: profile.core_desire,
      main_promise: profile.main_promise,
      call_to_action: profile.call_to_action,
      desired_duration: profile.desired_duration,
      ...(profile.unique_mechanism !== undefined
        ? { unique_mechanism: profile.unique_mechanism }
        : {}),
      ...(profile.benefits.length > 0 ? { benefits: [...profile.benefits] } : {}),
      ...(profile.objections.length > 0 ? { objections: [...profile.objections] } : {}),
      ...(profile.proof_assets.length > 0 ? { proof_assets: [...profile.proof_assets] } : {}),
      ...(profile.offer_details !== undefined ? { offer_details: profile.offer_details } : {}),
      ...(profile.tone !== undefined ? { tone: profile.tone } : {}),
      ...(profile.target_language !== undefined
        ? { target_language: profile.target_language }
        : {}),
      ...(profile.platform !== undefined ? { platform: profile.platform } : {}),
      ...(profile.restrictions.length > 0 ? { restrictions: [...profile.restrictions] } : {}),
    },
  }
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

  const response = await apiClient.get<JobStatusResponse>(`/jobs/${jobId}`, requestConfig)

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

  const response = await apiClient.get<JobResultResponse>(`/jobs/${jobId}/result`, requestConfig)

  return response.data
}

/** Fetch one page of jobs owned by the authenticated user. */
export async function listUserJobs(options: ListUserJobsOptions = {}): Promise<JobListResponse> {
  const jobId = options.jobId
  const limit = options.limit ?? DEFAULT_USER_JOBS_LIMIT
  const offset = options.offset ?? DEFAULT_USER_JOBS_OFFSET

  if (jobId !== undefined) {
    validateJobId(jobId)
  }

  validateUserJobsPagination(limit, offset)

  const requestConfig: AxiosRequestConfig = {
    params: {
      ...(jobId === undefined ? {} : { job_id: jobId }),
      ...(options.status === undefined ? {} : { status: options.status }),
      ...(options.pipelineType === undefined ? {} : { pipeline_type: options.pipelineType }),
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

function validateJobId(jobId: number): void {
  if (!Number.isSafeInteger(jobId) || jobId <= 0) {
    throw new TypeError('Job id must be a positive integer.')
  }
}

function validateUserJobsPagination(limit: number, offset: number): void {
  if (!Number.isSafeInteger(limit) || limit <= 0 || limit > MAX_USER_JOBS_LIMIT) {
    throw new TypeError(`Job list limit must be an integer between 1 and ${MAX_USER_JOBS_LIMIT}.`)
  }

  if (!Number.isSafeInteger(offset) || offset < 0) {
    throw new TypeError('Job list offset must be a non-negative integer.')
  }
}

function normalizeUploadProgress(event: AxiosProgressEvent): UploadProgress {
  const totalBytes =
    typeof event.total === 'number' && Number.isFinite(event.total) && event.total > 0
      ? event.total
      : null

  const percentage =
    totalBytes === null ? null : Math.min(100, Math.round((event.loaded / totalBytes) * 100))

  return {
    loadedBytes: event.loaded,
    totalBytes,
    percentage,
  }
}
