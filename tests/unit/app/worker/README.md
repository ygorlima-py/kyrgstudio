# Worker Unit Tests

Unit tests for `src/app/worker` must stay isolated from real database,
storage, Celery brokers, FFmpeg, transcription providers, and LLM providers.

Use fakes for worker stores, file resolvers, workflow executors, and workflow
factories.

## `test_worker_runner.py`

Status: Done.

Purpose: verify persisted job execution, state transitions, failure handling,
and cleanup without executing real workflows.

Tests:

- `test_rejects_invalid_job_id`
- `test_rejects_job_not_found`
- `test_rejects_job_not_uploaded`
- `test_marks_job_running_before_workflow_execution`
- `test_builds_workflow_execution_request`
- `test_persists_serializable_output_and_execution_time_on_success`
- `test_persists_controlled_error_on_workflow_failure`
- `test_preserves_original_error_when_mark_failed_fails`
- `test_cleans_materialized_file_on_success`
- `test_cleans_materialized_file_on_failure`
- `test_deletes_job_prefix_on_success`
- `test_deletes_job_prefix_on_failure`

## `test_worker_workflows.py`

Status: Done.

Purpose: verify workflow selection, input validation, result normalization,
and token aggregation using fake `kyrg` workflows and providers.

Tests:

- `test_selects_copy_analysis_workflow`
- `test_selects_copy_adaptation_workflow`
- `test_rejects_missing_required_input_json_fields`
- `test_normalizes_transcriber_copy_analysis_and_copy_adaptation_results`
- `test_aggregates_token_usage_by_stage`

## `test_worker_tasks.py`

Status: Done.

Purpose: verify that the public Celery task accepts only a persisted job
identifier and delegates execution through the asynchronous worker boundary.

Tests:

- `test_run_pipeline_job_accepts_only_job_id`

## `test_worker_celery_app.py`

Status: Done.

Purpose: verify Celery configuration remains import-safe and rejects invalid
broker configuration through a controlled application error.

Tests:

- `test_importing_celery_app_does_not_execute_workflows`
- `test_rejects_missing_celery_broker_url`
