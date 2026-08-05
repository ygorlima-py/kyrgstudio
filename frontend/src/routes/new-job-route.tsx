import { useSearchParams } from 'react-router'

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

  if (session.status !== 'authenticated') {
    return null
  }

  return (
    <div className="mx-auto w-full max-w-5xl space-y-8">
      <header className="space-y-2">
        <p className="text-meta font-medium uppercase tracking-wide text-action">
          New project
        </p>

        <h1 className="font-heading text-heading-lg text-text">
          Analyze or adapt a reference
        </h1>

        <p className="max-w-2xl text-body text-text-muted">
          Configure the project, upload your reference, and review everything
          before processing begins.
        </p>
      </header>

      <JobCreationForm
        draftOwnerId={session.user.user_id}
        initialPipelineType={
            initialPipelineType ?? 'copy_analysis'
        }               
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
            Cancel upload
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
          Describe your offer
        </h2>

        <p className="max-w-2xl text-body text-text-muted">
          Provide accurate information so the adapted script remains grounded
          in your real product, audience, and available evidence.
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
              Try again
            </Button>
          ) : null}

          <Button
            onClick={onDismiss}
            type="button"
            variant="ghost"
          >
            Review project
          </Button>
        </>
      }
      description={message.description}
      title={message.title}
    />
  )
}

interface SubmissionErrorMessage {
  readonly title: string
  readonly description: string
}

function getSubmissionErrorMessage(
  errorCode: string,
): SubmissionErrorMessage {
  switch (errorCode) {
    case 'upload_too_large':
      return {
        title: 'File is too large',
        description:
          'Select a smaller file before trying again.',
      }

    case 'unsupported_media_type':
      return {
        title: 'File type is not supported',
        description:
          'Select one of the supported video or audio formats.',
      }

    case 'invalid_input':
      return {
        title: 'Review the project information',
        description:
          'Some submitted information is missing or invalid.',
      }

    case 'network_error':
      return {
        title: 'Connection interrupted',
        description:
          'Check your connection and try sending the project again.',
      }

    case 'authentication_required':
    case 'invalid_token':
    case 'refresh_token_invalid':
      return {
        title: 'Your session expired',
        description:
          'Sign in again before submitting this project.',
      }

    case 'storage_error':
    case 'store_error':
    case 'job_store_error':
      return {
        title: 'Service temporarily unavailable',
        description:
          'The project could not be saved right now. Try again shortly.',
      }

    default:
      return {
        title: 'Project could not be submitted',
        description:
          'Review the information or try again in a few moments.',
      }
  }
}
