import {
  clearJobFormDraft,
  loadJobFormDraft,
  saveJobFormDraft,
} from '@/features/jobs/utils/job-form-draft'
import { beforeEach, describe, expect, it } from 'vitest'

describe('job form draft storage', () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it('saves and restores partial serializable form values', () => {
    const wasSaved = saveJobFormDraft(
      42,
      {
        pipeline_type: 'copy_adaptation',
        language: 'pt-BR',
        need_correction: true,
        user_profile: {
          product_or_solution: 'Training program',
          target_audience: 'Marketing professionals',
        },
      },
      'profile',
    )

    expect(wasSaved).toBe(true)
    expect(loadJobFormDraft(42)).toMatchObject({
      currentStepId: 'profile',
      values: {
        pipeline_type: 'copy_adaptation',
        language: 'pt-BR',
        need_correction: true,
        user_profile: {
          product_or_solution: 'Training program',
          target_audience: 'Marketing professionals',
        },
      },
    })
  })

  it('clears a saved draft', () => {
    saveJobFormDraft(
      42,
      {
        pipeline_type: 'copy_analysis',
        need_correction: false,
      },
      'settings',
    )

    clearJobFormDraft(42)

    expect(loadJobFormDraft(42)).toBeNull()
  })

  it('discards malformed browser data', () => {
    window.localStorage.setItem(
      'kyrg_job_creation_draft:42',
      JSON.stringify({ version: 1, values: 'invalid' }),
    )

    expect(loadJobFormDraft(42)).toBeNull()
    expect(window.localStorage.getItem('kyrg_job_creation_draft:42')).toBeNull()
  })

  it('keeps drafts isolated between authenticated users', () => {
    saveJobFormDraft(
      42,
      {
        pipeline_type: 'copy_analysis',
        language: 'pt-BR',
      },
      'settings',
    )

    expect(loadJobFormDraft(42)).not.toBeNull()
    expect(loadJobFormDraft(99)).toBeNull()
  })
})
