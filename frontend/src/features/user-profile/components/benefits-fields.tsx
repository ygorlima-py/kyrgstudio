import { RepeatableTextList } from './repeatable-text-list'

/**
 * Collects the concrete benefits that the adapted copy may communicate.
 */
export function BenefitsFields() {
  return (
    <section
      aria-labelledby="benefits-heading"
      className="space-y-5 border-t border-border pt-8"
    >
      <div className="space-y-1">
        <h3
          className="font-heading text-heading-sm text-text"
          id="benefits-heading"
        >
          Benefits
        </h3>

        <p className="text-body-sm text-text-muted">
          Add the most important practical or emotional benefits provided by
          the offer.
        </p>
      </div>

      <RepeatableTextList
        addLabel="Add benefit"
        description="Use one clear benefit per item. Avoid promises that the product cannot support."
        itemLabel="Describe a benefit"
        label="What benefits can the customer expect?"
        name="user_profile.benefits"
      />
    </section>
  )
}
