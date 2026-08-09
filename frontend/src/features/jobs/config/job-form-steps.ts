import type { PipelineType } from '../schemas/job-creation-schema'

export type JobFormStepId =
  | 'pipeline'
  | 'file'
  | 'settings'
  | 'profile'
  | 'review'

export type JobFormField =
  | 'pipeline_type'
  | 'file'
  | 'source_type'
  | 'language'
  | 'need_correction'
  | 'user_profile'

export interface JobFormStep {
  readonly id: JobFormStepId
  readonly labelKey: string
  readonly fields: readonly JobFormField[]
}

const PIPELINE_STEP: JobFormStep = {
  id: 'pipeline',
  labelKey: 'newJob.steps.pipeline',
  fields: ['pipeline_type'],
}

const FILE_STEP: JobFormStep = {
  id: 'file',
  labelKey: 'newJob.steps.file',
  fields: ['file', 'source_type'],
}

const SETTINGS_STEP: JobFormStep = {
  id: 'settings',
  labelKey: 'newJob.steps.settings',
  fields: ['language', 'need_correction'],
}

const PROFILE_STEP: JobFormStep = {
  id: 'profile',
  labelKey: 'newJob.steps.profile',
  fields: ['user_profile'],
}

const REVIEW_STEP: JobFormStep = {
  id: 'review',
  labelKey: 'newJob.steps.review',
  fields: [],
}

/**
 * Returns the visible steps for the selected pipeline.
 */
export function getJobFormSteps(
  pipelineType: PipelineType | undefined,
): readonly JobFormStep[] {
  if (pipelineType === 'copy_adaptation') {
    return [
      PIPELINE_STEP,
      FILE_STEP,
      SETTINGS_STEP,
      PROFILE_STEP,
      REVIEW_STEP,
    ]
  }

  return [
    PIPELINE_STEP,
    FILE_STEP,
    SETTINGS_STEP,
    REVIEW_STEP,
  ]
}