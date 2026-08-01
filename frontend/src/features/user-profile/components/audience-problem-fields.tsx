import { ProfileTextField } from './profile-text-field'

/**
 * Collects who the adapted copy should address and which primary problem it
 * should explore.
 */
export function AudienceProblemFields() {
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
          Audience and problem
        </h3>

        <p className="text-body-sm text-text-muted">
          Describe the person this message should reach and the main problem
          they are trying to solve.
        </p>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <ProfileTextField
          description="Include relevant characteristics, context, experience, and current situation."
          label="Who is the target audience?"
          name="user_profile.target_audience"
          placeholder="Example: Brazilian adults who understand English but freeze when speaking."
        />

        <ProfileTextField
          description="Focus on the most important difficulty the offer addresses."
          label="What is their main problem?"
          name="user_profile.core_problem"
          placeholder="Example: They have studied for years but cannot speak naturally in real situations."
        />
      </div>
    </section>
  )
}