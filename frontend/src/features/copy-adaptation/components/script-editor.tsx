import { useId, useState, type ReactNode } from 'react'

import type { TFunction } from 'i18next'
import { useTranslation } from 'react-i18next'

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
  const { t } = useTranslation()
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
              {t('adaptationResult.scriptEditor.eyebrow')}
            </p>
            <h2 className="mt-2 font-heading text-heading-3 text-text" id="script-editor-heading">
              {t('adaptationResult.scriptEditor.title')}
            </h2>
            <p className="mt-2 max-w-2xl text-body-sm text-text-muted">
              {t('adaptationResult.scriptEditor.description')}
            </p>
          </div>

          <Badge variant={hasLocalChanges ? 'warning' : 'neutral'}>
            {hasLocalChanges
              ? t('adaptationResult.scriptEditor.localChanges')
              : t('adaptationResult.scriptEditor.generatedVersion')}
          </Badge>
        </div>
      </header>

      <dl className="grid grid-cols-2 gap-px border-b border-border bg-border sm:grid-cols-4">
        <ScriptMetric
          label={t('adaptationResult.scriptEditor.draftWords')}
          value={currentWordCount.toLocaleString()}
        />
        <ScriptMetric
          label={t('adaptationResult.scriptEditor.sections')}
          value={String(script.sections.length)}
        />
        <ScriptMetric
          label={t('adaptationResult.scriptEditor.estimatedLength')}
          value={formatDuration(script.estimatedDurationSeconds, t)}
        />
        <ScriptMetric
          label={t('adaptationResult.scriptEditor.hookOptions')}
          value={String(script.hooks.length)}
        />
      </dl>

      <div className="grid lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="px-5 py-6 sm:px-8 sm:py-8">
          <div className="flex items-end justify-between gap-4">
            <label className="text-label text-text" htmlFor={editorId}>
              {t('adaptationResult.scriptEditor.fullScript')}
            </label>
            <span className="font-mono text-meta text-text-subtle" role="status">
              {hasLocalChanges
                ? t('adaptationResult.scriptEditor.editedLocally')
                : t('adaptationResult.scriptEditor.noLocalEdits')}
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
              {t('adaptationResult.scriptEditor.editingNote')}
            </p>
            <Button
              disabled={!hasLocalChanges}
              onClick={() => setDraft(script.script)}
              size="sm"
              variant="secondary"
            >
              {t('adaptationResult.scriptEditor.resetDraft')}
            </Button>
          </div>
        </div>

        <aside
          aria-label={t('adaptationResult.scriptEditor.contextAriaLabel')}
          className="border-t border-border bg-surface-muted/45 px-5 py-6 sm:px-8 lg:border-t-0 lg:border-l lg:px-6 lg:py-8"
        >
          <ScriptContext title={t('adaptationResult.scriptEditor.hookOptions')}>
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
                {t('adaptationResult.scriptEditor.noHookOptions')}
              </p>
            )}
          </ScriptContext>

          <ScriptContext title={t('adaptationResult.scriptEditor.primaryCallToAction')}>
            <p className="text-body-sm text-text-muted">
              {script.callToAction ?? t('adaptationResult.scriptEditor.noPrimaryCallToAction')}
            </p>
          </ScriptContext>

          <ScriptContext title={t('adaptationResult.scriptEditor.adaptationNotes')}>
            <p className="text-body-sm text-text-muted">
              {script.adaptationNotes ?? t('adaptationResult.scriptEditor.noAdaptationNotes')}
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

function formatDuration(seconds: number | null, t: TFunction): string {
  if (seconds === null) {
    return t('adaptationResult.scriptEditor.notEstimated')
  }

  const roundedSeconds = Math.max(0, Math.round(seconds))
  const minutes = Math.floor(roundedSeconds / 60)
  const remainingSeconds = roundedSeconds % 60

  return minutes > 0
    ? `${minutes}m ${String(remainingSeconds).padStart(2, '0')}s`
    : `${remainingSeconds}s`
}
