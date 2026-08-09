import { useTranslation } from 'react-i18next'
import {
  useRef,
  useState,
  type ChangeEvent,
  type DragEvent,
} from 'react'
import type { TFunction } from 'i18next'
import { useFormContext, useWatch } from 'react-hook-form'

import { environment } from '@/shared/config/environment'
import { Button } from '@/shared/ui/button'
import { FieldMessage } from '@/shared/ui/field-message'
import { cn } from '@/shared/utils/class-names'

import type { JobCreationFormInput } from '../schemas/job-creation-schema'
import {
  formatFileSize,
  validateJobFile,
  type JobFileValidationResult,
} from '../utils/validate-job-file'

/**
 * Handles selection and preliminary validation of the pipeline input file.
 *
 * Only the File reference is stored in the form. The file contents are not
 * loaded into browser memory.
 */
export function FileUploadStep() {
  const { t } = useTranslation()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [isDragging, setIsDragging] = useState(false)

  const {
    clearErrors,
    formState: { errors },
    resetField,
    setError,
    setValue,
    control,
  } = useFormContext<JobCreationFormInput>()

  const selectedFile = useWatch({
    control,
    name: 'file',
  })

  const fileError =
    typeof errors.file?.message === 'string'
      ? errors.file.message
      : undefined

  function selectFile(file: File) {
    const validation = validateJobFile(file)

    if (!validation.valid) {
      setError('file', {
        type: validation.code,
        message: getFileValidationMessage(validation, t),
      })
      return
    }

    setValue('file', file, {
      shouldDirty: true,
      shouldTouch: true,
      shouldValidate: true,
    })

    setValue('source_type', validation.sourceType, {
      shouldDirty: true,
      shouldValidate: true,
    })

    clearErrors('file')
  }

  function handleFileInputChange(
    event: ChangeEvent<HTMLInputElement>,
  ) {
    const file = event.currentTarget.files?.item(0)

    if (file) {
      selectFile(file)
    }

    // Allows selecting the same file again after removing or correcting it.
    event.currentTarget.value = ''
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setIsDragging(false)

    const file = event.dataTransfer.files.item(0)

    if (file) {
      selectFile(file)
    }
  }

  function removeSelectedFile() {
    resetField('file')
    resetField('source_type')
    clearErrors('file')

    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <section aria-labelledby="file-upload-heading" className="space-y-6">
      <div className="space-y-2">
        <h2
          className="font-heading text-heading-md text-text"
          id="file-upload-heading"
        >
          {t('newJob.file.title')}
        </h2>

        <p className="max-w-2xl text-body text-text-muted">
          {t('newJob.file.description')}
        </p>
      </div>

      <input
        ref={fileInputRef}
        accept={environment.acceptedMediaTypes.join(',')}
        className="sr-only"
        onChange={handleFileInputChange}
        type="file"
      />

      {!selectedFile ? (
        <div
          className={cn(
            'flex min-h-64 flex-col items-center justify-center rounded-lg',
            'border border-dashed border-border-strong px-6 py-10 text-center',
            'transition-colors',
            isDragging && 'border-action bg-surface-muted',
          )}
          onDragEnter={(event) => {
            event.preventDefault()
            setIsDragging(true)
          }}
          onDragLeave={() => setIsDragging(false)}
          onDragOver={(event) => event.preventDefault()}
          onDrop={handleDrop}
        >
          <div className="max-w-md space-y-4">
            <div className="space-y-1">
              <p className="font-medium text-text">
                {t('newJob.file.dropzone.title')}
              </p>

              <p className="text-body-sm text-text-muted">
                {t('newJob.file.dropzone.description', {
                  maxSize: formatFileSize(environment.maxUploadBytes),
                })}
              </p>
            </div>

            <Button
              onClick={() => fileInputRef.current?.click()}
              variant="secondary"
            >
              {t('newJob.file.actions.select')}
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex flex-col gap-4 border-y border-border py-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <p className="truncate font-medium text-text">
              {selectedFile.name}
            </p>

            <p className="mt-1 text-body-sm text-text-muted">
              {selectedFile.type} · {formatFileSize(selectedFile.size)}
            </p>
          </div>

          <div className="flex shrink-0 gap-2">
            <Button
              onClick={() => fileInputRef.current?.click()}
              size="sm"
              variant="secondary"
            >
              {t('newJob.file.actions.replace')}
            </Button>

            <Button
              onClick={removeSelectedFile}
              size="sm"
              variant="ghost"
            >
              {t('newJob.file.actions.remove')}
            </Button>
          </div>
        </div>
      )}

      {fileError ? (
        <FieldMessage variant="error">{fileError}</FieldMessage>
      ) : null}
    </section>
  )
}

function getFileValidationMessage(
  validation: Extract<JobFileValidationResult, { readonly valid: false }>,
  translate: TFunction,
): string {
  switch (validation.code) {
    case 'missing_filename':
      return translate('newJob.file.validation.missingFilename')

    case 'empty_file':
      return translate('newJob.file.validation.emptyFile')

    case 'unsupported_media_type':
      return translate('newJob.file.validation.unsupportedMediaType')

    case 'file_too_large':
      return translate('newJob.file.validation.fileTooLarge', {
        maxSize: formatFileSize(
          validation.maxUploadBytes ?? environment.maxUploadBytes,
        ),
      })
  }
}
