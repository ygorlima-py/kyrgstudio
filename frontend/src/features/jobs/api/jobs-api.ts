import type {
  AxiosProgressEvent,
  AxiosRequestConfig,
} from 'axios'

import type { UserProfileData } from '@/features/user-profile/schemas/user-profile-schema'
import {
  apiClient,
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