# API Plan

## Purpose

`src/app/api` is the HTTP boundary of the product. It authenticates requests,
validates HTTP-specific input, calls application services, and returns stable,
safe response schemas.

The API process submits and reads jobs. It never executes transcription, copy
analysis, copy adaptation, FFmpeg, or LLM work. Celery workers execute those
operations in a separate process.

```text
Browser
   |
   v
FastAPI -> PipelineService -> JobStore + Storage -> CeleryQueue
                                                      |
                                                      v
                                                Celery worker
                                                      |
                                                      v
                                             workflows + JobStore
```

The API must not implement SQL statements, storage backend logic, Celery task
bodies, workflow logic, or provider construction. Those responsibilities
already belong to `app.store`, `app.storage`, `app.queue`, `app.pipeline`,
`app.worker`, and `app.providers`.

## Initial Scope

The first API version exposes only:

```text
GET  /health
POST /v1/jobs
GET  /v1/jobs/{job_id}
GET  /v1/jobs/{job_id}/result
```

The initial upload path uses `LocalStorage`: the browser sends the media file to
the API, and the API passes its stream to `PipelineService.start_from_upload`.
Direct browser uploads to S3, R2, or GCP are a later transport option and do not
replace or invalidate this local-storage submission flow.

Exports, cancellation, live progress streaming, billing routes, OAuth routes,
and direct-to-cloud upload routes are outside this package milestone.

## Dependency Order

Modules must be implemented according to their imports, not according to their
position in the package tree.

```text
settings --> app.schemas/jobs.py --------------------+
        \--> uploads.py -----------------------------+--> routers/jobs.py
        \--> lifespan.py --> dependencies.py --------+

app errors --> exception_handlers.py ----------------+

app.auth principal/dependency --> dependencies.py ---+

middleware.py ---------------------------------------+

health router + jobs router + handlers + middleware + lifespan
        |
        v
      main.py
        |
        v
    api/__init__.py
```

`main.py` is composition code and must be created only after every module it
imports exists. `api/__init__.py` is last because it exports `create_app` from
`main.py` and therefore imports the complete API graph.

## Package Structure

```text
src/app/api/
  __init__.py
  lifespan.py
  dependencies.py
  exception_handlers.py
  middleware.py
  uploads.py
  main.py

  routers/
    __init__.py
    health.py
    jobs.py

src/app/schemas/
  __init__.py
  jobs.py
```

## Module Responsibilities

The following order is also the required implementation order inside the API
package.

### `app.schemas/jobs.py`

Define HTTP contracts and pure mapping functions. Do not expose
`PipelineInput`, SQLAlchemy models, storage paths, provider credentials, or
technical exceptions as HTTP schemas.

Required request schemas:

- `CreateCopyAnalysisJobRequest`;
- `CreateCopyAdaptationJobRequest`;
- a discriminated union using `pipeline_type`;
- adaptation requires `user_profile`;
- analysis must not accept or require `user_profile`.

Required response schemas:

- `JobSubmissionResponse`;
- `JobStatusResponse`;
- `JobResultResponse`;
- `ApiErrorResponse`.

Required pure helpers:

- parse the multipart `request` JSON string using Pydantic;
- apply explicit API defaults from `AppSettings` when provider or model fields
  are omitted;
- map HTTP requests to `app.schemas.pipeline` inputs;
- map persisted jobs to safe response schemas;
- exclude `input_file_key`, `input_file_uri`, local paths, raw input JSON, and
  `technical_message` from every public response.

`app.schemas.__init__` may export only the stable schemas and mapper types used
by application modules, routers, and tests.

### `uploads.py`

Own HTTP upload validation before the stream reaches `PipelineService`.

Responsibilities:

- require a non-empty client filename;
- reject unsupported media types using the configured allowlist;
- reject an empty upload;
- enforce `max_upload_bytes` using the actual uploaded stream size, not only a
  client-provided `Content-Length` header;
