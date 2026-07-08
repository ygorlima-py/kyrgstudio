# Unit Tests For App Layer

This document plans the unit test coverage for the application layer.

The first focus is `src/app/store`, because it is the persistence boundary used
by the API, worker, queue, and pipeline orchestration layers.

Unit tests in this folder must not require a real database server. They should
validate pure behavior, contracts, payload validation, factory wiring, and SQL
statement construction where possible. Tests that require an actual database,
transactions, migrations, or SQLAlchemy engine behavior belong in
`tests/integration/app/store`.

## Store Unit Test Strategy

`src/app/store` has three responsibilities:

- define stable contracts for persistence operations;
- define SQLAlchemy models and metadata;
- implement store classes that receive an active `AsyncSession` and perform
  database operations without owning commit or rollback.

The unit tests should verify these responsibilities without coupling to a real
Postgres instance.

## Test Modules

### `test_store_models.py`

Status: Pending.

Purpose: verify that SQLAlchemy model metadata matches the planned database
contract.

Tests:

- `test_users_table_name_and_columns`
  - Assert table name is `users`.
  - Assert required columns exist: `id`, `email`, `password_hash`, `name`,
    `avatar_url`, `auth_provider`, `google_sub`, `email_verified_at`,
    `created_at`, `updated_at`, `disabled_at`.

- `test_users_email_is_unique_and_uses_expected_length`
  - Assert `email` is unique.
  - Assert `email` uses length `320`.

- `test_users_google_sub_is_unique_and_indexed`
  - Assert `google_sub` is unique.
  - Assert the model has an index for `google_sub`.

- `test_users_password_hash_is_nullable_for_oauth_users`
  - Assert `password_hash` is nullable.

- `test_billing_customers_table_name_and_columns`
  - Assert table name is `billing_customers`.
  - Assert required columns exist: `id`, `user_id`, `stripe_customer_id`,
    `created_at`, `updated_at`.

- `test_billing_customers_constraints`
  - Assert `user_id` is unique and indexed.
  - Assert `stripe_customer_id` is unique and indexed.
  - Assert `user_id` has foreign key to `users.id`.

- `test_subscriptions_table_name_and_columns`
  - Assert table name is `subscriptions`.
  - Assert required columns exist: `id`, `user_id`, `stripe_customer_id`,
    `stripe_subscription_id`, `stripe_price_id`, `status`, `plan`,
    `current_period_start`, `current_period_end`, `cancel_at_period_end`,
    `created_at`, `updated_at`.

- `test_subscriptions_customer_id_is_indexed_but_not_unique`
  - Assert `stripe_customer_id` is indexed.
  - Assert `stripe_customer_id` is not unique.

- `test_subscriptions_subscription_id_is_unique`
  - Assert `stripe_subscription_id` is unique.

- `test_billing_events_table_name_and_columns`
  - Assert table name is `billing_events`.
  - Assert required columns exist: `id`, `stripe_event_id`, `event_type`,
    `payload_json`, `processed_at`, `created_at`.

- `test_billing_events_idempotency_constraints`
  - Assert `stripe_event_id` is unique.
  - Assert `event_type` is indexed.
  - Assert `created_at` is indexed.

- `test_jobs_table_name_and_columns`
  - Assert table name is `jobs`.
  - Assert required columns exist: `id`, `user_id`, `run_id`, `status`,
    `current_step`, `pipeline_type`, `input_json`, `storage_backend`,
    `input_file_key`, `input_file_uri`, `audio_file_key`, `audio_file_uri`,
    `output_json`, `error_json`, `token_usage_json`,
    `execution_time_seconds`, `created_at`, `updated_at`, `started_at`,
    `finished_at`.

- `test_jobs_indices_and_uniques`
  - Assert `user_id`, `status`, and `created_at` are indexed.
  - Assert `run_id` is unique.

- `test_job_events_table_name_and_columns`
  - Assert table name is `job_events`.
  - Assert required columns exist: `id`, `job_id`, `step`, `event_type`,
    `payload_json`, `created_at`.

- `test_job_events_has_compound_index_for_history_lookup`
  - Assert compound index exists for `(job_id, created_at)`.

- `test_model_metadata_contains_all_store_tables`
  - Assert `Base.metadata.tables` contains `users`, `billing_customers`,
    `subscriptions`, `billing_events`, `jobs`, and `job_events`.

### `test_store_base.py`

Status: Pending.

Purpose: verify that store interfaces expose the expected contracts.

Tests:

- `test_job_store_base_declares_required_methods`
  - Assert `JobStoreBase` has `create_job`, `mark_uploaded`, `mark_running`,
    `mark_step_completed`, `mark_completed`, `mark_failed`, `get_job`,
    `get_job_by_run_id`, and `list_user_jobs` as abstract methods.

- `test_user_store_base_declares_required_methods`
  - Assert `UserStoreBase` has `create_user`, `get_user`,
    `get_user_by_email`, and `get_user_by_google_sub` as abstract methods.

