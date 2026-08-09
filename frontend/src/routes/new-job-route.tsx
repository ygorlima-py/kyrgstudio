import { useSearchParams } from 'react-router'
import { useTranslation } from 'react-i18next'

import { useAuth } from '@/features/auth'
import {
  FileUploadStep,
  getInitialPipelineType,
  JobCreationForm,
  JobReviewStep,
  JobSettingsStep,
  JobTypeStep,
  UploadProgress,
  useJobSubmission,
} from '@/features/jobs'
import {
  AudienceProblemFields,
  BenefitsFields,
  CallToActionFields,
  DesirePromiseFields,
  MechanismFields,
  ObjectionsFields,
  OfferTermsFields,
  PlatformDurationFields,
  ProductOfferFields,
  ProofAssetsFields,
  RestrictionsFields,
  ToneLanguageFields,
} from '@/features/user-profile'
import { Button } from '@/shared/ui/button'

import type { ApiError } from '@/shared/api'
import { ErrorState } from '@/shared/components/states'

/**
 * Owns the complete job creation flow while keeping each form step isolated.
 */
export function NewJobRoute() {
  const session = useAuth()
  const [searchParams] = useSearchParams()
  const initialPipelineType = getInitialPipelineType(searchParams)
  const submission = useJobSubmission()
  const { t } = useTranslation()
  
  if (session.status !== 'authenticated') {
    return null
  }

  return (
    <div className="mx-auto w-full max-w-5xl space-y-8">
      <header className="space-y-2">
        <p className="text-meta font-medium uppercase tracking-wide text-action">
          {t('newJob.page.eyebrow')}
        </p>

        <h1 className="font-heading text-heading-lg text-text">
          {t('newJob.page.title')}
        </h1>

        <p className="max-w-2xl text-body text-text-muted">
          {t('newJob.page.description')}
        </p>
      </header>

      <JobCreationForm
        draftOwnerId={session.user.user_id}
        initialPipelineType={
            initialPipelineType ?? 'copy_analysis'
        }               
        initialStepId={initialPipelineType === undefined ? 'pipeline' : 'file'}
        onSubmit={submission.submit}
      >
        {(navigation) => {
          switch (navigation.currentStep.id) {
            case 'pipeline':
              return <JobTypeStep />

            case 'file':
              return <FileUploadStep />

            case 'settings':
              return <JobSettingsStep />

            case 'profile':
              return <UserProfileStep />

            case 'review':
              return (
                <JobReviewStep
                  onEditStep={navigation.goToStep}
                />
              )
          }
        }}
      </JobCreationForm>

      {submission.isSubmitting && submission.progress ? (
        <div className="space-y-4 border-t border-border pt-6">
          <UploadProgress progress={submission.progress} />

          <Button
            onClick={submission.cancel}
            size="sm"
            type="button"
            variant="ghost"
          >
            {t('newJob.submission.cancelUpload')}
          </Button>
        </div>
      ) : null}

      {submission.error ? (
        <JobSubmissionError
            canRetry={submission.canRetry}
            error={submission.error}
            onDismiss={submission.clearError}
            onRetry={submission.retry}
        />
        ) : null}
    </div>
  )
}

/**
 * Composes the independent offer-profile groups used only by adaptation jobs.
 */
function UserProfileStep() {
  const { t } = useTranslation()

  return (
    <section
      aria-labelledby="user-profile-heading"
      className="space-y-8"
    >
      <div className="space-y-2">
        <h2
          className="font-heading text-heading-md text-text"
          id="user-profile-heading"
        >
          {t('newJob.profile.title')}
        </h2>

        <p className="max-w-2xl text-body text-text-muted">
          {t('newJob.profile.description')}
        </p>
      </div>

      <ProductOfferFields />
      <AudienceProblemFields />
      <DesirePromiseFields />
      <MechanismFields />
      <BenefitsFields />
      <ObjectionsFields />
      <ProofAssetsFields />
      <OfferTermsFields />
      <CallToActionFields />
      <ToneLanguageFields />
      <PlatformDurationFields />
      <RestrictionsFields />
    </section>
  )
}

interface JobSubmissionErrorProps {
  readonly error: ApiError
  readonly canRetry: boolean
  readonly onRetry: () => Promise<void>
  readonly onDismiss: () => void
}

function JobSubmissionError({
  canRetry,
  error,
  onDismiss,
  onRetry,
}: JobSubmissionErrorProps) {
  const { t } = useTranslation()
  const message = getSubmissionErrorMessage(error.code)

  return (
    <ErrorState
      action={
        <>
          {canRetry ? (
            <Button
              onClick={() => {
                void onRetry()
              }}
              type="button"
            >
              {t('newJob.submission.actions.retry')}
            </Button>
          ) : null}

          <Button
            onClick={onDismiss}
            type="button"
            variant="ghost"
          >
            {t('newJob.submission.actions.review')}
          </Button>
        </>
      }
      description={t(message.descriptionKey)}
      title={t(message.titleKey)}
    />
  )
}

interface SubmissionErrorMessage {
  readonly titleKey: string
  readonly descriptionKey: string
}

function getSubmissionErrorMessage(
  errorCode: string,
): SubmissionErrorMessage {
  switch (errorCode) {
    case 'upload_too_large':
      return {
        titleKey: 'newJob.submission.errors.uploadTooLarge.title',
        descriptionKey: 'newJob.submission.errors.uploadTooLarge.description',
      }

    case 'unsupported_media_type':
      return {
        titleKey: 'newJob.submission.errors.unsupportedMediaType.title',
        descriptionKey: 'newJob.submission.errors.unsupportedMediaType.description',
      }

    case 'invalid_input':
      return {
        titleKey: 'newJob.submission.errors.invalidInput.title',
        descriptionKey: 'newJob.submission.errors.invalidInput.description',
      }

    case 'network_error':
      return {
        titleKey: 'newJob.submission.errors.network.title',
        descriptionKey: 'newJob.submission.errors.network.description',
      }

    case 'authentication_required':
    case 'invalid_token':
    case 'refresh_token_invalid':
      return {
        titleKey: 'newJob.submission.errors.sessionExpired.title',
        descriptionKey: 'newJob.submission.errors.sessionExpired.description',
      }

    case 'storage_error':
    case 'store_error':
    case 'job_store_error':
      return {
        titleKey: 'newJob.submission.errors.serviceUnavailable.title',
        descriptionKey: 'newJob.submission.errors.serviceUnavailable.description',
      }

    default:
      return {
        titleKey: 'newJob.submission.errors.default.title',
        descriptionKey: 'newJob.submission.errors.default.description',
      }
  }
}
