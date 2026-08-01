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
  readonly label: string
  readonly fields: readonly JobFormField[]
}

const PIPELINE_STEP: JobFormStep = {
  id: 'pipeline',
  label: 'Project type',
  fields: ['pipeline_type'],
}

const FILE_STEP: JobFormStep = {
  id: 'file',
  label: 'Reference',
  fields: ['file', 'source_type'],
}

const SETTINGS_STEP: JobFormStep = {
  id: 'settings',
  label: 'Settings',
  fields: ['language', 'need_correction'],
}

const PROFILE_STEP: JobFormStep = {
  id: 'profile',
  label: 'Offer profile',
  fields: ['user_profile'],
}

const REVIEW_STEP: JobFormStep = {
  id: 'review',
  label: 'Review',
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