- rewind the file before passing `UploadFile.file` to the pipeline;
- never load the complete media file into memory.

The reverse proxy and ASGI deployment must enforce the same body-size policy.
Application validation is not a substitute for an ingress limit.

FFmpeg or ffprobe remains authoritative for media readability and duration.
Filename extensions and MIME types are only preliminary checks.

### `exception_handlers.py`

Register controlled exception handlers through one public function:

```python
install_exception_handlers(app: FastAPI) -> None
```

Responsibilities:

- convert `AppError` through `error.to_dict()`;
- convert FastAPI/Pydantic request-validation failures to the same public error
  shape;
- log unexpected exceptions with request context;
- return a generic internal error without exposing stack traces, local paths,
  SQL errors, API keys, provider responses, or `technical_message`.

Required controlled error distinctions must exist in `app.errors` before this
module is implemented:

- upload too large -> `413`;
- unsupported media -> `415`;
- invalid request or pipeline input -> `422`;
- job absent or not owned by the current user -> `404`;
- result requested before completion -> `409`;
- unavailable broker, storage, or database dependency -> `503` when the error
  is retryable;
- unexpected or non-retryable infrastructure failure -> `500`.

Do not infer HTTP status from translated text or `technical_message`. Map stable
exception classes or error codes.

### `middleware.py`

Own request-level HTTP behavior shared by all routers.

Initial responsibility:

- accept a valid incoming `X-Request-ID` or generate a new identifier;
- make the identifier available to logs and exception handlers;
- return it in the response header;
- never use authorization tokens, filenames, or user input as a request id.

CORS is configured in `main.py` because it depends on application settings and
FastAPI middleware registration.

### `routers/health.py`

Expose `GET /health` as a liveness endpoint.

It verifies only that the API process can answer HTTP requests. It must not call
the database, broker, storage, transcribers, LLMs, or workflows.

A readiness endpoint may be added later for deployment-specific dependency
checks. Do not turn liveness into readiness accidentally.

`routers/__init__.py` should remain empty or expose only stable router objects.
It must not build the FastAPI application.

### Authentication Prerequisite

Production job routes require an authentication contract from `app.auth`
before `dependencies.py` and `routers/jobs.py` are completed.

The contract must return an authenticated principal containing the application
`user_id`. The API must not receive `user_id` from form data, JSON, headers
invented by the client, or query parameters.

`app.auth` must not import `app.api`; dependency direction is one-way:

```text
app.api -> app.auth
```

Tests may override the authentication dependency. A hardcoded development user
or unauthenticated production fallback is prohibited.

Authentication endpoints and Google OAuth implementation belong to the auth
milestone. They are not to be improvised inside the jobs router.

### `lifespan.py`

Own reusable infrastructure created by the API process.

Settings must be resolved exactly once by `create_app` and made available to
the lifespan. This is necessary because CORS is configured while the FastAPI
application is being built, before startup begins. The lifespan must reuse the
same `AppSettings` instance instead of calling `load_settings()` again.

At startup:

1. read the already-resolved settings from application state or a lifespan
   factory closure;
2. create one async SQLAlchemy engine;
3. create one `SessionFactory` from that engine;
4. create the configured `StorageBase`;
5. create the `QueueBase` adapter for the public Celery task;
6. store reusable resources in `app.state`.

At shutdown:

1. dispose the SQLAlchemy engine;
2. close only resources created and owned by the API process.

If startup fails after the engine is created, the engine must still be
disposed. Do not run Alembic migrations, start Celery workers, submit jobs, or
execute workflows during startup.

Never store an `AsyncSession` in `app.state`. Sessions are request-scoped.

The Celery decorator may be typed by static analyzers as a plain function even
though it produces an object with `.delay()` at runtime. Keep any required
`cast(CeleryTask, run_pipeline_job)` at this integration boundary and remove
unused type imports.

### `dependencies.py`

Provide typed FastAPI dependencies after lifespan and authentication contracts
exist.

Required dependencies:

