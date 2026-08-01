import { ProfileTextField } from './profile-text-field'

/**
 * Collects the basic description of the product, service, or solution that
 * will replace the original offer during copy adaptation.
 */
export function ProductOfferFields() {
  return (
    <section
      aria-labelledby="product-offer-heading"
      className="space-y-5"
    >
      <div className="space-y-1">
        <h3
          className="font-heading text-heading-sm text-text"
          id="product-offer-heading"
        >
          Product and offer
        </h3>

        <p className="text-body-sm text-text-muted">
          Explain clearly what you sell and what result it helps the customer
          achieve.
        </p>
      </div>

      <ProfileTextField
        description="Include the type of product, its purpose, and the transformation it provides."
        label="What product or solution are you offering?"
        name="user_profile.product_or_solution"
        placeholder="Example: An online English conversation course for Brazilian adults."
      />
    </section>
  )
}