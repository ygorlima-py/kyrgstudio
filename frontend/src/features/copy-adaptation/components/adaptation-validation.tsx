import type { TFunction } from 'i18next'
import { useTranslation } from 'react-i18next'

import { Badge } from '@/shared/ui/badge'

import type {
  NormalizedAdaptationValidation,
  NormalizedAdaptationValidationIssue,
} from '../utils/normalize-adaptation-result'

export interface AdaptationValidationProps {
  readonly validation: NormalizedAdaptationValidation | null
}

/** Present production-readiness checks without exposing raw validation data. */
export function AdaptationValidation({ validation }: AdaptationValidationProps) {
  const { t } = useTranslation()

  if (validation === null) {
    return <UnavailableValidation />
  }

  const status = validationStatus(validation, t)

  return (
    <section
      aria-labelledby="adaptation-validation-heading"
      className="overflow-hidden rounded-lg border border-border bg-surface"
    >
      <header className="grid gap-5 border-b border-border px-5 py-6 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-start sm:px-8 sm:py-7">
        <div>
          <p className="font-mono text-meta uppercase tracking-[0.14em] text-action">
            {t('adaptationResult.validation.eyebrow')}
          </p>
          <h2
            className="mt-2 font-heading text-heading-3 text-text"
            id="adaptation-validation-heading"
          >
            {t('adaptationResult.validation.title')}
          </h2>
          <p className="mt-2 max-w-2xl text-body-sm text-text-muted">{status.description}</p>
        </div>

        <Badge variant={status.variant}>{status.label}</Badge>
      </header>

      <dl className="grid grid-cols-2 gap-px border-b border-border bg-border">
        <ValidationMetric
          label={t('adaptationResult.validation.blockingIssues')}
          value={validation.errors.length}
        />
        <ValidationMetric
          label={t('adaptationResult.validation.warnings')}
          value={validation.warnings.length}
        />
      </dl>

      {validation.errors.length > 0 ? (
        <ValidationIssueGroup
          heading={t('adaptationResult.validation.resolveBeforeProduction')}
          issues={validation.errors}
          severity="error"
        />
      ) : null}

      {validation.warnings.length > 0 ? (
        <ValidationIssueGroup
          heading={t('adaptationResult.validation.reviewBeforePublishing')}
          issues={validation.warnings}
          severity="warning"
        />
      ) : null}

      {validation.errors.length === 0 && validation.warnings.length === 0 ? (
        <p className="px-5 py-7 text-body text-text-muted sm:px-8">
          {t('adaptationResult.validation.noIssues')}
        </p>
      ) : null}
    </section>
  )
}

function UnavailableValidation() {
  const { t } = useTranslation()

  return (
    <section
      aria-labelledby="adaptation-validation-heading"
      className="rounded-lg border border-border bg-surface px-5 py-6 sm:px-8 sm:py-7"
    >
      <Badge variant="neutral">{t('adaptationResult.validation.notAvailable')}</Badge>
      <h2 className="mt-3 font-heading text-heading-3 text-text" id="adaptation-validation-heading">
        {t('adaptationResult.validation.title')}
      </h2>
      <p className="mt-2 max-w-2xl text-body text-text-muted">
        {t('adaptationResult.validation.unavailableDescription')}
      </p>
    </section>
  )
}

interface ValidationMetricProps {
  readonly label: string
  readonly value: number
}

function ValidationMetric({ label, value }: ValidationMetricProps) {
  return (
    <div className="bg-surface px-5 py-4 sm:px-8">
      <dt className="font-mono text-meta uppercase tracking-[0.08em] text-text-subtle">{label}</dt>
      <dd className="mt-1 text-body-lg font-semibold text-text">{value}</dd>
    </div>
  )
}

interface ValidationIssueGroupProps {
  readonly heading: string
  readonly issues: readonly NormalizedAdaptationValidationIssue[]
  readonly severity: 'error' | 'warning'
}

function ValidationIssueGroup({ heading, issues, severity }: ValidationIssueGroupProps) {
  return (
    <div className="border-b border-border last:border-b-0">
      <h3 className="px-5 pt-6 text-label text-text sm:px-8">{heading}</h3>
      <ol className="divide-y divide-border">
        {issues.map((issue, index) => (
          <ValidationIssue
            index={index}
            issue={issue}
            key={`${severity}-${issue.code}-${issue.sectionOrder ?? 'all'}-${index}`}
            severity={severity}
          />
        ))}
      </ol>
    </div>
  )
}

