import { useTranslation } from 'react-i18next'

import { ProfileTextField } from './profile-text-field'

/**
 * Collects who the adapted copy should address and which primary problem it
 * should explore.
 */
export function AudienceProblemFields() {
  const { t } = useTranslation()

  return (
    <section
      aria-labelledby="audience-problem-heading"
      className="space-y-5 border-t border-border pt-8"
    >
      <div className="space-y-1">
        <h3
          className="font-heading text-heading-sm text-text"
          id="audience-problem-heading"
        >
          {t('userProfile.audienceProblem.title')}
        </h3>

        <p className="text-body-sm text-text-muted">
          {t('userProfile.audienceProblem.description')}
        </p>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <ProfileTextField
          description={t('userProfile.audienceProblem.audience.description')}
          label={t('userProfile.audienceProblem.audience.label')}
          name="user_profile.target_audience"
          placeholder={t('userProfile.audienceProblem.audience.placeholder')}
        />

        <ProfileTextField
          description={t('userProfile.audienceProblem.problem.description')}
          label={t('userProfile.audienceProblem.problem.label')}
          name="user_profile.core_problem"
          placeholder={t('userProfile.audienceProblem.problem.placeholder')}
        />
      </div>
    </section>
  )
}
