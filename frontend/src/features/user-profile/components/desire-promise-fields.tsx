import { ProfileTextField } from './profile-text-field'

/**
 * Defines the audience's desired outcome and the responsible promise the
 * adapted copy may communicate.
 */
export function DesirePromiseFields() {
  return (
    <section
      aria-labelledby="desire-promise-heading"
      className="space-y-5 border-t border-border pt-8"
    >
      <div className="space-y-1">
        <h3
          className="font-heading text-heading-sm text-text"
          id="desire-promise-heading"
        >
          Desire and promise
        </h3>

        <p className="text-body-sm text-text-muted">
          Define what the audience wants and what your offer can responsibly
          promise.
        </p>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <ProfileTextField
          description="Describe the result, feeling, or situation the audience wants to reach."
          label="What does the audience most want?"
          name="user_profile.core_desire"
          placeholder="Example: Speak English confidently in everyday and professional situations."
        />

        <ProfileTextField
          description="Use a realistic promise that your product can support without exaggeration."
          label="What is the main promise?"
          name="user_profile.main_promise"
          placeholder="Example: Build the confidence and practical ability needed for real conversations."
        />
      </div>
    </section>
  )
}