interface ValidationIssueProps {
  readonly index: number
  readonly issue: NormalizedAdaptationValidationIssue
  readonly severity: 'error' | 'warning'
}

function ValidationIssue({ index, issue, severity }: ValidationIssueProps) {
  const { t } = useTranslation()
  const instruction = issue.customInstruction ?? correctionLabel(issue.correctionAction, t)

  return (
    <li className="grid gap-4 px-5 py-6 sm:grid-cols-[2.5rem_minmax(0,1fr)] sm:px-8">
      <span className="font-mono text-meta text-text-subtle">
        {String(index + 1).padStart(2, '0')}
      </span>

      <div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={severity === 'error' ? 'danger' : 'warning'}>
            {formatValidationCategory(issue.category, t)}
          </Badge>
          <span className="font-mono text-meta text-text-subtle">{issue.code}</span>
        </div>

        <p className="mt-3 max-w-3xl text-body text-text">{issue.message}</p>

        <dl className="mt-4 grid gap-x-8 gap-y-3 border-t border-border pt-4 text-body-sm sm:grid-cols-2">
          <ValidationDetail
            label={t('adaptationResult.validation.location')}
            value={issueLocation(issue, t)}
          />
          <ValidationDetail
            label={t('adaptationResult.validation.recommendedAction')}
            value={instruction}
          />
        </dl>
      </div>
    </li>
  )
}

interface ValidationDetailProps {
  readonly label: string
  readonly value: string
}

function ValidationDetail({ label, value }: ValidationDetailProps) {
  return (
    <div>
      <dt className="font-mono text-meta uppercase tracking-[0.08em] text-text-subtle">{label}</dt>
      <dd className="mt-1 text-body-sm text-text-muted">{value}</dd>
    </div>
  )
}

function validationStatus(
  validation: NormalizedAdaptationValidation,
  t: TFunction,
): {
  readonly description: string
  readonly label: string
  readonly variant: 'success' | 'warning' | 'danger'
} {
  if (validation.errors.length > 0) {
    return {
      description: t('adaptationResult.validation.status.needsRevisionDescription'),
      label: t('adaptationResult.validation.status.needsRevision'),
      variant: 'danger',
    }
  }

  if (!validation.passed) {
    return {
      description: t('adaptationResult.validation.status.manualReviewDescription'),
      label: t('adaptationResult.validation.status.manualReview'),
      variant: 'warning',
    }
  }

  if (validation.warnings.length > 0) {
    return {
      description: t('adaptationResult.validation.status.readyWithNotesDescription'),
      label: t('adaptationResult.validation.status.readyWithNotes'),
      variant: 'warning',
    }
  }

  return {
    description: t('adaptationResult.validation.status.validationPassedDescription'),
    label: t('adaptationResult.validation.status.validationPassed'),
    variant: 'success',
  }
}

function issueLocation(issue: NormalizedAdaptationValidationIssue, t: TFunction): string {
  const locationParts: string[] = []

  if (issue.sectionOrder !== null) {
    locationParts.push(
      t('adaptationResult.validation.sectionNumber', { order: issue.sectionOrder }),
    )
  }

  if (issue.sectionType !== null) {
    locationParts.push(t(`analysisResult.sections.${issue.sectionType}`))
  }

  if (issue.field !== null) {
    locationParts.push(formatLabel(issue.field))
  }

  return locationParts.length > 0
    ? locationParts.join(' · ')
    : t('adaptationResult.validation.entireScript')
}

function correctionLabel(
  value: NormalizedAdaptationValidationIssue['correctionAction'],
  t: TFunction,
): string {
  return t(`adaptationResult.validation.correctionActions.${value}`)
}

function formatValidationCategory(
  value: NormalizedAdaptationValidationIssue['category'],
  t: TFunction,
): string {
  return t(`adaptationResult.validation.categories.${value}`)
}

function formatLabel(value: string): string {
  const normalizedValue = value.trim().replaceAll(/[_-]+/g, ' ')
  return normalizedValue.charAt(0).toUpperCase() + normalizedValue.slice(1)
}