- `test_billing_store_base_declares_required_methods`
  - Assert `BillingStoreBase` has `set_stripe_customer`,
    `upsert_subscription`, `record_billing_event`, and
    `get_subscription_by_user_id` as abstract methods.

- `test_concrete_stores_implement_abstract_contracts`
  - Assert `SQLAlchemyJobStore`, `SQLAlchemyUserStore`, and
    `SQLAlchemyBillingStore` are instantiable with a fake session object if the
    constructors only assign the session.

### `test_store_factory.py`

Status: Pending.

Purpose: verify that the factory wires concrete stores correctly without opening
connections or owning transactions.

Tests:

- `test_create_store_returns_app_store`
  - Pass a fake session object.
  - Assert `create_store` returns `AppStore`.

- `test_create_store_uses_same_session_for_all_stores`
  - Assert `store.jobs.session`, `store.users.session`, and
    `store.billing.session` reference the exact same session object.

- `test_create_store_returns_contract_typed_stores`
  - Assert `store.jobs` is a `JobStoreBase`.
  - Assert `store.users` is a `UserStoreBase`.
  - Assert `store.billing` is a `BillingStoreBase`.

- `test_app_store_is_frozen`
  - Assert assigning a new store to `AppStore.jobs` raises an error.

### `test_store_database.py`

Status: Pending.

Purpose: verify database configuration and helper behavior that does not require
opening a real database connection.

Tests:

- `test_database_config_from_settings_reads_expected_fields`
  - Use a simple settings object.
  - Assert `DatabaseConfig.from_settings` maps URL, echo, pool size,
    max overflow, and pool pre-ping correctly.

- `test_database_config_rejects_missing_database_url`
  - Assert missing URL raises `StoreError`.

- `test_validate_async_database_url_accepts_postgresql_asyncpg`
  - Assert `postgresql+asyncpg://...` passes.

- `test_validate_async_database_url_accepts_sqlite_aiosqlite`
  - Assert `sqlite+aiosqlite:///...` passes.

- `test_validate_async_database_url_rejects_sync_postgres_driver`
  - Assert `postgresql://...` raises `StoreError`.

- `test_validate_async_database_url_rejects_sync_sqlite_driver`
  - Assert `sqlite:///...` raises `StoreError`.

- `test_create_async_engine_from_config_uses_sqlite_safe_kwargs`
  - Monkeypatch SQLAlchemy `create_async_engine`.
  - Assert SQLite config does not pass Postgres pool kwargs.

- `test_create_async_engine_from_config_uses_postgres_pool_kwargs`
  - Monkeypatch SQLAlchemy `create_async_engine`.
  - Assert Postgres config passes `pool_pre_ping`, `pool_size`, and
    `max_overflow`.

- `test_create_async_session_factory_uses_expire_on_commit_false`
  - Monkeypatch or inspect factory configuration where possible.
  - Assert session factory is configured for app store behavior.

### `test_store_jobs.py`

Status: Pending.

Purpose: verify job store payload validation, transition statement intent, and
error behavior without requiring a real database.

Tests:

- `test_create_job_requires_user_id`
  - Missing `user_id` raises `JobStoreError`.

- `test_create_job_requires_pipeline_type`
  - Missing `pipeline_type` raises `JobStoreError`.

- `test_create_job_requires_input_json_object`
  - Non-object `input_json` raises `JobStoreError`.

- `test_create_job_normalizes_blank_run_id_to_none`
  - Use a fake session/savepoint strategy if feasible.
  - Assert blank `run_id` does not persist as empty string.

- `test_mark_uploaded_requires_storage_backend_and_input_file_references`
  - Missing `storage_backend`, `input_file_key`, or `input_file_uri` raises
    `JobStoreError`.

- `test_mark_running_rejects_invalid_transition_when_update_returns_no_row`
  - Fake session execute returning no row.
  - Assert `JobStoreError`.

- `test_mark_completed_uses_running_as_allowed_status`
  - Inspect the call to the transition helper or fake session statement.
  - Assert only `running` is accepted.

- `test_mark_failed_accepts_pending_uploaded_and_running`
  - Inspect transition call.
  - Assert allowed statuses are `pending`, `uploaded`, and `running`.

- `test_list_user_jobs_rejects_non_positive_limit`
  - Assert zero or negative limit raises `JobStoreError`.

- `test_list_user_jobs_caps_limit_to_maximum`
  - Assert limit above max becomes `MAX_PAGE_LIMIT`.

- `test_list_user_jobs_rejects_negative_offset`
  - Assert negative offset raises `JobStoreError`.

- `test_get_job_returns_none_when_session_get_returns_none`
  - Fake session get returns `None`.
  - Assert method returns `None`.

- `test_sqlalchemy_errors_are_wrapped_as_job_store_error`
  - Fake session raises `SQLAlchemyError`.
  - Assert `JobStoreError` includes operation details.

