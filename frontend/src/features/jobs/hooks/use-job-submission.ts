import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router'

import {
  normalizeApiError,
  type ApiError,
  type UploadProgress,
} from '@/shared/api'

import { submitJob } from '../api/jobs-api'
import type { JobCreationData } from '../schemas/job-creation-schema'
import { buildJobRequestMetadata } from '../utils/build-job-request'
import { userJobsQueryRootKey } from './use-user-jobs'

export interface UseJobSubmissionResult {
  readonly isSubmitting: boolean
  readonly progress: UploadProgress | null
  readonly error: ApiError | null
  readonly canRetry: boolean
  readonly submit: (formData: JobCreationData) => Promise<void>
  readonly retry: () => Promise<void>
  readonly cancel: () => void
  readonly clearError: () => void
}

/**
 * Coordinates job upload without allowing duplicate simultaneous requests.
 *
 * Failed retries preserve the idempotency key while changes to the submitted
 * data generate a new key.
 */
export function useJobSubmission(): UseJobSubmissionResult {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const activeRequestRef = useRef<AbortController | null>(null)
  const submissionInProgressRef = useRef(false)
  const idempotencyKeyRef = useRef<string | null>(null)
  const submissionIdentityRef = useRef<string | null>(null)
  const lastSubmissionRef = useRef<JobCreationData | null>(null)

  const [isSubmitting, setIsSubmitting] = useState(false)
  const [progress, setProgress] =
    useState<UploadProgress | null>(null)
  const [error, setError] = useState<ApiError | null>(null)

  useEffect(() => {
    return () => {
      activeRequestRef.current?.abort()
    }
  }, [])

  const submit = useCallback(
    async (formData: JobCreationData): Promise<void> => {
      if (submissionInProgressRef.current) {
        return
      }

      lastSubmissionRef.current = formData

      const metadata = buildJobRequestMetadata(formData)
      const submissionIdentity = buildSubmissionIdentity(
        formData,
        metadata,
      )

      if (
        submissionIdentityRef.current !== submissionIdentity ||
        idempotencyKeyRef.current === null
      ) {
        submissionIdentityRef.current = submissionIdentity
        idempotencyKeyRef.current = crypto.randomUUID()
      }

      const controller = new AbortController()
      const idempotencyKey = idempotencyKeyRef.current

      activeRequestRef.current = controller
      submissionInProgressRef.current = true
      setIsSubmitting(true)
      setError(null)
      setProgress({
        loadedBytes: 0,
        totalBytes: formData.file.size,
        percentage: 0,
      })

      try {
        const response = await submitJob(
          {
            file: formData.file,
            metadata,
            idempotencyKey,
          },
          {
            signal: controller.signal,
            onUploadProgress: setProgress,
          },
        )

        idempotencyKeyRef.current = null
        submissionIdentityRef.current = null
        lastSubmissionRef.current = null

        void queryClient.invalidateQueries({
          queryKey: userJobsQueryRootKey,
        })

        void navigate(`/app/jobs/${response.job_id}`)
      } catch (submissionError) {
        const normalizedError =
          normalizeApiError(submissionError)

        setProgress(null)

        if (normalizedError.code !== 'request_cancelled') {
          setError(normalizedError)
        }
      } finally {
        activeRequestRef.current = null
        submissionInProgressRef.current = false
        setIsSubmitting(false)
      }
    },
    [navigate, queryClient],
  )

  const cancel = useCallback(() => {
    activeRequestRef.current?.abort()
  }, [])

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  const retry = useCallback(async (): Promise<void> => {
    const lastSubmission = lastSubmissionRef.current

    if (lastSubmission === null) {
      return
    }

    await submit(lastSubmission)
  }, [submit])

  const canRetry = error?.retryable === true

  return {
    isSubmitting,
    progress,
    error,
    canRetry,
    submit,
    retry,
    cancel,
    clearError,
  }
}

function buildSubmissionIdentity(
  formData: JobCreationData,
  metadata: ReturnType<typeof buildJobRequestMetadata>,
): string {
  return JSON.stringify({
    file: {
      name: formData.file.name,
      size: formData.file.size,
      type: formData.file.type,
      lastModified: formData.file.lastModified,
    },
    metadata,
  })
}
