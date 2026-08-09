import { environment } from '@/shared/config/environment'

import type { SourceType } from '../schemas/job-creation-schema'

export type JobFileValidationErrorCode =
  | 'missing_filename'
  | 'empty_file'
  | 'unsupported_media_type'
  | 'file_too_large'

export type JobFileValidationResult =
  | {
      readonly valid: true
      readonly sourceType: SourceType
    }
  | {
      readonly valid: false
      readonly code: JobFileValidationErrorCode
      readonly maxUploadBytes?: number
    }

/**
 * Performs preliminary browser validation before an upload reaches the API.
 */
export function validateJobFile(
  file: File,
): JobFileValidationResult {
  if (!file.name.trim()) {
    return {
      valid: false,
      code: 'missing_filename',
    }
  }

  if (file.size <= 0) {
    return {
      valid: false,
      code: 'empty_file',
    }
  }

  const mediaType = file.type.trim().toLowerCase()

  if (!environment.acceptedMediaTypes.includes(mediaType)) {
    return {
      valid: false,
      code: 'unsupported_media_type',
    }
  }

  if (file.size > environment.maxUploadBytes) {
    return {
      valid: false,
      code: 'file_too_large',
      maxUploadBytes: environment.maxUploadBytes,
    }
  }

  return {
    valid: true,
    sourceType: mediaType.startsWith('video/')
      ? 'video'
      : 'audio',
  }
}

/**
 * Formats a byte count for user-facing file information.
 */
export function formatFileSize(sizeBytes: number): string {
  if (sizeBytes < 1024) {
    return `${sizeBytes} B`
  }

  const units = ['KB', 'MB', 'GB', 'TB']
  let value = sizeBytes / 1024
  let unitIndex = 0

  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024
    unitIndex += 1
  }

  const fractionDigits = value >= 10 ? 0 : 1

  return `${value.toFixed(fractionDigits)} ${units[unitIndex]}`
}
