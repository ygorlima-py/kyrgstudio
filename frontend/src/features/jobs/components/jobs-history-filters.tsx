import { useRef, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { Label } from '@/shared/ui/label'
import { Select } from '@/shared/ui/select'

import type { JobListPipelineType, JobListStatus } from '../api/jobs-api'

const ALL_FILTERS_VALUE = 'all'

export interface JobsHistoryFiltersProps {
  readonly hasActiveFilters: boolean
  readonly jobId: number | undefined
  readonly pipelineType: JobListPipelineType | undefined
  readonly status: JobListStatus | undefined
  readonly onClear: () => void
  readonly onJobIdChange: (jobId: number | undefined) => void
  readonly onPipelineTypeChange: (pipelineType: JobListPipelineType | undefined) => void
  readonly onStatusChange: (status: JobListStatus | undefined) => void
}

/** Search and filter controls for the authenticated project history. */
export function JobsHistoryFilters({
  hasActiveFilters,
  jobId,
  onClear,
  onJobIdChange,
  onPipelineTypeChange,
  onStatusChange,
  pipelineType,
  status,
}: JobsHistoryFiltersProps) {
  const { t } = useTranslation()
  const jobIdInputRef = useRef<HTMLInputElement>(null)
  const statusOptions = [
    { value: ALL_FILTERS_VALUE, label: t('jobs.history.filters.allStatuses') },
    { value: 'pending', label: t('jobs.history.status.preparing') },
    { value: 'uploaded', label: t('jobs.history.status.queued') },
    { value: 'running', label: t('jobs.history.status.processing') },
    { value: 'completed', label: t('jobs.history.status.completed') },
    { value: 'failed', label: t('jobs.history.status.failed') },
  ] as const
  const pipelineOptions = [
    { value: ALL_FILTERS_VALUE, label: t('jobs.history.filters.allProjectTypes') },
    { value: 'copy_analysis', label: t('jobs.pipeline.analysis') },
    { value: 'copy_adaptation', label: t('jobs.pipeline.adaptation') },
  ] as const

  function handleSearch(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()

    const normalizedValue = jobIdInputRef.current?.value.trim() ?? ''
    onJobIdChange(normalizedValue === '' ? undefined : Number(normalizedValue))
  }

  function handleClear(): void {
    if (jobIdInputRef.current !== null) {
      jobIdInputRef.current.value = ''
    }

    onClear()
  }

  return (
    <section aria-labelledby="history-filters-heading" className="border-b border-border pb-7">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-body font-semibold text-text" id="history-filters-heading">
            {t('jobs.history.filters.title')}
          </h2>
          <p className="mt-1 text-body-sm text-text-muted">
            {t('jobs.history.filters.description')}
          </p>
        </div>

        <Button
          disabled={!hasActiveFilters}
          onClick={handleClear}
          size="sm"
          type="button"
          variant="ghost"
        >
          {t('jobs.history.filters.clear')}
        </Button>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-[minmax(16rem,1.35fr)_minmax(12rem,0.8fr)_minmax(12rem,0.8fr)] lg:items-end">
        <form className="flex items-end gap-2" onSubmit={handleSearch}>
          <div className="min-w-0 flex-1">
            <Label htmlFor="history-job-id">{t('jobs.history.filters.projectNumber')}</Label>
            <Input
              className="mt-2"
              defaultValue={jobId === undefined ? '' : String(jobId)}
              id="history-job-id"
              inputMode="numeric"
              key={jobId ?? 'all-projects'}
              min={1}
              placeholder={t('jobs.history.filters.projectNumberPlaceholder')}
              ref={jobIdInputRef}
              step={1}
              type="number"
            />
          </div>
          <Button className="shrink-0" type="submit" variant="secondary">
            {t('jobs.history.filters.search')}
          </Button>
        </form>

        <div>
          <Label id="history-status-label">{t('jobs.history.filters.status')}</Label>
          <Select
            aria-labelledby="history-status-label"
            className="mt-2"
            onValueChange={(value) => onStatusChange(readStatusValue(value))}
            options={statusOptions}
            value={status ?? ALL_FILTERS_VALUE}
          />
        </div>

        <div>
          <Label id="history-pipeline-label">{t('jobs.history.filters.projectType')}</Label>
          <Select
            aria-labelledby="history-pipeline-label"
            className="mt-2"
            onValueChange={(value) => onPipelineTypeChange(readPipelineValue(value))}
            options={pipelineOptions}
            value={pipelineType ?? ALL_FILTERS_VALUE}
          />
        </div>
      </div>
    </section>
  )
}

function readStatusValue(value: string): JobListStatus | undefined {
  switch (value) {
    case 'pending':
    case 'uploaded':
    case 'running':
    case 'completed':
    case 'failed':
      return value
    default:
      return undefined
  }
}

function readPipelineValue(value: string): JobListPipelineType | undefined {
  switch (value) {
    case 'copy_analysis':
    case 'copy_adaptation':
      return value
    default:
      return undefined
  }
}
