# Pipeline Unit Tests

Unit tests for `src/app/pipeline` must stay isolated from real database,
storage, queue, API, and workflow execution.

Use fakes for `JobStoreBase`, `StorageBase`, and `QueueBase`.

## `test_pipeline_input.py`

Status: Done.

Purpose: verify input validation and normalization before the pipeline touches
storage, store, or queue.

Tests:

- `test_normalize_copy_analysis_input`
- `test_normalize_copy_adaptation_input`
- `test_rejects_invalid_source_type`
- `test_rejects_missing_required_provider_or_model`
- `test_rejects_unsupported_llm_provider`
- `test_rejects_unsupported_transcriber_provider`
- `test_rejects_non_positive_max_duration`
- `test_normalizes_output_formats_and_aliases`

## `test_pipeline_files.py`

Status: Done.

Purpose: verify storage key generation and conversion from stored file to job
upload payload.

Tests:

- `test_build_pipeline_input_key_uses_job_input_key`
- `test_save_pipeline_upload_calls_storage_save_upload`
- `test_save_pipeline_file_calls_storage_save_file`
- `test_pipeline_input_file_returns_job_payload`
- `test_stored_file_to_job_payload_returns_expected_fields`

## `test_pipeline_jobs.py`

Status: Done.

Purpose: verify payload construction and store calls without using a real
database.

Tests:

- `test_build_create_job_payload_for_copy_analysis`
- `test_build_create_job_payload_for_copy_adaptation`
- `test_build_input_json_is_json_serializable`
- `test_create_pipeline_job_calls_job_store_create_job`
- `test_mark_pipeline_job_uploaded_calls_job_store_mark_uploaded`
- `test_mark_pipeline_job_failed_calls_job_store_mark_failed`
- `test_rejects_invalid_user_id`

## `test_pipeline_service.py`

Status: Done.

Purpose: verify orchestration order and failure behavior using fake store,
storage, and queue implementations.

Tests:

- `test_start_from_upload_creates_job_saves_file_marks_uploaded_and_enqueues`
- `test_start_from_file_creates_job_saves_file_marks_uploaded_and_enqueues`
- `test_start_from_upload_returns_pipeline_start_result`
- `test_marks_job_failed_when_upload_fails_after_job_creation`
- `test_marks_job_failed_when_mark_uploaded_fails`
- `test_marks_job_failed_when_enqueue_fails`
- `test_enqueue_failure_is_re_raised`

## `test_pipeline_public_api.py`

Status: Done.

Purpose: keep `app.pipeline` public exports explicit and stable.

Tests:

- `test_public_api_exports_expected_symbols`
- `test_public_api_imports_without_circular_imports`
