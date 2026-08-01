import { ProfileTextField } from './profile-text-field'

/**
 * Collects the commercial conditions that may be communicated in the adapted
 * copy.
 */
export function OfferTermsFields() {
  return (
    <section
      aria-labelledby="offer-details-heading"
      className="space-y-5 border-t border-border pt-8"
    >
      <div className="space-y-1">
        <h3
          className="font-heading text-heading-sm text-text"
          id="offer-details-heading"
        >
          Price and conditions
        </h3>

        <p className="text-body-sm text-text-muted">
          Describe the real commercial details that the adapted message may
          present.
        </p>
      </div>

      <ProfileTextField
        description="This field is optional. Include price, payment terms, access period, bonuses, guarantees, or relevant conditions."
        label="What are the offer details?"
        name="user_profile.offer_details"
        placeholder="Example: Twelve months of access, payment in up to 12 installments, and a seven-day guarantee."
      />
    </section>
  )
}