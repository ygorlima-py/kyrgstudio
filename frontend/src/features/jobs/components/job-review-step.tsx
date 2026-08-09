import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { useFormContext } from 'react-hook-form'

import { Button } from '@/shared/ui/button'

import type { JobFormStepId } from '../config/job-form-steps'
import type { JobCreationFormInput } from '../schemas/job-creation-schema'
import { formatFileSize } from '../utils/validate-job-file'

export interface JobReviewStepProps {
  readonly onEditStep: (stepId: JobFormStepId) => void
}

/**
 * Presents the information that will be submitted and allows the user to
 * return directly to a previous step to correct it.
 */
export function JobReviewStep({
  onEditStep,
}: JobReviewStepProps) {
  const { t } = useTranslation()
  const { getValues } = useFormContext<JobCreationFormInput>()
  const values = getValues()
  const selectedFile =
    values.file instanceof File ? values.file : undefined

  return (
    <section
      aria-labelledby="job-review-heading"
      className="space-y-8"
    >
      <div className="space-y-2">
        <h2
          className="font-heading text-heading-md text-text"
          id="job-review-heading"
        >
          {t('newJob.review.title')}
        </h2>

        <p className="max-w-2xl text-body text-text-muted">
          {t('newJob.review.description')}
        </p>
      </div>

      <ReviewSection
        onEdit={() => onEditStep('pipeline')}
        title={t('newJob.review.sections.projectType')}
      >
        <ReviewItem
          label={t('newJob.review.labels.pipeline')}
          value={
            values.pipeline_type === 'copy_adaptation'
              ? t('newJob.review.pipeline.adaptation')
              : t('newJob.review.pipeline.analysis')
          }
        />
      </ReviewSection>

      <ReviewSection
        onEdit={() => onEditStep('file')}
        title={t('newJob.review.sections.referenceFile')}
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <ReviewItem
            label={t('newJob.review.labels.file')}
            value={selectedFile?.name ?? t('newJob.review.empty.file')}
          />

          <ReviewItem
            label={t('newJob.review.labels.size')}
            value={
              selectedFile
                ? formatFileSize(selectedFile.size)
                : t('newJob.review.empty.notAvailable')
            }
          />

          <ReviewItem
            label={t('newJob.review.labels.mediaType')}
            value={
              values.source_type === 'video'
                ? t('newJob.review.media.video')
                : t('newJob.review.media.audio')
            }
          />
        </div>
      </ReviewSection>

      <ReviewSection
        onEdit={() => onEditStep('settings')}
        title={t('newJob.review.sections.transcriptionSettings')}
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <ReviewItem
            label={t('newJob.review.labels.originalLanguage')}
            value={formatReviewLanguage(values.language, t)}
          />

          <ReviewItem
            label={t('newJob.review.labels.transcriptCorrection')}
            value={
              values.need_correction
                ? t('newJob.review.boolean.enabled')
                : t('newJob.review.boolean.disabled')
            }
          />
        </div>
      </ReviewSection>

      {values.pipeline_type === 'copy_adaptation' ? (
        <ReviewSection
          onEdit={() => onEditStep('profile')}
          title={t('newJob.review.sections.offerProfile')}
        >
          <div className="grid gap-5 sm:grid-cols-2">
            <ReviewItem
              label={t('newJob.review.labels.productOrSolution')}
              value={values.user_profile.product_or_solution}
            />

            <ReviewItem
              label={t('newJob.review.labels.targetAudience')}
              value={values.user_profile.target_audience}
            />

            <ReviewItem
              label={t('newJob.review.labels.mainProblem')}
              value={values.user_profile.core_problem}
            />

            <ReviewItem
              label={t('newJob.review.labels.mainPromise')}
              value={values.user_profile.main_promise}
            />

            <ReviewItem
              label={t('newJob.review.labels.platform')}
              value={
                values.user_profile.platform ||
                t('newJob.review.empty.notSpecified')
              }
            />

            <ReviewItem
              label={t('newJob.review.labels.desiredDuration')}
              value={t('newJob.review.durationMinutes', {
                count: values.user_profile.desired_duration,
              })}
            />
          </div>

          <div className="mt-5 grid gap-4 border-t border-border pt-5 sm:grid-cols-4">
            <ReviewItem
              label={t('newJob.review.labels.benefits')}
              value={values.user_profile.benefits?.length ?? 0}
            />

            <ReviewItem
              label={t('newJob.review.labels.objections')}
              value={values.user_profile.objections?.length ?? 0}
            />

            <ReviewItem
              label={t('newJob.review.labels.proofAssets')}
              value={values.user_profile.proof_assets?.length ?? 0}
            />

            <ReviewItem
              label={t('newJob.review.labels.restrictions')}
              value={values.user_profile.restrictions?.length ?? 0}
            />
          </div>
        </ReviewSection>
      ) : null}
    </section>
  )
}

interface ReviewSectionProps {
  readonly title: string
  readonly children: ReactNode
  readonly onEdit: () => void
}

function ReviewSection({
  children,
  onEdit,
  title,
}: ReviewSectionProps) {
  const { t } = useTranslation()

  return (
    <section className="border-t border-border pt-6">
      <div className="mb-5 flex items-center justify-between gap-4">
        <h3 className="font-heading text-heading-sm text-text">
          {title}
        </h3>

        <Button
          onClick={onEdit}
          size="sm"
          type="button"
          variant="ghost"
        >
          {t('newJob.review.edit')}
        </Button>
      </div>

      {children}
    </section>
  )
}

interface ReviewItemProps {
  readonly label: string
  readonly value: ReactNode
}

function ReviewItem({ label, value }: ReviewItemProps) {
  return (
    <div className="space-y-1">
      <dt className="text-meta font-medium uppercase tracking-wide text-text-muted">
        {label}
      </dt>

      <dd className="text-body text-text">{value}</dd>
    </div>
  )
}

function formatReviewLanguage(
  language: string | undefined,
  translate: (key: string) => string,
): string {
  switch (language) {
    case 'pt':
      return translate('newJob.settings.language.options.pt')

    case 'en':
      return translate('newJob.settings.language.options.en')

    case 'es':
      return translate('newJob.settings.language.options.es')

    default:
      return translate('newJob.settings.language.options.auto')
  }
}
