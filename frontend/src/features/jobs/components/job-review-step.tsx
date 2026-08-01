import type { ReactNode } from 'react'
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
          Review your project
        </h2>

        <p className="max-w-2xl text-body text-text-muted">
          Confirm the information below before submitting the file for
          processing.
        </p>
      </div>

      <ReviewSection
        onEdit={() => onEditStep('pipeline')}
        title="Project type"
      >
        <ReviewItem
          label="Pipeline"
          value={
            values.pipeline_type === 'copy_adaptation'
              ? 'Copy adaptation'
              : 'Copy analysis'
          }
        />
      </ReviewSection>

      <ReviewSection
        onEdit={() => onEditStep('file')}
        title="Reference file"
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <ReviewItem
            label="File"
            value={selectedFile?.name ?? 'No file selected'}
          />

          <ReviewItem
            label="Size"
            value={
              selectedFile
                ? formatFileSize(selectedFile.size)
                : 'Not available'
            }
          />

          <ReviewItem
            label="Media type"
            value={
              values.source_type === 'video'
                ? 'Video'
                : 'Audio'
            }
          />
        </div>
      </ReviewSection>

      <ReviewSection
        onEdit={() => onEditStep('settings')}
        title="Transcription settings"
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <ReviewItem
            label="Original language"
            value={values.language || 'Detect automatically'}
          />

          <ReviewItem
            label="Transcript correction"
            value={values.need_correction ? 'Enabled' : 'Disabled'}
          />
        </div>
      </ReviewSection>

      {values.pipeline_type === 'copy_adaptation' ? (
        <ReviewSection
          onEdit={() => onEditStep('profile')}
          title="Offer profile"
        >
          <div className="grid gap-5 sm:grid-cols-2">
            <ReviewItem
              label="Product or solution"
              value={values.user_profile.product_or_solution}
            />

            <ReviewItem
              label="Target audience"
              value={values.user_profile.target_audience}
            />

            <ReviewItem
              label="Main problem"
              value={values.user_profile.core_problem}
            />

            <ReviewItem
              label="Main promise"
              value={values.user_profile.main_promise}
            />

            <ReviewItem
              label="Platform"
              value={values.user_profile.platform || 'Not specified'}
            />

            <ReviewItem
              label="Desired duration"
              value={`${values.user_profile.desired_duration} minute(s)`}
            />
          </div>

          <div className="mt-5 grid gap-4 border-t border-border pt-5 sm:grid-cols-4">
            <ReviewItem
              label="Benefits"
              value={values.user_profile.benefits?.length ?? 0}
            />

            <ReviewItem
              label="Objections"
              value={values.user_profile.objections?.length ?? 0}
            />

            <ReviewItem
              label="Proof assets"
              value={values.user_profile.proof_assets?.length ?? 0}
            />

            <ReviewItem
              label="Restrictions"
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
          Edit
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