- `get_settings`: return the resolved `AppSettings` from `app.state`;
- `get_session_factory`: return the application `SessionFactory`;
- `get_storage`: return `StorageBase`;
- `get_queue`: return `QueueBase`;
- `get_session`: yield one request-scoped `AsyncSession` for read operations;
- `get_job_store`: build a `JobStoreBase` over the request-scoped session;
- `get_pipeline_service`: build `PipelineService` using
  `PipelineJobStore(SessionFactory)`, storage, and queue;
- `get_current_user`: consume the production principal supplied by `app.auth`.

The read store uses a request-scoped session. `PipelineService` uses the
transaction-aware `PipelineJobStore`, which opens short independent
transactions for submission checkpoints.

Do not open one transaction around file upload or queue submission.

### `routers/jobs.py`

Own only HTTP concerns for job submission and retrieval.

The router may call application/store contracts returned by dependencies, but
must not write SQL, instantiate `WorkerRunner`, call workflows, construct
storage keys, call Celery tasks directly, or import concrete storage backends.

#### `POST /v1/jobs`

Use `multipart/form-data`:

- `file`: required `UploadFile`;
- `request`: required JSON string parsed as the discriminated request union;
- `Idempotency-Key`: optional header mapped to `run_id` when the request does
  not already provide one.

Processing order:

1. authenticate the user;
2. parse and validate request metadata;
3. validate and rewind the uploaded file;
4. map the HTTP request to a normalized pipeline input;
5. call `PipelineService.start_from_upload` with the authenticated user id,
   client filename, stream, and pipeline input;
6. return `202 Accepted` with `JobSubmissionResponse`.

Analysis sends no `user_profile`. Adaptation requires it. The route does not
accept server filesystem paths.

#### `GET /v1/jobs/{job_id}`

Load the job through `JobStoreBase`, verify that `job.user_id` matches the
authenticated principal, and return:

```text
job_id
run_id
pipeline_type
status
current_step
created_at
started_at
finished_at
execution_time_seconds
error (only when failed)
```

An absent job and a job belonging to another user both return the same `404`
response. This prevents ownership probing.

#### `GET /v1/jobs/{job_id}/result`

Return persisted `output_json` only when the owned job is `completed`.

- `pending`, `uploaded`, or `running` -> controlled `409`;
- `failed` -> safe persisted failure payload;
- absent or foreign job -> `404`.

Never return full internal input JSON, local storage paths, raw provider
configuration, or another user's identifiers.

### `main.py`

Create `create_app(settings: AppSettings | None = None) -> FastAPI` only after
lifespan, handlers, middleware, and both routers exist.

Responsibilities:

1. resolve settings once, allowing explicit settings injection in tests;
2. create the FastAPI application with the lifespan;
3. store the resolved settings for lifespan and dependencies;
4. configure CORS from the explicit `api_cors_origins` allowlist;
5. install request-id middleware;
6. install exception handlers;
7. include health and jobs routers;
8. return the configured application.

The module-level ASGI object may then be defined as:

```python
app = create_app()
```

Application construction may read and validate environment configuration, but
must not connect to the database or broker, initialize storage clients, submit
jobs, execute workflows, or start a worker.

`api_host` and `api_port` configure the Uvicorn process or deployment command;
they are not route settings.

### `__init__.py`

Implement last. Export only:

```python
create_app
```

Do not export routers, dependencies, sessions, concrete stores, storage
backends, Celery tasks, or the module-level `app` object from the package root.

## Transaction And Queue Invariants

Submission order is mandatory:

```text
validate request
    -> create pending job and commit
    -> stream file into storage
    -> mark uploaded and commit
    -> enqueue only job_id
```

If upload, transition, or enqueue fails, persist `failed` in a new transaction
when possible. Never enqueue before the `uploaded` commit is visible. The API
must not hold an `AsyncSession` transaction while receiving or saving a large
file, and it must not wait for the worker result.

## Configuration

Runtime dependencies:

```text
fastapi
uvicorn[standard]
python-multipart
```

