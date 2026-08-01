import { RepeatableTextList } from './repeatable-text-list'

/**
 * Collects the main reasons that may prevent the target audience from
 * accepting the offer.
 */
export function ObjectionsFields() {
  return (
    <section
      aria-labelledby="objections-heading"
      className="space-y-5 border-t border-border pt-8"
    >
      <div className="space-y-1">
        <h3
          className="font-heading text-heading-sm text-text"
          id="objections-heading"
        >
          Objections
        </h3>

        <p className="text-body-sm text-text-muted">
          List the doubts, fears, or reasons that may stop the audience from
          taking action.
        </p>
      </div>

      <RepeatableTextList
        addLabel="Add objection"
        description="Use one objection per item and write it from the customer’s perspective."
        itemLabel="Describe an objection"
        label="What objections does the audience have?"
        name="user_profile.objections"
      />
    </section>
  )
}
