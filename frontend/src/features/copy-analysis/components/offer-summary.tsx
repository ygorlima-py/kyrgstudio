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
    <section aria-labelledby="offer-summary-heading">
      <div className="border-b border-border pb-5">
        <p className="font-mono text-meta uppercase tracking-[0.14em] text-action">
          {t('analysisResult.offer.eyebrow')}
        </p>

        <h2 className="mt-2 font-heading text-heading-3 text-text" id="offer-summary-heading">
          {t('analysisResult.offer.title')}
        </h2>

        <p className="mt-2 max-w-3xl text-body text-text-muted">{offer.summary}</p>
      </div>

      <dl className="grid border-b border-border md:grid-cols-2">
        {coreDetails.map(([label, value]) => (
          <OfferDetail key={label} label={label} value={value} />
        ))}
      </dl>

      <div className="grid gap-x-10 lg:grid-cols-2">
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
        <dl className="grid border-y border-border md:grid-cols-2">
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
    <div className="border-b border-border px-0 py-5 last:border-b-0 md:px-5 md:odd:border-r md:[&:nth-last-child(-n+2)]:border-b-0">
      <dt className="font-mono text-meta uppercase tracking-[0.1em] text-text-subtle">{label}</dt>
      <dd className="mt-2 text-body text-text">
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
    <section aria-label={title} className="border-b border-border py-6">
      <h3 className="text-label text-text">{title}</h3>

      <ul className="mt-4 space-y-5">
        {elements.map((element, index) => (
          <li key={`${element.name}-${index}`}>
            <p className="text-body font-medium text-text">{element.name}</p>
            <p className="mt-1 text-body-sm text-text-muted">{element.description}</p>

            {element.evidence ? (
              <blockquote className="mt-2 border-l border-border-strong pl-3 text-body-sm text-text-subtle">
                {element.evidence}
              </blockquote>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  )
}
