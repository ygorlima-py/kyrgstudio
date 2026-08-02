import type {
  NormalizedCopySection,
  NormalizedCopyStructure,
} from '../utils/normalize-analysis-result'

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

export interface StructureTimelineProps {
  readonly structure: NormalizedCopyStructure
}

/** Show the detected copy sections in their original narrative order. */
export function StructureTimeline({ structure }: StructureTimelineProps) {
  return (
    <section aria-labelledby="copy-structure-heading">
      <div className="border-b border-border pb-5">
        <p className="font-mono text-meta uppercase tracking-[0.14em] text-action">
          Message anatomy
        </p>

        <h2 className="mt-2 font-heading text-heading-3 text-text" id="copy-structure-heading">
          Copy structure
        </h2>

        <p className="mt-2 max-w-3xl text-body text-text-muted">
          The sequence below shows how each part advances the sales argument.
        </p>
      </div>

      {structure.sections.length > 0 ? (
        <ol className="divide-y divide-border border-b border-border">
          {structure.sections.map((section, index) => (
            <StructureStep index={index} key={`${section.type}-${index}`} section={section} />
          ))}
        </ol>
      ) : (
        <p className="border-b border-border py-8 text-body text-text-muted">
          No structural sections were identified in this copy.
        </p>
      )}
    </section>
  )
}

interface StructureStepProps {
  readonly index: number
  readonly section: NormalizedCopySection
}

function StructureStep({ index, section }: StructureStepProps) {
  const timeRange = formatTimeRange(section.startSeconds, section.endSeconds)

  return (
    <li className="grid gap-4 py-6 sm:grid-cols-[3rem_minmax(9rem,0.35fr)_minmax(0,1fr)] sm:gap-6 sm:py-7">
      <span className="font-mono text-meta text-text-subtle">
        {String(index + 1).padStart(2, '0')}
      </span>

      <div>
        <h3 className="text-label text-text">{SECTION_LABELS[section.type]}</h3>
        <p className="mt-1 text-body-sm text-text-muted">{section.purpose}</p>

        {timeRange ? (
          <p className="mt-3 font-mono text-meta text-text-subtle">{timeRange}</p>
        ) : null}
      </div>

      <blockquote className="text-body text-text">{section.text}</blockquote>
    </li>
  )
}

function formatTimeRange(startSeconds: number | null, endSeconds: number | null): string | null {
  if (startSeconds === null && endSeconds === null) {
    return null
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
