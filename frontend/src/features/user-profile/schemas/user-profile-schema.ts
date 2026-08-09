import { z } from 'zod'

export interface UserProfileValidationMessages {
  readonly listItemRequired: string
  readonly productOrSolutionRequired: string
  readonly targetAudienceRequired: string
  readonly coreProblemRequired: string
  readonly coreDesireRequired: string
  readonly mainPromiseRequired: string
  readonly callToActionRequired: string
  readonly desiredDurationPositive: string
}

function requiredText(message: string) {
  return z.string().trim().min(1, message)
}

const optionalText = z
  .string()
  .trim()
  .transform((value) => (value.length > 0 ? value : undefined))
  .optional()

/**
 * Validates the offer information required to produce a grounded adaptation.
 *
 * Field names intentionally match the public backend contract.
 */
export function createUserProfileSchema(
  messages: UserProfileValidationMessages,
) {
  const textList = z
    .array(requiredText(messages.listItemRequired))
    .default([])

  return z.object({
    product_or_solution: requiredText(
      messages.productOrSolutionRequired,
    ),
    target_audience: requiredText(
      messages.targetAudienceRequired,
    ),
    core_problem: requiredText(
      messages.coreProblemRequired,
    ),
    core_desire: requiredText(
      messages.coreDesireRequired,
    ),
    main_promise: requiredText(
      messages.mainPromiseRequired,
    ),
    unique_mechanism: optionalText,
    benefits: textList,
    objections: textList,
    proof_assets: textList,
    offer_details: optionalText,
    call_to_action: requiredText(
      messages.callToActionRequired,
    ),
    tone: optionalText,
    target_language: optionalText,
    platform: optionalText,
    desired_duration: z
      .number()
      .positive(messages.desiredDurationPositive),
    restrictions: textList,
  })
  .strict()
}

export const userProfileSchema = createUserProfileSchema({
  listItemRequired: 'List items cannot be empty.',
  productOrSolutionRequired: 'Describe the product or solution.',
  targetAudienceRequired: 'Describe the target audience.',
  coreProblemRequired: 'Describe the main problem.',
  coreDesireRequired: 'Describe the audience’s main desire.',
  mainPromiseRequired: 'Describe the main promise.',
  callToActionRequired: 'Describe the desired call to action.',
  desiredDurationPositive: 'Duration must be greater than zero.',
})

export type UserProfileFormInput = z.input<typeof userProfileSchema>
export type UserProfileData = z.output<typeof userProfileSchema>
