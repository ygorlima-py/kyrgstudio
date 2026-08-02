import { Badge } from '@/shared/ui/badge'

import type { NormalizedAdaptedScriptSection } from '../utils/normalize-adaptation-result'

const SECTION_LABELS: Record<NormalizedAdaptedScriptSection['type'], string> = {
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

export interface ScriptSectionsProps {
  readonly sections: readonly NormalizedAdaptedScriptSection[]
}

/** Present the generated script architecture as a compact, expandable list. */
export function ScriptSections({ sections }: ScriptSectionsProps) {
  return (
    <section aria-labelledby="adapted-sections-heading">
      <header className="border-b border-border pb-5">
        <p className="font-mono text-meta uppercase tracking-[0.14em] text-action">
          Script architecture
        </p>
        <h2 className="mt-2 font-heading text-heading-3 text-text" id="adapted-sections-heading">
          Section by section
        </h2>
        <p className="mt-2 max-w-3xl text-body text-text-muted">
          Open a section to inspect its copy, strategic role, source and production timing.
        </p>
      </header>

      {sections.length > 0 ? (
        <div className="divide-y divide-border border-b border-border">
          {sections.map((section) => (
            <ScriptSection key={`${section.order}-${section.type}`} section={section} />
          ))}
        </div>
      ) : (
        <div className="border-b border-border py-8">
          <p className="text-body text-text-muted">No structured script sections were generated.</p>
        </div>
      )}
    </section>
  )
}

interface ScriptSectionProps {
  readonly section: NormalizedAdaptedScriptSection
}

function ScriptSection({ section }: ScriptSectionProps) {
  return (
    <details className="group">
      <summary className="grid min-h-20 cursor-pointer list-none grid-cols-[2rem_minmax(0,1fr)_auto] items-center gap-4 py-5 marker:hidden sm:grid-cols-[3rem_minmax(10rem,0.35fr)_minmax(0,1fr)_auto] sm:gap-6 [&::-webkit-details-marker]:hidden">
        <span className="font-mono text-meta text-text-subtle">
          {String(section.order).padStart(2, '0')}
        </span>

        <div>
          <h3 className="text-label text-text">{SECTION_LABELS[section.type]}</h3>
          <p className="mt-1 font-mono text-meta text-text-subtle">
            {formatDuration(section.estimatedDurationSeconds)}
          </p>
        </div>

        <p className="col-span-3 row-start-2 line-clamp-2 text-body-sm text-text-muted sm:col-span-1 sm:col-start-3 sm:row-start-1">
          {section.purpose}
        </p>

        <span className="col-start-3 row-start-1 flex items-center justify-end gap-3 sm:col-start-4">
          <Badge variant={section.missingProof ? 'warning' : 'neutral'}>
            {section.adaptationMode === 'adapted_from_reference' ? 'Adapted' : 'Original'}
          </Badge>
          <ChevronIcon />
        </span>
      </summary>

      <div className="grid gap-6 border-t border-border bg-surface px-5 py-6 sm:px-6 lg:grid-cols-[minmax(0,1fr)_17rem]">
        <div>
          <p className="font-mono text-meta uppercase tracking-[0.1em] text-text-subtle">
            Section copy
          </p>
          <p className="mt-3 whitespace-pre-wrap text-body leading-7 text-text">{section.text}</p>
        </div>

        <dl className="divide-y divide-border border-y border-border text-body-sm">
          <SectionDetail label="Purpose" value={section.purpose} />
          <SectionDetail
            label="Reference"
            value={
              section.sourceReferenceSectionType ?? 'Created without a matching reference section'
            }
          />
          <SectionDetail
            label="Proof"
            value={
              section.missingProof
                ? 'Requires proof before production'
                : (section.proofUsed ?? 'No proof attached to this section')
            }
          />
          <SectionDetail
            label="Transition"
            value={section.transitionHint ?? 'No transition note provided'}
          />
          <SectionDetail
            label="Timing"
            value={`${formatTimeRange(section.startSeconds, section.endSeconds)} · ${section.wordCount} words`}
          />
        </dl>
      </div>
    </details>
  )
}

interface SectionDetailProps {
  readonly label: string
  readonly value: string
}

function SectionDetail({ label, value }: SectionDetailProps) {
  return (
    <div className="py-3 first:pt-0 last:pb-0">
      <dt className="font-mono text-meta uppercase tracking-[0.08em] text-text-subtle">{label}</dt>
      <dd className="mt-1 text-body-sm text-text-muted">{value}</dd>
    </div>
  )
}

function ChevronIcon() {
  return (
    <svg
      aria-hidden="true"
      className="size-4 shrink-0 text-text-subtle transition-transform duration-(--duration-fast) group-open:rotate-180"
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

function formatDuration(seconds: number | null): string {
  if (seconds === null) {
    return 'Duration unavailable'
  }

  return `${Math.max(0, Math.round(seconds))} sec`
}

function formatTimeRange(startSeconds: number | null, endSeconds: number | null): string {
  if (startSeconds === null && endSeconds === null) {
    return 'Timing unavailable'
  }

  const start = formatTimestamp(startSeconds ?? 0)

  return endSeconds === null ? `From ${start}` : `${start}–${formatTimestamp(endSeconds)}`
}

function formatTimestamp(seconds: number): string {
  const safeSeconds = Math.max(0, Math.floor(seconds))
  const minutes = Math.floor(safeSeconds / 60)
  const remainingSeconds = safeSeconds % 60

  return `${minutes}:${String(remainingSeconds).padStart(2, '0')}`
}
