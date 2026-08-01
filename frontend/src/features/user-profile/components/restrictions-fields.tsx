import { RepeatableTextList } from './repeatable-text-list'

/**
 * Collects claims, topics, expressions, or promises that the adapted copy must
 * not use.
 */
export function RestrictionsFields() {
  return (
    <section
      aria-labelledby="restrictions-heading"
      className="space-y-5 border-t border-border pt-8"
    >
      <div className="space-y-1">
        <h3
          className="font-heading text-heading-sm text-text"
          id="restrictions-heading"
        >
          Restrictions
        </h3>

        <p className="text-body-sm text-text-muted">
          Define the boundaries the adapted script must respect.
        </p>
      </div>

      <RepeatableTextList
        addLabel="Add restriction"
        description="Add prohibited promises, unsupported claims, sensitive topics, words, or approaches that should not appear."
        itemLabel="Describe a restriction"
        label="What must the adapted copy avoid?"
        name="user_profile.restrictions"
      />
    </section>
  )
}