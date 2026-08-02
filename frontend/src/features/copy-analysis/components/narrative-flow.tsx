export interface NarrativeFlowProps {
  readonly steps: readonly string[]
}

/** Translate the inferred narrative progression into a readable sequence. */
export function NarrativeFlow({ steps }: NarrativeFlowProps) {
  return (
    <section aria-labelledby="narrative-flow-heading">
      <div>
        <p className="font-mono text-meta uppercase tracking-[0.14em] text-action">
          Strategic progression
        </p>

        <h2 className="mt-2 font-heading text-heading-3 text-text" id="narrative-flow-heading">
          Narrative flow
        </h2>

        <p className="mt-2 max-w-3xl text-body text-text-muted">
          How the message moves the audience from attention toward action.
        </p>
      </div>

      {steps.length > 0 ? (
        <ol className="mt-6 border-y border-border">
          {steps.map((step, index) => (
            <li
              className="grid grid-cols-[2.5rem_minmax(0,1fr)] gap-4 border-b border-border py-5 last:border-b-0 sm:grid-cols-[3rem_minmax(0,1fr)] sm:gap-6"
              key={`${index}-${step}`}
            >
              <span
                aria-hidden="true"
                className="flex size-8 items-center justify-center rounded-full border border-border-strong font-mono text-meta text-action"
              >
                {index + 1}
              </span>

              <p className="self-center text-body text-text">{step}</p>
            </li>
          ))}
        </ol>
      ) : (
        <p className="mt-6 border-y border-border py-7 text-body text-text-muted">
          No narrative progression was identified in this copy.
        </p>
      )}
    </section>
  )
}
