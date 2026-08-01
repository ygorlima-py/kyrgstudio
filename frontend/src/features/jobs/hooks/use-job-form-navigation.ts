import {
  useCallback,
  useMemo,
  useState,
} from 'react'
import type {
  FieldPath,
  UseFormTrigger,
} from 'react-hook-form'

import {
  getJobFormSteps,
  type JobFormStep,
  type JobFormStepId,
} from '../config/job-form-steps'
import type {
  JobCreationFormInput,
  PipelineType,
} from '../schemas/job-creation-schema'

export interface UseJobFormNavigationOptions {
  readonly pipelineType: PipelineType | undefined
  readonly trigger: UseFormTrigger<JobCreationFormInput>
}

export interface JobFormNavigation {
  readonly currentStep: JobFormStep
  readonly steps: readonly JobFormStep[]
  readonly isFirstStep: boolean
  readonly isLastStep: boolean
  readonly goBack: () => void
  readonly goNext: () => Promise<boolean>
  readonly goToStep: (stepId: JobFormStepId) => void
}

/**
 * Controls wizard navigation and validates only the current step.
 */
export function useJobFormNavigation({
  pipelineType,
  trigger,
}: UseJobFormNavigationOptions): JobFormNavigation {
  const [currentStepId, setCurrentStepId] =
    useState<JobFormStepId>('pipeline')

  const steps = useMemo(
    () => getJobFormSteps(pipelineType),
    [pipelineType],
  )

  const currentStepIndex = Math.max(
    0,
    steps.findIndex((step) => step.id === currentStepId),
  )

  const currentStep = steps[currentStepIndex] ?? steps[0]

  if (currentStep === undefined) {
    throw new Error('Job form must contain at least one step.')
  }

  const goBack = useCallback(() => {
    const previousStep = steps[currentStepIndex - 1]

    if (previousStep !== undefined) {
      setCurrentStepId(previousStep.id)
    }
  }, [currentStepIndex, steps])

  const goNext = useCallback(async (): Promise<boolean> => {
    const fields = [
      ...currentStep.fields,
    ] as FieldPath<JobCreationFormInput>[]

    const isValid =
      fields.length === 0
        ? true
        : await trigger(fields, {
            shouldFocus: true,
          })

    if (!isValid) {
      return false
    }

    const nextStep = steps[currentStepIndex + 1]

    if (nextStep !== undefined) {
      setCurrentStepId(nextStep.id)
    }

    return true
  }, [
    currentStep.fields,
    currentStepIndex,
    steps,
    trigger,
  ])

  const goToStep = useCallback(
    (stepId: JobFormStepId) => {
      if (steps.some((step) => step.id === stepId)) {
        setCurrentStepId(stepId)
      }
    },
    [steps],
  )

  return {
    currentStep,
    steps,
    isFirstStep: currentStepIndex === 0,
    isLastStep: currentStepIndex === steps.length - 1,
    goBack,
    goNext,
    goToStep,
  }
}