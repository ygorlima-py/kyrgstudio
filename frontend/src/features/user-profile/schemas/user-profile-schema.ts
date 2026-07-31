import { z } from 'zod'

function requiredText(message: string) {
  return z.string().trim().min(1, message)
}

const optionalText = z
  .string()
  .trim()
  .transform((value) => (value.length > 0 ? value : undefined))
  .optional()

const textList = z
  .array(requiredText('List items cannot be empty.'))
  .default([])

/**
 * Validates the offer information required to produce a grounded adaptation.
 *
 * Field names intentionally match the public backend contract.
 */
export const userProfileSchema = z
  .object({
    product_or_solution: requiredText(
      'Describe the product or solution.',
    ),
    target_audience: requiredText(
      'Describe the target audience.',
    ),
    core_problem: requiredText(
      'Describe the main problem.',
    ),
    core_desire: requiredText(
      'Describe the audience’s main desire.',
    ),
    main_promise: requiredText(
      'Describe the main promise.',
    ),
    unique_mechanism: optionalText,
    benefits: textList,
    objections: textList,
    proof_assets: textList,
    offer_details: optionalText,
    call_to_action: requiredText(
      'Describe the desired call to action.',
    ),
    tone: optionalText,
    target_language: optionalText,
    platform: optionalText,
    desired_duration: z
      .number()
      .positive('Duration must be greater than zero.'),
    restrictions: textList,
  })
  .strict()

export type UserProfileFormInput = z.input<typeof userProfileSchema>
export type UserProfileData = z.output<typeof userProfileSchema>