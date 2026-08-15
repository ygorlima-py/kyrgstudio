import { useTranslation } from 'react-i18next'

import type {
  NormalizedOfferAnalysis,
  NormalizedOfferElement,
} from '../utils/normalize-analysis-result'

export interface OfferSummaryProps {
  readonly offer: NormalizedOfferAnalysis
}

/** Present the commercial offer and its supporting elements as readable content. */
export function OfferSummary({ offer }: OfferSummaryProps) {
  const { t } = useTranslation()
  const coreDetails = [
    [t('analysisResult.offer.details.productOrSolution'), offer.productOrSolution],
    [t('analysisResult.offer.details.targetAudience'), offer.targetAudience],
    [t('analysisResult.offer.details.coreProblem'), offer.coreProblem],
    [t('analysisResult.offer.details.coreDesire'), offer.coreDesire],
    [t('analysisResult.offer.details.mainPromise'), offer.mainPromise],
    [t('analysisResult.offer.details.uniqueMechanism'), offer.uniqueMechanism],
  ] as const

  return (
    <section aria-labelledby="offer-summary-heading" className="min-w-0">
      <div className="border-b border-border pb-5">
        <p className="font-mono text-meta uppercase tracking-[0.14em] text-action">
          {t('analysisResult.offer.eyebrow')}
        </p>

        <h2 className="mt-2 font-heading text-heading-3 text-text" id="offer-summary-heading">
          {t('analysisResult.offer.title')}
        </h2>

        <p className="mt-3 max-w-3xl break-words text-body-lg leading-relaxed text-text-muted">
          {offer.summary}
        </p>
      </div>

      <dl className="grid min-w-0 border-b border-border md:grid-cols-2">
        {coreDetails.map(([label, value]) => (
          <OfferDetail key={label} label={label} value={value} />
        ))}
      </dl>

      <div className="grid min-w-0 gap-x-12 lg:grid-cols-2">
        <OfferElementGroup
          elements={offer.benefits}
          title={t('analysisResult.offer.groups.benefits')}
        />
        <OfferElementGroup
          elements={offer.proofElements}
          title={t('analysisResult.offer.groups.proof')}
        />
        <OfferElementGroup
          elements={offer.objections}
          title={t('analysisResult.offer.groups.objections')}
        />
        <OfferElementGroup
          elements={offer.bonuses}
          title={t('analysisResult.offer.groups.bonuses')}
        />
        <OfferElementGroup
          elements={offer.urgencyOrScarcity}
          title={t('analysisResult.offer.groups.urgencyOrScarcity')}
        />
      </div>

      {offer.priceOrTerms || offer.callToAction ? (
        <dl className="grid min-w-0 border-y border-border md:grid-cols-2">
          <OfferDetail
            label={t('analysisResult.offer.details.priceOrTerms')}
            value={offer.priceOrTerms}
          />
          <OfferDetail
            label={t('analysisResult.offer.details.callToAction')}
            value={offer.callToAction}
          />
        </dl>
      ) : null}
    </section>
  )
}

function OfferDetail({ label, value }: { readonly label: string; readonly value: string | null }) {
  const { t } = useTranslation()

  return (
    <div className="min-w-0 border-b border-border px-0 py-5 last:border-b-0 md:px-5 md:odd:border-r md:[&:nth-last-child(-n+2)]:border-b-0">
      <dt className="font-mono text-meta uppercase tracking-[0.1em] text-text-subtle">{label}</dt>
      <dd className="mt-2 break-words text-body text-text">
        {value ?? t('analysisResult.common.notIdentified')}
      </dd>
    </div>
  )
}

interface OfferElementGroupProps {
  readonly elements: readonly NormalizedOfferElement[]
  readonly title: string
}

function OfferElementGroup({ elements, title }: OfferElementGroupProps) {
  if (elements.length === 0) {
    return null
  }

  return (
    <section aria-label={title} className="min-w-0 border-b border-border">
      <details className="group min-w-0">
        <summary className="flex min-w-0 cursor-pointer list-none items-center justify-between gap-5 py-6 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-focus [&::-webkit-details-marker]:hidden">
          <h3 className="min-w-0 text-label text-text [overflow-wrap:anywhere]">{title}</h3>
          <ChevronIcon />
        </summary>

        <ul className="min-w-0 space-y-5 pb-7 pr-8 sm:pr-12">
          {elements.map((element, index) => (
            <li className="min-w-0" key={`${element.name}-${index}`}>
              <p className="text-body font-medium text-text [overflow-wrap:anywhere]">
                {element.name}
              </p>
              <p className="mt-1 text-body-sm text-text-muted [overflow-wrap:anywhere]">
                {element.description}
              </p>

              {element.evidence ? (
                <blockquote className="mt-2 border-l border-border-strong pl-3 text-body-sm text-text-subtle [overflow-wrap:anywhere]">
                  {element.evidence}
                </blockquote>
              ) : null}
            </li>
          ))}
        </ul>
      </details>
    </section>
  )
}

function ChevronIcon() {
  return (
    <svg
      aria-hidden="true"
      className="size-4 shrink-0 transition-transform duration-(--duration-fast) group-open:rotate-180"
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
