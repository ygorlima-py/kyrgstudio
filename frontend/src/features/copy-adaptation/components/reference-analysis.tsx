import { Badge } from '@/shared/ui/badge'

import type {
  NormalizedAnalysisResult,
  NormalizedCopySection,
} from '@/features/copy-analysis/utils/normalize-analysis-result'

const SECTION_LABELS: Record<NormalizedCopySection['type'], string> = {
  hook: 'Hook',
  problem: 'Problem',
  pain: 'Pain',
  agitation: 'Agitation',
  promise: 'Promise',
  mechanism: 'Mechanism',
  proof: 'Proof',
  story: 'Story',
  objection: 'Objection',
  offer: 'Offer',
  cta: 'Call to action',
  urgency: 'Urgency',
  scarcity: 'Scarcity',
  transition: 'Transition',
  education: 'Education',
  payoff: 'Payoff',
}

export interface ReferenceAnalysisProps {
  readonly analysis: NormalizedAnalysisResult
}

/** Keep the source strategy available without mixing it with the adapted copy. */
export function ReferenceAnalysis({ analysis }: ReferenceAnalysisProps) {
  return (
    <section aria-labelledby="reference-analysis-heading">
      <details className="group overflow-hidden rounded-lg border border-border bg-surface">
        <summary className="grid cursor-pointer list-none gap-4 px-5 py-6 marker:hidden sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center sm:px-8 sm:py-7 [&::-webkit-details-marker]:hidden">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <p className="font-mono text-meta uppercase tracking-[0.14em] text-action">
                Strategic source
              </p>
              <Badge variant="neutral">Reference only</Badge>
            </div>
            <h2
              className="mt-2 font-heading text-heading-3 text-text"
              id="reference-analysis-heading"
            >
              Original copy analysis
            </h2>
            <p className="mt-2 line-clamp-2 max-w-3xl text-body-sm text-text-muted">
              {analysis.structure.summary}
            </p>
          </div>

          <span className="flex items-center gap-2 text-label text-text-muted">
            View reference
            <ChevronIcon />
          </span>
        </summary>

        <div className="border-t border-border">
          <dl className="grid grid-cols-2 gap-px border-b border-border bg-border lg:grid-cols-4">
            <ReferenceMetric label="Content type" value={analysis.structure.contentType} />
            <ReferenceMetric
              label="Language"
              value={analysis.language ?? analysis.structure.language ?? 'Not identified'}
            />
            <ReferenceMetric
              label="Persuasion pattern"
              value={analysis.persuasion.pattern ?? 'Not identified'}
            />
            <ReferenceMetric
              label="Dominant emotion"
              value={analysis.persuasion.dominantEmotion ?? 'Not identified'}
            />
          </dl>

          <div className="grid lg:grid-cols-[minmax(0,1.15fr)_minmax(18rem,0.85fr)]">
            <div className="px-5 py-6 sm:px-8 sm:py-8">
              <p className="font-mono text-meta uppercase tracking-[0.1em] text-text-subtle">
                Reference hook
              </p>
              {analysis.structure.mainHook ? (
                <blockquote className="mt-4 border-l-2 border-action pl-5 font-heading text-heading-3 text-text">
                  {analysis.structure.mainHook}
                </blockquote>
              ) : (
                <p className="mt-3 text-body text-text-muted">No dominant hook was identified.</p>
              )}
            </div>

            <div className="border-t border-border px-5 py-6 sm:px-8 lg:border-t-0 lg:border-l lg:px-6 lg:py-8">
              <ReferenceSummary label="Offer reading" value={analysis.offer.summary} />
              <ReferenceSummary label="Persuasion reading" value={analysis.persuasion.summary} />
            </div>
          </div>

          <div className="border-t border-border px-5 py-6 sm:px-8">
            <p className="font-mono text-meta uppercase tracking-[0.1em] text-text-subtle">
              Reference sequence
            </p>
            {analysis.structure.sections.length > 0 ? (
              <ol className="mt-4 grid gap-x-6 gap-y-3 sm:grid-cols-2 lg:grid-cols-3">
                {analysis.structure.sections.map((section, index) => (
                  <li
                    className="grid grid-cols-[2rem_minmax(0,1fr)] items-baseline gap-2 border-b border-border pb-3"
                    key={`${section.type}-${index}`}
                  >
                    <span className="font-mono text-meta text-text-subtle">
                      {String(index + 1).padStart(2, '0')}
                    </span>
                    <span className="text-body-sm font-medium text-text">
                      {SECTION_LABELS[section.type]}
                    </span>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="mt-3 text-body text-text-muted">
                No structural sequence was identified in the reference.
              </p>
            )}
          </div>

          <footer className="border-t border-border bg-surface-muted/45 px-5 py-4 sm:px-8">
            <p className="text-body-sm text-text-muted">
              Use this analysis to understand the strategic pattern. The adapted script should
              preserve the logic, not copy the original wording or unsupported claims.
            </p>
          </footer>
        </div>
      </details>
    </section>
  )
}

interface ReferenceMetricProps {
  readonly label: string
  readonly value: string
}

function ReferenceMetric({ label, value }: ReferenceMetricProps) {
  return (
    <div className="bg-surface px-5 py-4 sm:px-6">
      <dt className="font-mono text-meta uppercase tracking-[0.08em] text-text-subtle">{label}</dt>
      <dd className="mt-1 text-body-sm font-medium text-text">{formatLabel(value)}</dd>
    </div>
  )
}

interface ReferenceSummaryProps {
  readonly label: string
  readonly value: string
}

function ReferenceSummary({ label, value }: ReferenceSummaryProps) {
  return (
    <section className="border-b border-border py-5 first:pt-0 last:border-b-0 last:pb-0">
      <h3 className="font-mono text-meta uppercase tracking-[0.08em] text-text-subtle">{label}</h3>
      <p className="mt-2 text-body-sm text-text-muted">{value}</p>
    </section>
  )
}

function ChevronIcon() {
  return (
    <svg
      aria-hidden="true"
      className="size-4 shrink-0 transition-transform duration-(--duration-fast) group-open:rotate-180"
      fill="none"
      viewBox="0 0 20 20"
    >
      <path
        d="m5 7.5 5 5 5-5"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.5"
      />
    </svg>
  )
}

function formatLabel(value: string): string {
  const normalizedValue = value.trim().replaceAll(/[_-]+/g, ' ')
  return normalizedValue.charAt(0).toUpperCase() + normalizedValue.slice(1)
}