Required API settings:

- `api_host`;
- `api_port`;
- `api_cors_origins` as an explicit allowlist;
- `max_upload_bytes`;
- `api_upload_timeout_seconds`;
- `accepted_input_media_types`.

An empty CORS list is valid for same-origin or non-browser clients. Do not use a
wildcard origin with authenticated requests.

## Result And Progress Contract

The initial frontend polls `GET /v1/jobs/{job_id}` using `status` and
`current_step`. The API reads persisted state; it does not query Celery's result
backend or LangGraph checkpoints.

A future timeline endpoint may expose stable product-level `job_events`. Do not
persist one event per LLM token, FFmpeg line, or log record.

## Logging And Privacy

- include request id, route, controlled error code, authenticated user id, and
  job id when available;
- never log authorization headers, passwords, API keys, complete media,
  complete transcripts, or complete user profiles by default;
- never expose `technical_message`, stack traces, SQL errors, provider bodies,
  local paths, or private storage URIs;
- let the frontend translate stable public error codes.

## Tests

Create tests beside the implementation stages:

```text
tests/unit/app/api/
  test_api_schemas.py
  test_api_uploads.py
  test_api_exception_handlers.py
  test_api_middleware.py
  test_api_health.py
  test_api_lifespan.py
  test_api_dependencies.py
  test_api_jobs.py
  test_api_main.py
  test_api_public_api.py

tests/integration/app/api/
  test_api_jobs_integration.py
```

Unit tests use dependency overrides and fakes. They must not open a real
database, contact a broker, execute Celery tasks, run workflows, call FFmpeg,
or contact remote providers.

Integration tests use a migrated temporary database, real `LocalStorage`, and
a fake queue. They must verify:

- valid analysis upload returns `202` and queues one persisted uploaded job;
- valid adaptation upload persists `user_profile` safely;
- upload and queue failures persist `failed` when possible;
- the uploaded transition is committed before queue invocation;
- local storage paths never appear in responses;
- one user cannot read another user's job or result;
- incomplete result requests return `409`;
- public errors follow the stable error schema.

## Exact Construction Order

Follow this order. Do not build `main.py` early with imports for files that do
not exist yet.

1. Verify `PipelineJobStore` and the submission transaction tests are complete.
2. Add FastAPI, Uvicorn, and multipart dependencies.
3. Add and validate API upload/CORS settings.
4. Add the missing stable `AppError` subclasses/codes required for `413`,
   `404`, and `409` behavior.
5. Implement `app.schemas/jobs.py`, update `app.schemas/__init__.py`, and add
   schema tests.
6. Implement `uploads.py` and upload tests.
7. Implement `exception_handlers.py` and handler tests.
8. Implement `middleware.py` and request-id tests.
9. Implement `routers/health.py`, `routers/__init__.py`, and health tests.
10. Complete the production authentication principal/dependency in `app.auth`.
11. Implement or adjust `lifespan.py` so it reuses the settings resolved by the
    app factory; add lifespan tests.
12. Implement `dependencies.py` and dependency tests.
13. Implement `routers/jobs.py` and router unit tests.
14. Implement `main.py` and application composition tests.
15. Implement `api/__init__.py` and public API tests.
16. Run API integration tests with a real temporary database, `LocalStorage`,
    and a fake queue.
17. Run one end-to-end environment with API, RabbitMQ, Celery worker, database,
    local storage, and a real media file.

## Definition Of Done

The API foundation is complete when:

- `create_app` imports without connecting to infrastructure;
- settings are resolved once and shared by CORS, lifespan, and dependencies;
- startup creates reusable resources and shutdown disposes owned resources;
- `POST /v1/jobs` returns only after upload is durable and the job is queued;
- API and Celery worker execute in separate processes;
- every job read enforces authenticated ownership;
- API responses never expose local paths or technical errors;
- result retrieval reads `jobs.output_json`, not workflow/checkpoint state;
- unit, integration, and one real end-to-end submission pass.
