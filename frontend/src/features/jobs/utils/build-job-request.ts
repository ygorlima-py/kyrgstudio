import type { UserProfileData } from '@/features/user-profile/schemas/user-profile-schema'

import type { JobRequestMetadata } from '../api/jobs-api'
import type { JobCreationData } from '../schemas/job-creation-schema'

/**
 * Converts validated form data into the JSON metadata expected by the API.
 *
 * The uploaded file is intentionally excluded because it occupies its own
 * multipart field.
 */
export function buildJobRequestMetadata(
  formData: JobCreationData,
): JobRequestMetadata {
  const commonMetadata = {
    source_type: formData.source_type,
    need_correction: formData.need_correction,
    ...(formData.language !== undefined
      ? { language: formData.language }
      : {}),
  }

  if (formData.pipeline_type === 'copy_analysis') {
    return {
      ...commonMetadata,
      pipeline_type: 'copy_analysis',
    }
  }

  return {
    ...commonMetadata,
    pipeline_type: 'copy_adaptation',
    user_profile: buildUserProfile(formData.user_profile),
  }
}

function buildUserProfile(
  profile: UserProfileData,
): UserProfileData {
  return {
    product_or_solution: profile.product_or_solution,
    target_audience: profile.target_audience,
    core_problem: profile.core_problem,
    core_desire: profile.core_desire,
    main_promise: profile.main_promise,
    benefits: [...profile.benefits],
    objections: [...profile.objections],
    proof_assets: [...profile.proof_assets],
    call_to_action: profile.call_to_action,
    desired_duration: profile.desired_duration,
    restrictions: [...profile.restrictions],
    ...(profile.unique_mechanism !== undefined
      ? { unique_mechanism: profile.unique_mechanism }
      : {}),
    ...(profile.offer_details !== undefined
      ? { offer_details: profile.offer_details }
      : {}),
    ...(profile.tone !== undefined
      ? { tone: profile.tone }
      : {}),
    ...(profile.target_language !== undefined
      ? { target_language: profile.target_language }
      : {}),
    ...(profile.platform !== undefined
      ? { platform: profile.platform }
      : {}),
  }
}