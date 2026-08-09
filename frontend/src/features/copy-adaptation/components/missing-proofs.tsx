import { useTranslation } from 'react-i18next'

import { Badge } from '@/shared/ui/badge'

export interface MissingProofsProps {
  readonly proofs: readonly string[]
}

/** Highlight claims that still require real supporting material. */
export function MissingProofs({ proofs }: MissingProofsProps) {
  const { t } = useTranslation()
  const hasMissingProofs = proofs.length > 0

  return (
    <section
      aria-labelledby="missing-proofs-heading"
      className="overflow-hidden rounded-lg border border-border bg-surface"
    >
      <header className="grid gap-4 border-b border-border px-5 py-6 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-start sm:px-8 sm:py-7">
        <div>
          <p className="font-mono text-meta uppercase tracking-[0.14em] text-action">
            {t('adaptationResult.missingProofs.eyebrow')}
          </p>
          <h2 className="mt-2 font-heading text-heading-3 text-text" id="missing-proofs-heading">
            {t('adaptationResult.missingProofs.title')}
          </h2>
          <p className="mt-2 max-w-2xl text-body-sm text-text-muted">
            {t('adaptationResult.missingProofs.description')}
          </p>
        </div>

        <Badge variant={hasMissingProofs ? 'warning' : 'success'}>
          {hasMissingProofs
            ? t('adaptationResult.missingProofs.count', { count: proofs.length })
            : t('adaptationResult.missingProofs.noGapsFound')}
        </Badge>
      </header>

      {hasMissingProofs ? (
        <ol className="divide-y divide-border">
          {proofs.map((proof, index) => (
            <li
              className="grid gap-3 px-5 py-5 sm:grid-cols-[2.5rem_minmax(0,1fr)] sm:px-8"
              key={`${index}-${proof}`}
            >
              <span className="font-mono text-meta text-warning">
                {String(index + 1).padStart(2, '0')}
              </span>
              <p className="text-body text-text">{proof}</p>
            </li>
          ))}
        </ol>
      ) : (
        <p className="px-5 py-7 text-body text-text-muted sm:px-8">
          {t('adaptationResult.missingProofs.empty')}
        </p>
      )}

      {hasMissingProofs ? (
        <footer className="border-t border-border bg-surface-muted/45 px-5 py-4 sm:px-8">
          <p className="text-body-sm text-text-muted">
            {t('adaptationResult.missingProofs.warning')}
          </p>
        </footer>
      ) : null}
    </section>
  )
}
