import { ProfileTextField } from './profile-text-field'

/**
 * Defines how the adapted copy should sound and which language it should use
 * in the final script.
 */
export function ToneLanguageFields() {
  return (
    <section
      aria-labelledby="tone-language-heading"
      className="space-y-5 border-t border-border pt-8"
    >
      <div className="space-y-1">
        <h3
          className="font-heading text-heading-sm text-text"
          id="tone-language-heading"
        >
          Tone and output language
        </h3>

        <p className="text-body-sm text-text-muted">
          Define the intended voice of the adapted copy and the language of the
          final script.
        </p>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <ProfileTextField
          description="Describe the desired communication style using a few clear characteristics."
          label="What tone should the copy use?"
          name="user_profile.tone"
          placeholder="Example: Direct, welcoming, confident, and conversational."
        />

        <ProfileTextField
          description="Use a language or locale such as English, Portuguese, pt-BR, or es-MX."
          label="What language should the final script use?"
          multiline={false}
          name="user_profile.target_language"
          placeholder="Example: pt-BR"
        />
      </div>
    </section>
  )
}