import { useTranslation } from 'react-i18next'

export interface NarrativeFlowProps {
  readonly steps: readonly string[]
}

/** Translate the inferred narrative progression into a readable sequence. */
export function NarrativeFlow({ steps }: NarrativeFlowProps) {
  const { t } = useTranslation()

  if (steps.length === 0) {
    return null
  }

  return (
    <section aria-labelledby="narrative-flow-heading" className="min-w-0">
      <details className="group border-y border-border">
        <summary className="flex cursor-pointer list-none items-start justify-between gap-6 py-6 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-focus [&::-webkit-details-marker]:hidden">
          <span className="min-w-0">
            <span className="font-mono text-meta uppercase tracking-[0.14em] text-action">
              {t('analysisResult.narrative.eyebrow')}
            </span>

            <span
              className="mt-2 block font-heading text-heading-3 text-text"
              id="narrative-flow-heading"
            >
              {t('analysisResult.narrative.title')}
            </span>

            <span className="mt-2 block max-w-3xl text-body text-text-muted">
              {t('analysisResult.narrative.description')}
            </span>
          </span>

          <ChevronIcon />
        </summary>

        <ol className="border-t border-border pb-2">
          {steps.map((step, index) => (
            <li
              className="grid min-w-0 grid-cols-[2rem_minmax(0,1fr)] gap-4 border-b border-border py-5 last:border-b-0 sm:grid-cols-[2.5rem_minmax(0,1fr)] sm:gap-5"
              key={`${index}-${step}`}
            >
              <span
                aria-hidden="true"
                className="flex size-7 items-center justify-center rounded-full border border-border-strong font-mono text-meta text-action"
              >
                {index + 1}
              </span>

              <p className="min-w-0 break-words self-center text-body text-text">{step}</p>
            </li>
          ))}
        </ol>
      </details>
    </section>
  )
}

function ChevronIcon() {
  return (
    <svg
      aria-hidden="true"
      className="mt-1 size-4 shrink-0 transition-transform duration-(--duration-fast) group-open:rotate-180"
      fill="none"
      viewBox="0 0 16 16"
    >
      <path
        d="m4 6 4 4 4-4"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.5"
      />
    </svg>
  )
}
