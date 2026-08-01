import { ProfileTextField } from './profile-text-field'

/**
 * Describes the method or approach that explains how the offer produces its
 * intended result.
 */
export function MechanismFields() {
  return (
    <section
      aria-labelledby="mechanism-heading"
      className="space-y-5 border-t border-border pt-8"
    >
      <div className="space-y-1">
        <h3
          className="font-heading text-heading-sm text-text"
          id="mechanism-heading"
        >
          Unique mechanism
        </h3>

        <p className="text-body-sm text-text-muted">
          Explain what makes the approach different and why it may work better
          for this audience.
        </p>
      </div>

      <ProfileTextField
        description="This field is optional. Describe a real method, process, framework, or differentiator without inventing claims."
        label="How does your solution work?"
        name="user_profile.unique_mechanism"
        placeholder="Example: Conversation practice based on situations the student encounters in everyday life."
      />
    </section>
  )
}