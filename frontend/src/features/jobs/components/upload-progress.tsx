import { useTranslation } from 'react-i18next'

import type { UploadProgress as UploadProgressData } from '@/shared/api'
import { Progress } from '@/shared/ui/progress'

export interface UploadProgressProps {
  readonly progress: UploadProgressData
}

/**
 * Displays the number of transferred bytes and the upload percentage when the
 * browser knows the complete request size.
 */
export function UploadProgress({
  progress,
}: UploadProgressProps) {
  const { t } = useTranslation()
  const percentage = progress.percentage ?? 0

  return (
    <div
      aria-live="polite"
      className="space-y-3"
    >
      <div className="flex items-center justify-between gap-4 text-body-sm">
        <span className="font-medium text-text">
          {t('newJob.uploadProgress.title')}
        </span>

        <span className="text-text-muted">
          {progress.percentage === null
            ? formatFileSize(progress.loadedBytes)
            : `${progress.percentage}%`}
        </span>
      </div>

      <Progress
        label={t('newJob.uploadProgress.label')}
        value={percentage}
      />
    </div>
  )
}

function formatFileSize(sizeBytes: number): string {
  if (sizeBytes < 1024) {
    return `${sizeBytes} B`
  }

  const units = ['KB', 'MB', 'GB']
  let value = sizeBytes / 1024
  let unitIndex = 0

  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024
    unitIndex += 1
  }

  return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[unitIndex]}`
}
