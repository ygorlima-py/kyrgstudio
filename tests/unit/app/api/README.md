# API Unit Tests

## `test_api_schemas.py`

Status: Completed.

- `test_parse_copy_analysis_job_request`
- `test_parse_copy_adaptation_job_request`
- `test_parse_job_request_rejects_invalid_json`
- `test_parse_job_request_rejects_unknown_pipeline_type`
- `test_parse_job_request_rejects_extra_fields`
- `test_build_analysis_pipeline_input_uses_settings_defaults`
- `test_build_adaptation_pipeline_input_uses_settings_defaults`
- `test_request_run_id_has_priority_over_idempotency_key`
- `test_idempotency_key_is_used_when_run_id_is_missing`
- `test_build_job_submission_response_hides_storage_references`
- `test_build_job_status_response_maps_public_fields`
- `test_build_failed_job_status_hides_internal_error_details`
- `test_build_job_result_response_requires_completed_job`
- `test_build_job_result_response_returns_only_public_output`

## `test_api_uploads.py`

Status: Completed.

- `test_validate_upload_returns_filename_content_type_size_and_stream`
- `test_validate_upload_normalizes_content_type`
- `test_validate_upload_rewinds_stream`
- `test_validate_upload_rejects_missing_filename`
- `test_validate_upload_rejects_unsupported_media_type`
- `test_validate_upload_rejects_empty_file`
- `test_validate_upload_rejects_file_above_actual_size_limit`
- `test_validate_upload_does_not_trust_content_length`
- `test_validate_upload_rejects_empty_media_type_configuration`
- `test_validate_upload_wraps_unreadable_stream_error`

## `test_api_exception_handlers.py`

Status: Completed.

- `test_install_exception_handlers_registers_expected_handlers`
- `test_authentication_errors_return_401_with_bearer_header`
- `test_forbidden_auth_errors_return_403`
- `test_account_link_required_returns_409`
- `test_upload_too_large_returns_413`
- `test_unsupported_media_type_returns_415`
- `test_invalid_input_returns_422`
- `test_job_not_found_returns_404`
- `test_job_result_not_ready_returns_409`
- `test_retryable_infrastructure_error_returns_503`
- `test_non_retryable_infrastructure_error_returns_500`
- `test_auth_errors_hide_internal_details`
- `test_public_error_details_are_allowlisted`
- `test_request_validation_error_uses_public_error_shape`
- `test_unexpected_error_returns_generic_500_without_internal_details`

## `test_api_middleware.py`

Status: Completed.

- `test_request_id_middleware_preserves_valid_request_id`
- `test_request_id_middleware_generates_missing_request_id`
- `test_request_id_middleware_replaces_invalid_request_id`
- `test_request_id_is_available_in_request_state`
- `test_request_id_is_returned_in_response_header`
- `test_request_id_rejects_control_characters`
- `test_request_id_rejects_oversized_values`
- `test_install_request_id_middleware_registers_middleware`

## `test_api_health.py`

Status: Completed.

- `test_health_check_returns_ok`
- `test_health_route_is_registered`
- `test_health_response_rejects_extra_fields`
- `test_health_route_does_not_require_application_resources`

## `test_api_lifespan.py`

Status: Completed.

- `test_lifespan_reuses_preconfigured_settings`
- `test_lifespan_rejects_invalid_preconfigured_settings`
- `test_lifespan_creates_session_factory_storage_queue_and_auth_service`
- `test_lifespan_exposes_resources_through_application_state`
- `test_lifespan_disposes_engine_on_normal_shutdown`
- `test_lifespan_disposes_engine_when_startup_or_application_fails`
- `test_lifespan_does_not_execute_workflows`
- `test_create_auth_service_uses_auth_settings`
- `test_create_auth_service_rejects_missing_jwt_secret`
- `test_create_pipeline_queue_wraps_public_celery_task`

## `test_api_dependencies.py`

Status: Completed.

- `test_get_settings_returns_application_settings`
- `test_get_session_factory_returns_application_factory`
- `test_get_storage_returns_application_storage`
- `test_get_queue_returns_application_queue`
- `test_resource_dependencies_reject_missing_or_invalid_state`
- `test_get_session_yields_and_closes_read_session`
- `test_get_job_store_uses_request_session`
- `test_get_pipeline_service_uses_transactional_job_store`
- `test_get_pipeline_service_reuses_storage_and_queue`

## `test_api_jobs.py`

Status: Completed.

- `test_submit_job_parses_analysis_request_and_validates_upload`
- `test_submit_job_parses_adaptation_request_and_user_profile`
- `test_submit_job_uses_authenticated_user_id`
- `test_submit_job_forwards_idempotency_key`
- `test_submit_job_calls_pipeline_service_with_rewound_stream`
- `test_submit_job_returns_202_public_response`
- `test_submit_job_does_not_return_storage_references`
- `test_submit_job_rejects_invalid_request_json`
- `test_get_job_status_returns_owned_job`
- `test_get_job_status_rejects_missing_job`
- `test_get_job_status_hides_job_owned_by_another_user`
- `test_get_job_result_returns_completed_owned_job`
- `test_get_job_result_rejects_incomplete_job`
- `test_get_job_result_hides_job_owned_by_another_user`
- `test_job_responses_do_not_expose_input_or_storage_fields`

## `test_api_main.py`

Status: Completed.

- `test_create_app_uses_explicit_settings`
- `test_create_app_loads_settings_once_when_not_injected`
- `test_create_app_configures_api_lifespan`
- `test_create_app_stores_resolved_settings`
- `test_create_app_configures_explicit_cors_origins`
- `test_create_app_does_not_enable_wildcard_cors`
- `test_create_app_installs_request_id_middleware`
- `test_create_app_installs_exception_handlers`
- `test_create_app_registers_health_auth_and_jobs_routers`
- `test_importing_main_does_not_connect_to_infrastructure`
- `test_module_app_is_created_by_create_app`

## `test_api_public_api.py`

Status: Completed.

- `test_public_api_exports_expected_symbols`
- `test_public_api_does_not_export_internal_routers_or_dependencies`
- `test_public_api_imports_without_circular_dependencies`
