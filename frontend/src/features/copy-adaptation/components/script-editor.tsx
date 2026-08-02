import { useId, useState, type ReactNode } from 'react'

import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { Textarea } from '@/shared/ui/textarea'

import type { NormalizedAdaptedScript } from '../utils/normalize-adaptation-result'

export interface ScriptEditorProps {
  readonly script: NormalizedAdaptedScript
}

/** Provide an in-memory editing workspace for the generated script. */
export function ScriptEditor({ script }: ScriptEditorProps) {
  return <ScriptEditorSession key={script.script} script={script} />
}

function ScriptEditorSession({ script }: ScriptEditorProps) {
  const editorDescriptionId = useId()
  const editorId = useId()
  const [draft, setDraft] = useState(script.script)
  const hasLocalChanges = draft !== script.script
  const currentWordCount = hasLocalChanges
    ? countWords(draft)
    : (script.wordCount ?? countWords(draft))

  return (
    <section
      aria-labelledby="script-editor-heading"
      className="overflow-hidden rounded-lg border border-border bg-surface"
    >
      <header className="border-b border-border px-5 py-6 sm:px-8 sm:py-7">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="font-mono text-meta uppercase tracking-[0.14em] text-action">
              Working draft
            </p>
            <h2 className="mt-2 font-heading text-heading-3 text-text" id="script-editor-heading">
              Adapted script
            </h2>
            <p className="mt-2 max-w-2xl text-body-sm text-text-muted">
              Refine the generated copy here. Changes remain in this browser tab and are not saved
              to your account yet.
            </p>
          </div>

          <Badge variant={hasLocalChanges ? 'warning' : 'neutral'}>
            {hasLocalChanges ? 'Local changes' : 'Generated version'}
          </Badge>
        </div>
      </header>

      <dl className="grid grid-cols-2 gap-px border-b border-border bg-border sm:grid-cols-4">
        <ScriptMetric label="Draft words" value={currentWordCount.toLocaleString()} />
        <ScriptMetric label="Sections" value={String(script.sections.length)} />
        <ScriptMetric
          label="Estimated length"
          value={formatDuration(script.estimatedDurationSeconds)}
        />
        <ScriptMetric label="Hook options" value={String(script.hooks.length)} />
      </dl>

      <div className="grid lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="px-5 py-6 sm:px-8 sm:py-8">
          <div className="flex items-end justify-between gap-4">
            <label className="text-label text-text" htmlFor={editorId}>
              Full script
            </label>
            <span className="font-mono text-meta text-text-subtle" role="status">
              {hasLocalChanges ? 'Edited locally' : 'No local edits'}
            </span>
          </div>

          <Textarea
            aria-describedby={editorDescriptionId}
            className="mt-3 min-h-[34rem] resize-y px-4 py-4 text-body leading-7 shadow-none"
            id={editorId}
            onChange={(event) => setDraft(event.target.value)}
            spellCheck
            value={draft}
          />

          <div className="mt-4 flex flex-col gap-3 border-t border-border pt-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="max-w-xl text-body-sm text-text-muted" id={editorDescriptionId}>
              Editing does not change the structured sections, validation or stored result.
            </p>
            <Button
              disabled={!hasLocalChanges}
              onClick={() => setDraft(script.script)}
              size="sm"
              variant="secondary"
            >
              Reset draft
            </Button>
          </div>
        </div>

        <aside
          aria-label="Script context"
          className="border-t border-border bg-surface-muted/45 px-5 py-6 sm:px-8 lg:border-t-0 lg:border-l lg:px-6 lg:py-8"
        >
          <ScriptContext title="Hook options">
            {script.hooks.length > 0 ? (
              <ol className="space-y-3">
                {script.hooks.map((hook, index) => (
                  <li
                    className="grid grid-cols-[1.5rem_1fr] gap-2 text-body-sm text-text"
                    key={`${index}-${hook}`}
                  >
                    <span className="font-mono text-meta text-text-subtle">
                      {String(index + 1).padStart(2, '0')}
                    </span>
                    <span>{hook}</span>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="text-body-sm text-text-muted">
                No separate hook options were generated.
              </p>
            )}
          </ScriptContext>

          <ScriptContext title="Primary call to action">
            <p className="text-body-sm text-text-muted">
              {script.callToAction ?? 'No primary call to action was identified.'}
            </p>
          </ScriptContext>

          <ScriptContext title="Adaptation notes">
            <p className="text-body-sm text-text-muted">
              {script.adaptationNotes ?? 'No additional adaptation notes were provided.'}
            </p>
          </ScriptContext>
        </aside>
      </div>
    </section>
  )
}

interface ScriptMetricProps {
  readonly label: string
  readonly value: string
}

function ScriptMetric({ label, value }: ScriptMetricProps) {
  return (
    <div className="bg-surface px-5 py-4 sm:px-6">
      <dt className="font-mono text-meta uppercase tracking-[0.08em] text-text-subtle">{label}</dt>
      <dd className="mt-1 text-body font-semibold text-text">{value}</dd>
    </div>
  )
}

interface ScriptContextProps {
  readonly children: ReactNode
  readonly title: string
}

function ScriptContext({ children, title }: ScriptContextProps) {
  return (
    <section className="border-b border-border py-5 first:pt-0 last:border-b-0 last:pb-0">
      <h3 className="font-mono text-meta uppercase tracking-[0.1em] text-text-subtle">{title}</h3>
      <div className="mt-3">{children}</div>
    </section>
  )
}

function countWords(value: string): number {
  const normalizedValue = value.replace(/^#{1,6}\s+.*$/gmu, '').trim()

  return normalizedValue ? normalizedValue.split(/\s+/u).length : 0
}

function formatDuration(seconds: number | null): string {
  if (seconds === null) {
    return 'Not estimated'
  }

  const roundedSeconds = Math.max(0, Math.round(seconds))
  const minutes = Math.floor(roundedSeconds / 60)
  const remainingSeconds = roundedSeconds % 60

  return minutes > 0
    ? `${minutes}m ${String(remainingSeconds).padStart(2, '0')}s`
    : `${remainingSeconds}s`
}
