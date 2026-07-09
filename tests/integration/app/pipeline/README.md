# Pipeline Integration Tests

Integration tests for `src/app/pipeline` must verify the pipeline service
working with real app infrastructure boundaries:

- real database session and app store;
- real local storage directory;
- real `InlineQueue`;
- real file saved to disk;
- no real API server;
- no real workflow execution;
- no remote provider calls.

The goal is to prove that the pipeline can create a job, persist the uploaded
file reference, enqueue the job id, and make the stored job readable after the
operation.

## Test Layout

```text
tests/integration/app/pipeline/
  README.md
  conftest.py
  test_pipeline_service_integration.py
```

## Fixtures

### `database_url`

Use the same integration database strategy already used by app store tests.

Rules:

- skip tests when no integration database URL is configured;
- do not use production database URLs;
- each test must isolate its data.

### `session`

Provide a real SQLAlchemy `AsyncSession`.

Rules:

- use explicit transaction boundaries;
- rollback or clean up after each test;
- do not let pipeline tests depend on store test data.

### `app_store`

Create a real `AppStore` from the session using `create_store(session)`.

The pipeline service should receive `app_store.jobs`.

### `local_storage`

Create a real `LocalStorage` pointing to a temporary directory.

Rules:

- use `tmp_path`;
- assert the stored file physically exists;
- remove temporary files automatically through pytest temp directory cleanup.

### `inline_queue`

Create an `InlineQueue` with a small async handler that records received job ids.

The handler must not execute workflows.

Example behavior:

```text
queued_job_ids.append(job_id)
```

## `test_pipeline_service_integration.py`

Status: Done.

Purpose: verify the complete app-level startup flow with real database, real
local storage, and real inline queue.

Tests:

- `test_start_from_file_creates_job_saves_local_file_marks_uploaded_and_enqueues`
  - create a real user in the database;
  - create a temporary input file;
  - call `PipelineService.start_from_file(...)`;
  - assert a real job was created;
  - assert the local storage file exists;
  - assert job status is `uploaded`;
  - assert `storage_backend`, `input_file_key`, and `input_file_uri` were saved;
  - assert `InlineQueue` handler received the job id;
  - reload the job from store and assert persisted status.

- `test_start_from_upload_creates_job_saves_local_upload_marks_uploaded_and_enqueues`
  - create a real user in the database;
  - pass `BytesIO` as uploaded file;
  - call `PipelineService.start_from_upload(...)`;
  - assert local storage contains the uploaded bytes;
  - assert job status is `uploaded`;
  - assert queue received the job id.

- `test_pipeline_service_marks_job_failed_when_inline_queue_fails`
  - create a real user in the database;
  - use real local storage;
  - use a queue fake or inline handler that raises;
  - assert the original queue error is raised;
  - reload the job from store;
  - assert job status is `failed`;
  - assert `error_json.code` is `pipeline_execution_failed`.

## Out Of Scope

These tests must not execute:

- transcriber workflow;
- copy analysis workflow;
- copy adaptation workflow;
- Celery worker;
- external storage backends;
- remote LLM or transcription providers;
- HTTP API routes.

Those belong to worker, workflow, storage backend, provider, or API integration
tests.
