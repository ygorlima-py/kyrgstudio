# API Integration Tests

## `test_api_jobs_integration.py`

Status: Completed.

- submit a valid copy-analysis upload through the complete HTTP boundary;
- persist a copy-adaptation profile in normalized job input;
- persist controlled upload and queue failures;
- verify the uploaded transaction is committed before queue invocation;
- prevent local storage paths from appearing in public responses;
- hide jobs and results owned by another user;
- keep filtered job listings isolated to the authenticated user;
- reject result retrieval before completion;
- return completed persisted output through the result endpoint;
- preserve the stable public error contract.

The suite uses the migrated disposable database configured through
`APP_API_INTEGRATION_DATABASE_URL` or `APP_STORE_INTEGRATION_DATABASE_URL`,
real `LocalStorage`, the real pipeline service composition, authenticated
dependency overrides, and a fake queue. It does not run Celery, workflows,
FFmpeg, or remote providers.
