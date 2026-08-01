import {
  useEffect,
  type FormEvent,
  type ReactNode,
} from 'react'

import { zodResolver } from '@hookform/resolvers/zod'
import {
  FormProvider,
  useForm,
  useWatch,
  type DefaultValues,
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
import { JobFormProgress } from './job-form-progress'

export interface JobCreationFormProps {
  readonly initialPipelineType?: PipelineType
  readonly onSubmit: (
    formData: JobCreationData,
  ) => Promise<void> | void
  readonly children: (
    navigation: JobFormNavigation,
  ) => ReactNode
}

/**
 * Owns the single React Hook Form instance used throughout job creation.
 */
export function JobCreationForm({
  children,
  initialPipelineType = 'copy_analysis',
  onSubmit,
}: JobCreationFormProps) {
  const form = useForm<
    JobCreationFormInput,
    unknown,
    JobCreationData
  >({
    resolver: zodResolver(jobCreationSchema),
    defaultValues: createDefaultValues(initialPipelineType),
    shouldUnregister: false,
  })

  const pipelineType = useWatch({
    control: form.control,
    name: 'pipeline_type',
  })

  useEffect(() => {
    if (
      pipelineType === 'copy_adaptation' &&
      form.getValues('user_profile') === undefined
    ) {
      form.setValue(
        'user_profile',
        createUserProfileDefaultValues(),
        {
          shouldDirty: false,
          shouldTouch: false,
          shouldValidate: false,
        },
      )
    }
  }, [form, pipelineType])

  const navigation = useJobFormNavigation({
    pipelineType,
    trigger: form.trigger,
  })

  function handleFormSubmit(
    event: FormEvent<HTMLFormElement>,
  ): void {
    if (!navigation.isLastStep) {
      event.preventDefault()
      void navigation.goNext()
      return
    }

    void form.handleSubmit(onSubmit)(event)
  }

  return (
    <FormProvider {...form}>
      <form
        className="space-y-8"
        noValidate
        onSubmit={handleFormSubmit}
      >
        <JobFormProgress
          currentStepId={navigation.currentStep.id}
          steps={navigation.steps}
        />

        <div>{children(navigation)}</div>

        <div className="flex items-center justify-between gap-4 border-t border-border pt-6">
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
            {navigation.isLastStep
              ? 'Submit project'
              : 'Continue'}
          </Button>
        </div>
      </form>
    </FormProvider>
  )
}

function createDefaultValues(
  pipelineType: PipelineType,
): DefaultValues<JobCreationFormInput> {
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
