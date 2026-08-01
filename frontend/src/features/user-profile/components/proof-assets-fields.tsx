import { RepeatableTextList } from './repeatable-text-list'

/**
 * Collects real evidence that the adaptation may use to support its claims.
 */
export function ProofAssetsFields() {
  return (
    <section
      aria-labelledby="proof-assets-heading"
      className="space-y-5 border-t border-border pt-8"
    >
      <div className="space-y-1">
        <h3
          className="font-heading text-heading-sm text-text"
          id="proof-assets-heading"
        >
          Available proof
        </h3>

        <p className="text-body-sm text-text-muted">
          Add only evidence that already exists and can be verified. The
          adaptation must not invent testimonials, numbers, or results.
        </p>
      </div>

      <RepeatableTextList
        addLabel="Add proof"
        description="Examples include real testimonials, case studies, demonstrations, credentials, or documented results."
        itemLabel="Describe available proof"
        label="What evidence supports the offer?"
        name="user_profile.proof_assets"
      />
    </section>
  )
}
