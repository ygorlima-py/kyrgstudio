import { useFormContext, useWatch } from 'react-hook-form'

import type { JobCreationFormInput } from '@/features/jobs/schemas/job-creation-schema'
import { Button } from '@/shared/ui/button'
import { FieldMessage } from '@/shared/ui/field-message'
import { Input } from '@/shared/ui/input'

type UserProfileListFieldName =
  | 'user_profile.benefits'
  | 'user_profile.objections'
  | 'user_profile.proof_assets'
  | 'user_profile.restrictions'

export interface RepeatableTextListProps {
  name: UserProfileListFieldName
  label: string
  description: string
  itemLabel: string
  addLabel: string
}

/**
 * Controls a repeatable list of text values inside the offer profile.
 *
 * The values remain string arrays, matching the backend contract directly.
 */
export function RepeatableTextList({
  addLabel,
  description,
  itemLabel,
  label,
  name,
}: RepeatableTextListProps) {
  const { control, setValue } =
    useFormContext<JobCreationFormInput>()

  const watchedItems = useWatch({
    control,
    name,
  })

  const items = Array.isArray(watchedItems)
    ? watchedItems
    : []

  function updateItems(nextItems: string[]) {
    setValue(name, nextItems, {
      shouldDirty: true,
      shouldTouch: true,
      shouldValidate: true,
    })
  }

  function addItem() {
    updateItems([...items, ''])
  }

  function updateItem(index: number, value: string) {
    updateItems(
      items.map((item, itemIndex) =>
        itemIndex === index ? value : item,
      ),
    )
  }

  function removeItem(index: number) {
    updateItems(
      items.filter((_, itemIndex) => itemIndex !== index),
    )
  }

  return (
    <fieldset className="space-y-4">
      <div className="space-y-1">
        <legend className="text-label text-text">
          {label}
        </legend>

        <FieldMessage>{description}</FieldMessage>
      </div>

      {items.length > 0 ? (
        <div className="space-y-3">
          {items.map((item, index) => (
            <div
              className="flex items-start gap-2"
              key={`${name}-${index}`}
            >
              <Input
                aria-label={`${itemLabel} ${index + 1}`}
                onChange={(event) => {
                  updateItem(index, event.currentTarget.value)
                }}
                placeholder={itemLabel}
                value={item}
              />

              <Button
                aria-label={`Remove ${itemLabel} ${index + 1}`}
                onClick={() => removeItem(index)}
                size="sm"
                type="button"
                variant="ghost"
              >
                Remove
              </Button>
            </div>
          ))}
        </div>
      ) : (
        <FieldMessage>No items added yet.</FieldMessage>
      )}

      <Button
        onClick={addItem}
        size="sm"
        type="button"
        variant="secondary"
      >
        {addLabel}
      </Button>
    </fieldset>
  )
}
