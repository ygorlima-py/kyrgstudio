import { describe, expect, it } from 'vitest'

import { normalizePersuasionStrength } from '@/features/copy-analysis'

describe('normalizePersuasionStrength', () => {
  it('separates a localized rating from an explanation', () => {
    expect(
      normalizePersuasionStrength('Media. El único elemento de prueba es el testimonio de Carol.'),
    ).toEqual({
      level: 'medium',
      explanation: 'El único elemento de prueba es el testimonio de Carol.',
    })
  })

  it('keeps a plain rating without creating an explanation', () => {
    expect(normalizePersuasionStrength('high')).toEqual({
      level: 'high',
      explanation: null,
    })
  })

  it('does not expose an unknown long value as a rating label', () => {
    expect(normalizePersuasionStrength('A custom explanation without a rating.')).toEqual({
      level: 'unknown',
      explanation: 'A custom explanation without a rating.',
    })
  })
})
