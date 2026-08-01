import { ProfileTextField } from './profile-text-field'

/**
 * Defines the action the audience should take after consuming the adapted
 * sales message.
 */
export function CallToActionFields() {
  return (
    <section
      aria-labelledby="call-to-action-heading"
      className="space-y-5 border-t border-border pt-8"
    >
      <div className="space-y-1">
        <h3
          className="font-heading text-heading-sm text-text"
          id="call-to-action-heading"
        >
          Call to action
        </h3>

        <p className="text-body-sm text-text-muted">
          Explain clearly what the audience should do after watching or
          listening to the adapted message.
        </p>
      </div>

      <ProfileTextField
        description="Use a specific action that matches the real purchasing or contact process."
        label="What action should the audience take?"
        name="user_profile.call_to_action"
        placeholder="Example: Click the button to learn more about the course and enroll."
      />
    </section>
  )
}