### `test_store_users.py`

Status: Pending.

Purpose: verify user store payload validation and normalization without requiring
a real database.

Tests:

- `test_create_user_requires_email`
  - Missing or blank email raises `UserStoreError`.

- `test_create_user_rejects_invalid_email`
  - Email without `@` raises `UserStoreError`.

- `test_create_user_normalizes_email_to_lowercase`
  - Input `USER@EXAMPLE.COM` becomes `user@example.com`.

- `test_create_password_user_requires_password_hash`
  - `auth_provider=password` with no `password_hash` raises `UserStoreError`.

- `test_create_google_user_requires_google_sub`
  - `auth_provider=google` with no `google_sub` raises `UserStoreError`.

- `test_create_google_user_allows_null_password_hash`
  - OAuth user can be built without local password hash.

- `test_get_user_by_email_normalizes_email_before_query`
  - Fake session captures query intent or helper behavior.

- `test_get_user_by_google_sub_rejects_blank_google_sub`
  - Blank Google subject raises `UserStoreError`.

- `test_update_password_hash_rejects_blank_hash`
  - Blank password hash raises `UserStoreError`.

- `test_mark_email_verified_updates_with_database_time`
  - Fake update path verifies method delegates to update helper.

- `test_sqlalchemy_errors_are_wrapped_as_user_store_error`
  - Fake session raises `SQLAlchemyError`.
  - Assert `UserStoreError`.

### `test_store_billing.py`

Status: Pending.

Purpose: verify billing store validation, idempotency result semantics, and
customer/subscription boundaries without requiring a real database.

Tests:

- `test_set_stripe_customer_requires_positive_user_id`
  - Zero, negative, bool, float, and non-numeric values raise
    `BillingStoreError`.

- `test_set_stripe_customer_requires_customer_prefix`
  - Customer id must start with `cus_`.

- `test_set_stripe_customer_updates_existing_customer_for_user`
  - Fake `get_billing_customer_by_user_id` returns an existing customer.
  - Assert update path is used.

- `test_set_stripe_customer_rejects_customer_linked_to_other_user`
  - Simulate conflict by customer id.
  - Assert `BillingStoreError`.

- `test_upsert_subscription_requires_customer_prefix`
  - `stripe_customer_id` must start with `cus_`.

- `test_upsert_subscription_requires_subscription_prefix`
  - `stripe_subscription_id` must start with `sub_`.

- `test_upsert_subscription_uses_subscription_id_as_identity`
  - Existing subscription should be resolved by `stripe_subscription_id`, not by
    customer id.

- `test_upsert_subscription_rejects_customer_conflict_with_different_subscription`
  - Simulate unique conflict on customer id.
  - Assert store raises controlled `BillingStoreError` instead of overwriting
    subscription identity.

- `test_record_billing_event_requires_event_prefix`
  - `stripe_event_id` must start with `evt_`.

- `test_record_billing_event_returns_should_process_true_for_new_event`
  - New insert returns `BillingEventRecordResult(created=True,
    should_process=True)`.

- `test_record_billing_event_returns_should_process_false_for_duplicate_event`
  - Duplicate event returns existing event with `created=False` and
    `should_process=False`.

- `test_mark_billing_event_processed_requires_event_prefix`
  - Invalid event id raises `BillingStoreError`.

- `test_mark_subscription_canceled_requires_subscription_prefix`
  - Invalid subscription id raises `BillingStoreError`.

- `test_get_active_subscription_uses_active_and_trialing_statuses`
  - Verify active subscription statuses are `active` and `trialing`.

- `test_sqlalchemy_errors_are_wrapped_as_billing_store_error`
  - Fake session raises `SQLAlchemyError`.
  - Assert `BillingStoreError`.

## Integration Tests That Must Not Be Placed Here

The following tests require a real database or migration environment and must be
implemented in `tests/integration/app/store`:

- creating all tables from Alembic migrations;
- applying first migration from an empty database;
- creating a user and reading it back;
- enforcing unique email;
- enforcing unique `billing_customers.user_id`;
- enforcing unique `billing_customers.stripe_customer_id`;
- allowing multiple subscriptions for the same `stripe_customer_id`;
- enforcing unique `subscriptions.stripe_subscription_id`;
- recording duplicate Stripe event only once;
- executing job status transitions with real SQL `RETURNING`;
- rolling back failed transactions;
- validating `async_savepoint_scope` behavior with unique constraint conflicts;
- verifying indexes exist in the migrated database.

## Current Priority

Build unit tests in this order:

1. `test_store_models.py`
2. `test_store_factory.py`
3. `test_store_database.py`
4. `test_store_users.py`
5. `test_store_billing.py`
6. `test_store_jobs.py`
7. `test_store_base.py`

This order gives fast feedback on schema and wiring first, then validates domain
store behavior.
