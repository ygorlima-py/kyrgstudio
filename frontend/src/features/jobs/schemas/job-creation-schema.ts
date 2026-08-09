import { z } from 'zod'

import {
  createUserProfileSchema,
  userProfileSchema,
  type UserProfileValidationMessages,
} from '@/features/user-profile/schemas/user-profile-schema'

export const pipelineTypeSchema = z.enum([
  'copy_analysis',
  'copy_adaptation',
])

const sourceTypeSchema = z.enum(['video', 'audio'])

export interface JobCreationValidationMessages {
  readonly fileRequired: string
  readonly userProfile: UserProfileValidationMessages
}

function createUploadedFileSchema(message: string) {
  return z.custom<File>(
    (value) => value instanceof File,
    {
      message,
    },
  )
}

const optionalTextSchema = z
  .string()
  .trim()
  .transform((value) => (value.length > 0 ? value : undefined))
  .optional()

const commonJobFields = {
  file: createUploadedFileSchema('Select a video or audio file.'),
  source_type: sourceTypeSchema,
  language: optionalTextSchema,
  need_correction: z.boolean().default(false),
}

export const copyAnalysisJobSchema = z.object({
  ...commonJobFields,
  pipeline_type: z.literal('copy_analysis'),
})

export const copyAdaptationJobSchema = z.object({
  ...commonJobFields,
  pipeline_type: z.literal('copy_adaptation'),
  user_profile: userProfileSchema,
})

/**
 * Selects the correct job contract from the chosen pipeline type.
 *
 * Analysis does not require or return adaptation-only fields.
 */
export const jobCreationSchema = z.discriminatedUnion(
  'pipeline_type',
  [
    copyAnalysisJobSchema,
    copyAdaptationJobSchema,
  ],
)

export function createJobCreationSchema(
  messages: JobCreationValidationMessages,
) {
  const translatedCommonJobFields = {
    file: createUploadedFileSchema(messages.fileRequired),
    source_type: sourceTypeSchema,
    language: optionalTextSchema,
    need_correction: z.boolean().default(false),
  }

  const translatedCopyAnalysisJobSchema = z.object({
    ...translatedCommonJobFields,
    pipeline_type: z.literal('copy_analysis'),
  })

  const translatedCopyAdaptationJobSchema = z.object({
    ...translatedCommonJobFields,
    pipeline_type: z.literal('copy_adaptation'),
    user_profile: createUserProfileSchema(messages.userProfile),
  })

  return z.discriminatedUnion('pipeline_type', [
    translatedCopyAnalysisJobSchema,
    translatedCopyAdaptationJobSchema,
  ])
}

export type PipelineType = z.infer<typeof pipelineTypeSchema>
export type SourceType = z.infer<typeof sourceTypeSchema>

export type CopyAnalysisJobData = z.output<
  typeof copyAnalysisJobSchema
>

export type CopyAdaptationJobData = z.output<
  typeof copyAdaptationJobSchema
>

export type JobCreationFormInput = z.input<
  typeof jobCreationSchema
>

export type JobCreationData = z.output<
  typeof jobCreationSchema
>
