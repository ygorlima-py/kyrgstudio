import { useEffect, useState, type FormEvent, type ReactNode } from 'react'

import { zodResolver } from '@hookform/resolvers/zod'
import {
  FormProvider,
  useForm,
  useWatch,
  type DefaultValues,
  type FieldErrors,
} from 'react-hook-form'

import { Button } from '@/shared/ui/button'

import type { JobFormNavigation } from '../hooks/use-job-form-navigation'
import { useJobFormNavigation } from '../hooks/use-job-form-navigation'
import {
  jobCreationSchema,
  type JobCreationData,
  type JobCreationFormInput,
  type PipelineType,
} from '../schemas/job-creation-schema'
import {
  clearJobFormDraft,
  loadJobFormDraft,
  saveJobFormDraft,
  type JobFormDraft,
  type JobFormDraftValues,
} from '../utils/job-form-draft'
import { JobFormProgress } from './job-form-progress'

export interface JobCreationFormProps {
  readonly draftOwnerId: number
  readonly initialPipelineType?: PipelineType
  readonly onSubmit: (formData: JobCreationData) => Promise<void> | void
  readonly children: (navigation: JobFormNavigation) => ReactNode
}

/**
 * Owns the single React Hook Form instance used throughout job creation.
 */
export function JobCreationForm({
  children,
  draftOwnerId,
  initialPipelineType = 'copy_analysis',
  onSubmit,
}: JobCreationFormProps) {
  const [initialDraft] = useState<JobFormDraft | null>(() => loadJobFormDraft(draftOwnerId))
  const [draftMessage, setDraftMessage] = useState<string | null>(
    initialDraft === null ? null : 'Draft restored. Select the media file again before submitting.',
  )

  const form = useForm<JobCreationFormInput, unknown, JobCreationData>({
    resolver: zodResolver(jobCreationSchema),
    defaultValues: createInitialValues(initialPipelineType, initialDraft),
    shouldUnregister: false,
  })

  const pipelineType = useWatch({
    control: form.control,
    name: 'pipeline_type',
  })

  useEffect(() => {
    if (pipelineType === 'copy_adaptation' && form.getValues('user_profile') === undefined) {
      form.setValue('user_profile', createUserProfileDefaultValues(), {
        shouldDirty: false,
        shouldTouch: false,
        shouldValidate: false,
      })
    }
  }, [form, pipelineType])

  const navigation = useJobFormNavigation({
    ...(initialDraft === null ? {} : { initialStepId: initialDraft.currentStepId }),
    pipelineType,
    trigger: form.trigger,
  })

  function handleSaveDraft(): void {
    const { file, ...serializableValues } = form.getValues()
    void file

    const wasSaved = saveJobFormDraft(
      draftOwnerId,
      serializableValues as JobFormDraftValues,
      navigation.currentStep.id,
    )

    setDraftMessage(
      wasSaved ? 'Draft saved on this device.' : 'The draft could not be saved in this browser.',
    )
  }

  function handleClearForm(): void {
    const shouldClear = window.confirm('Clear every field and delete the saved draft?')

    if (!shouldClear) {
      return
    }

    clearJobFormDraft(draftOwnerId)
    form.reset(createDefaultValues(initialPipelineType))
    navigation.goToStep('pipeline')
    setDraftMessage('Form and saved draft cleared.')
  }

  async function submitAndClearDraft(formData: JobCreationData): Promise<void> {
    await onSubmit(formData)
    clearJobFormDraft(draftOwnerId)
  }

  function showStepWithInvalidFields(errors: FieldErrors<JobCreationFormInput>): void {
    if (errors.pipeline_type !== undefined) {
      navigation.goToStep('pipeline')
      return
    }

    if (errors.file !== undefined || errors.source_type !== undefined) {
      navigation.goToStep('file')
      return
    }

    if (errors.language !== undefined || errors.need_correction !== undefined) {
      navigation.goToStep('settings')
      return
    }

    if ('user_profile' in errors && errors.user_profile !== undefined) {
      navigation.goToStep('profile')
    }
  }

  function handleFormSubmit(event: FormEvent<HTMLFormElement>): void {
    if (!navigation.isLastStep) {
      event.preventDefault()
      void navigation.goNext()
      return
    }

    void form.handleSubmit(submitAndClearDraft, showStepWithInvalidFields)(event)
  }

  return (
    <FormProvider {...form}>
      <form className="space-y-8" noValidate onSubmit={handleFormSubmit}>
        <JobFormProgress currentStepId={navigation.currentStep.id} steps={navigation.steps} />

        <div>{children(navigation)}</div>

        <div className="flex flex-col gap-3 border-t border-border pt-6 sm:flex-row sm:items-center sm:justify-between">
          <p aria-live="polite" className="text-body-sm text-text-muted" role="status">
            {draftMessage ?? 'Save a draft manually to continue later on this device.'}
          </p>

          <div className="flex flex-wrap gap-2">
            <Button
              disabled={form.formState.isSubmitting}
              onClick={handleSaveDraft}
              type="button"
              variant="secondary"
            >
              Save draft
            </Button>

            <Button
              disabled={form.formState.isSubmitting}
              onClick={handleClearForm}
              type="button"
              variant="ghost"
            >
              Clear form
            </Button>
          </div>
        </div>

        <div className="flex items-center justify-between gap-4">
          <div>
            {!navigation.isFirstStep ? (
              <Button
                disabled={form.formState.isSubmitting}
                onClick={navigation.goBack}
                type="button"
                variant="ghost"
              >
                Back
              </Button>
            ) : null}
          </div>

          <Button
            isLoading={form.formState.isSubmitting}
            loadingContent="Submitting..."
            type="submit"
          >
            {navigation.isLastStep ? 'Submit project' : 'Continue'}
          </Button>
        </div>
      </form>
    </FormProvider>
  )
}

