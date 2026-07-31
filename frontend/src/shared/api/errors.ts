import { isAxiosError, isCancel } from 'axios'

import type { ApiErrorResponse } from './types'

const GENERIC_REQUEST_MESSAGE = 'The request could not be completed.'

interface ApiErrorOptions {
  code: string
  status: number | null
  step: string | null
  details: Record<string, unknown>
  retryable: boolean
}

/**
 * Represents a safe and normalized failure returned by the HTTP layer.
 *
 * User-facing messages must be selected from `code`. Raw provider, server,
 * Axios or network messages are intentionally not exposed.
 */
export class ApiError extends Error {
  readonly code: string
  readonly status: number | null
  readonly step: string | null
  readonly details: Readonly<Record<string, unknown>>
  readonly retryable: boolean

  constructor(options: ApiErrorOptions) {
    super(GENERIC_REQUEST_MESSAGE)

    this.name = 'ApiError'
    this.code = options.code
    this.status = options.status
    this.step = options.step
    this.details = Object.freeze({ ...options.details })
    this.retryable = options.retryable
  }
}

/**
 * Converts any request failure into the application's stable error contract.
 */
export function normalizeApiError(error: unknown): ApiError {
  if (error instanceof ApiError) {
    return error
  }

  if (isCancel(error)) {
    return new ApiError({
      code: 'request_cancelled',
      status: null,
      step: null,
      details: {},
      retryable: false,
    })
  }

  if (!isAxiosError<unknown>(error)) {
    return new ApiError({
      code: 'unexpected_error',
      status: null,
      step: null,
      details: {},
      retryable: false,
    })
  }

  const status = error.response?.status ?? null
  const response = parseApiErrorResponse(error.response?.data)

  if (response !== null) {
    return new ApiError({
      code: response.code,
      status,
      step: response.step ?? null,
      details: response.details ?? {},
      retryable: isRetryableStatus(status),
    })
  }

  return new ApiError({
    code: status === null ? 'network_error' : 'invalid_error_response',
    status,
    step: null,
    details: {},
    retryable: status === null || isRetryableStatus(status),
  })
}

function parseApiErrorResponse(value: unknown): ApiErrorResponse | null {
  if (!isRecord(value) || typeof value.code !== 'string') {
    return null
  }

  const code = value.code.trim()

  if (code.length === 0) {
    return null
  }

  const response: ApiErrorResponse = { code }

  if (typeof value.step === 'string' || value.step === null) {
    response.step = value.step
  }

  if (isRecord(value.details)) {
    response.details = value.details
  }

  return response
}

function isRetryableStatus(status: number | null): boolean {
  return status === 408 || status === 429 || status === 502 || status === 503 || status === 504
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}
