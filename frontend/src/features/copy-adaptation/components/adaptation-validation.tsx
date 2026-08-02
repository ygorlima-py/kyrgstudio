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
  if (validation === null) {
    return <UnavailableValidation />
  }

  const status = validationStatus(validation)

  return (
    <section
      aria-labelledby="adaptation-validation-heading"
      className="overflow-hidden rounded-lg border border-border bg-surface"
    >
      <header className="grid gap-5 border-b border-border px-5 py-6 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-start sm:px-8 sm:py-7">
        <div>
          <p className="font-mono text-meta uppercase tracking-[0.14em] text-action">
            Quality control
          </p>
          <h2
            className="mt-2 font-heading text-heading-3 text-text"
            id="adaptation-validation-heading"
          >
            Production readiness
          </h2>
          <p className="mt-2 max-w-2xl text-body-sm text-text-muted">{status.description}</p>
        </div>

        <Badge variant={status.variant}>{status.label}</Badge>
      </header>

      <dl className="grid grid-cols-2 gap-px border-b border-border bg-border">
        <ValidationMetric label="Blocking issues" value={validation.errors.length} />
        <ValidationMetric label="Warnings" value={validation.warnings.length} />
      </dl>

      {validation.errors.length > 0 ? (
        <ValidationIssueGroup
          heading="Resolve before production"
          issues={validation.errors}
          severity="error"
        />
      ) : null}

      {validation.warnings.length > 0 ? (
        <ValidationIssueGroup
          heading="Review before publishing"
          issues={validation.warnings}
          severity="warning"
        />
      ) : null}

      {validation.errors.length === 0 && validation.warnings.length === 0 ? (
        <p className="px-5 py-7 text-body text-text-muted sm:px-8">
          No blocking errors or review warnings were returned for this script.
        </p>
      ) : null}
    </section>
  )
}

function UnavailableValidation() {
  return (
    <section
      aria-labelledby="adaptation-validation-heading"
      className="rounded-lg border border-border bg-surface px-5 py-6 sm:px-8 sm:py-7"
    >
      <Badge variant="neutral">Not available</Badge>
      <h2 className="mt-3 font-heading text-heading-3 text-text" id="adaptation-validation-heading">
        Production readiness
      </h2>
      <p className="mt-2 max-w-2xl text-body text-text-muted">
        This result does not include a structured validation report. Review the script manually
        before publishing it.
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
  const instruction = issue.customInstruction ?? correctionLabel(issue.correctionAction)

  return (
    <li className="grid gap-4 px-5 py-6 sm:grid-cols-[2.5rem_minmax(0,1fr)] sm:px-8">
      <span className="font-mono text-meta text-text-subtle">
        {String(index + 1).padStart(2, '0')}
      </span>

      <div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={severity === 'error' ? 'danger' : 'warning'}>
            {formatLabel(issue.category)}
          </Badge>
          <span className="font-mono text-meta text-text-subtle">{issue.code}</span>
        </div>

        <p className="mt-3 max-w-3xl text-body text-text">{issue.message}</p>

        <dl className="mt-4 grid gap-x-8 gap-y-3 border-t border-border pt-4 text-body-sm sm:grid-cols-2">
          <ValidationDetail label="Location" value={issueLocation(issue)} />
          <ValidationDetail label="Recommended action" value={instruction} />
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

function validationStatus(validation: NormalizedAdaptationValidation): {
  readonly description: string
  readonly label: string
  readonly variant: 'success' | 'warning' | 'danger'
} {
  if (validation.errors.length > 0) {
    return {
      description: 'Blocking issues were found. Revise these points before using the script.',
      label: 'Needs revision',
      variant: 'danger',
    }
  }

  if (!validation.passed) {
    return {
      description: 'Validation did not pass. Review the returned notes and the complete script.',
      label: 'Manual review',
      variant: 'warning',
    }
  }

  if (validation.warnings.length > 0) {
    return {
      description: 'The script has no blocking errors, but the points below deserve review.',
      label: 'Ready with notes',
      variant: 'warning',
    }
  }

  return {
    description: 'The script passed every structured production-readiness check.',
    label: 'Validation passed',
    variant: 'success',
  }
}

function issueLocation(issue: NormalizedAdaptationValidationIssue): string {
  const locationParts: string[] = []

  if (issue.sectionOrder !== null) {
    locationParts.push(`Section ${issue.sectionOrder}`)
  }

  if (issue.sectionType !== null) {
    locationParts.push(formatLabel(issue.sectionType))
  }

  if (issue.field !== null) {
    locationParts.push(formatLabel(issue.field))
  }

  return locationParts.length > 0 ? locationParts.join(' · ') : 'Entire script'
}

function correctionLabel(value: NormalizedAdaptationValidationIssue['correctionAction']): string {
  const labels: Record<NormalizedAdaptationValidationIssue['correctionAction'], string> = {
    remove: 'Remove the unsupported content',
    soften: 'Soften the claim or wording',
    rewrite: 'Rewrite the affected passage',
    shorten: 'Shorten the affected content',
    expand: 'Add the missing context',
    align_with_profile: 'Align the content with the offer profile',
    custom: 'Apply a manual correction',
  }

  return labels[value]
}

function formatLabel(value: string): string {
  const normalizedValue = value.trim().replaceAll(/[_-]+/g, ' ')
  return normalizedValue.charAt(0).toUpperCase() + normalizedValue.slice(1)
}