function createDefaultValues(pipelineType: PipelineType): DefaultValues<JobCreationFormInput> {
  const commonValues = {
    pipeline_type: pipelineType,
    language: '',
    need_correction: false,
  }

  if (pipelineType === 'copy_adaptation') {
    return {
      ...commonValues,
      pipeline_type: 'copy_adaptation',
      user_profile: createUserProfileDefaultValues(),
    }
  }

  return {
    ...commonValues,
    pipeline_type: 'copy_analysis',
  }
}

function createInitialValues(
  initialPipelineType: PipelineType,
  draft: JobFormDraft | null,
): DefaultValues<JobCreationFormInput> {
  if (draft === null) {
    return createDefaultValues(initialPipelineType)
  }

  const commonDraftValues = {
    language: draft.values.language ?? '',
    need_correction: draft.values.need_correction ?? false,
    ...(draft.values.source_type === undefined ? {} : { source_type: draft.values.source_type }),
  }

  if (draft.values.pipeline_type === 'copy_adaptation') {
    return {
      ...commonDraftValues,
      pipeline_type: 'copy_adaptation',
      user_profile: restoreUserProfile(draft.values.user_profile),
    }
  }

  return {
    ...commonDraftValues,
    pipeline_type: 'copy_analysis',
  }
}

function restoreUserProfile(draft: JobFormDraftValues['user_profile']) {
  const defaults = createUserProfileDefaultValues()

  return {
    product_or_solution: draft?.product_or_solution ?? defaults.product_or_solution,
    target_audience: draft?.target_audience ?? defaults.target_audience,
    core_problem: draft?.core_problem ?? defaults.core_problem,
    core_desire: draft?.core_desire ?? defaults.core_desire,
    main_promise: draft?.main_promise ?? defaults.main_promise,
    unique_mechanism: draft?.unique_mechanism ?? defaults.unique_mechanism,
    benefits: draft?.benefits ?? defaults.benefits,
    objections: draft?.objections ?? defaults.objections,
    proof_assets: draft?.proof_assets ?? defaults.proof_assets,
    offer_details: draft?.offer_details ?? defaults.offer_details,
    call_to_action: draft?.call_to_action ?? defaults.call_to_action,
    tone: draft?.tone ?? defaults.tone,
    target_language: draft?.target_language ?? defaults.target_language,
    platform: draft?.platform ?? defaults.platform,
    desired_duration: draft?.desired_duration ?? defaults.desired_duration,
    restrictions: draft?.restrictions ?? defaults.restrictions,
  }
}

function createUserProfileDefaultValues() {
  return {
    product_or_solution: '',
    target_audience: '',
    core_problem: '',
    core_desire: '',
    main_promise: '',
    unique_mechanism: '',
    benefits: [],
    objections: [],
    proof_assets: [],
    offer_details: '',
    call_to_action: '',
    tone: '',
    target_language: '',
    platform: '',
    desired_duration: 1,
    restrictions: [],
  }
}
