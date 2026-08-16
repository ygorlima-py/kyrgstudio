import axios, { type AxiosResponse } from 'axios'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { apiClient, type JobSubmissionResponse, type PresignedUploadResponse } from '@/shared/api'

import { submitJob } from '@/features/jobs/api/jobs-api'

describe('submitJob', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('prepares, uploads directly to storage, and confirms in order', async () => {
    const file = new File(['video'], 'reference.mp4', {
      type: 'video/mp4',
    })
    const controller = new AbortController()
    const prepareResponse: AxiosResponse<PresignedUploadResponse> = {
      data: {
        job_id: 72,
        object_key: 'jobs/72/input.mp4',
        upload_url: 'https://storage.example.test/upload/72',
        expires_in: 900,
      },
      status: 201,
      statusText: 'Created',
      headers: {},
      config: {} as AxiosResponse['config'],
    }
    const confirmedResponse: AxiosResponse<JobSubmissionResponse> = {
      data: {
        job_id: 72,
        run_id: null,
        status: 'uploaded',
        current_step: 'uploaded',
        pipeline_type: 'copy_analysis',
      },
      status: 200,
      statusText: 'OK',
      headers: {},
      config: {} as AxiosResponse['config'],
    }
    const apiPost = vi
      .spyOn(apiClient, 'post')
      .mockResolvedValueOnce(prepareResponse)
      .mockResolvedValueOnce(confirmedResponse)
    const storagePut = vi.spyOn(axios, 'put').mockResolvedValue({} as AxiosResponse)
    const onUploadProgress = vi.fn()

    const response = await submitJob(
      {
        file,
        metadata: {
          pipeline_type: 'copy_analysis',
          source_type: 'video',
          need_correction: false,
          language: 'pt-BR',
        },
        idempotencyKey: 'submission-key',
      },
      {
        signal: controller.signal,
        onUploadProgress,
      },
    )

    expect(response).toEqual(confirmedResponse.data)
    expect(apiPost).toHaveBeenNthCalledWith(
      1,
      '/jobs/upload-url',
      {
        pipeline: {
          pipeline_type: 'copy_analysis',
          source_type: 'video',
          need_correction: false,
          language: 'pt-BR',
        },
        filename: 'reference.mp4',
        content_type: 'video/mp4',
        size_bytes: file.size,
      },
      {
        headers: { 'Idempotency-Key': 'submission-key' },
        signal: controller.signal,
      },
    )
    expect(storagePut).toHaveBeenCalledWith(
      prepareResponse.data.upload_url,
      file,
      expect.objectContaining({
        signal: controller.signal,
        withCredentials: false,
        headers: { 'Content-Type': 'video/mp4' },
      }),
    )
    expect(apiPost).toHaveBeenNthCalledWith(2, '/jobs/72/upload/complete', undefined, {
      signal: controller.signal,
    })
    expect(onUploadProgress).toHaveBeenLastCalledWith({
      loadedBytes: file.size,
      totalBytes: file.size,
      percentage: 100,
    })
  })

  it('does not confirm the job when the storage upload fails', async () => {
    const file = new File(['video'], 'reference.mp4', {
      type: 'video/mp4',
    })
    const prepareResponse: AxiosResponse<PresignedUploadResponse> = {
      data: {
        job_id: 73,
        object_key: 'jobs/73/input.mp4',
        upload_url: 'https://storage.example.test/upload/73',
        expires_in: 900,
      },
      status: 201,
      statusText: 'Created',
      headers: {},
      config: {} as AxiosResponse['config'],
    }
    const apiPost = vi.spyOn(apiClient, 'post').mockResolvedValueOnce(prepareResponse)
    const storageError = new Error('storage upload failed')

    vi.spyOn(axios, 'put').mockRejectedValue(storageError)

    await expect(
      submitJob({
        file,
        metadata: {
          pipeline_type: 'copy_analysis',
          source_type: 'video',
          need_correction: false,
        },
        idempotencyKey: 'submission-key',
      }),
    ).rejects.toBe(storageError)

    expect(apiPost).toHaveBeenCalledTimes(1)
  })
})
