# Auth Unit Tests

## `test_auth_principal.py`

Status: Completed.

- `test_authenticated_principal_normalizes_verified_identity`
- `test_authenticated_principal_is_immutable`
- `test_authenticated_principal_rejects_invalid_user_id`
- `test_authenticated_principal_rejects_invalid_email`
- `test_google_identity_normalizes_verified_claims`
- `test_google_identity_rejects_invalid_claims`
- `test_access_token_claims_require_timezone_aware_dates`
- `test_access_token_claims_reject_invalid_date_order`
- `test_access_token_claims_require_access_token_type`
- `test_issued_auth_tokens_require_bearer_token_type`
- `test_issued_auth_tokens_require_refresh_expiry_after_access_expiry`
- `test_token_contract_repr_hides_token_values`

## `test_auth_passwords.py`

Status: Completed.

- `test_hash_produces_argon2id_encoded_hash`
- `test_hash_accepts_password_at_configured_boundaries`
- `test_hash_rejects_password_outside_configured_boundaries`
- `test_verify_accepts_correct_password`
- `test_verify_rejects_incorrect_password`
- `test_verify_rejects_missing_or_malformed_hash`
- `test_verify_uses_dummy_hash_for_missing_or_malformed_hash`
- `test_verify_accepts_legacy_password_below_registration_minimum`
- `test_verify_and_update_returns_replacement_hash_when_parameters_change`
- `test_verify_and_update_returns_none_when_hash_is_current`
- `test_constructor_rejects_invalid_argon2_configuration`

## `test_auth_tokens.py`

Status: Completed.

- `test_issue_creates_access_jwt_with_required_claims`
- `test_issue_generates_unique_jti_for_each_token`
- `test_decode_returns_validated_access_token_claims`
- `test_decode_rejects_expired_token`
- `test_decode_rejects_modified_signature`
- `test_decode_rejects_wrong_issuer`
- `test_decode_rejects_wrong_audience`
- `test_decode_rejects_wrong_algorithm`
- `test_decode_rejects_missing_required_claims`
- `test_decode_rejects_non_access_token_type`
- `test_access_token_service_rejects_invalid_configuration`
- `test_refresh_generator_returns_unique_url_safe_tokens`
- `test_refresh_digest_is_deterministic`
- `test_refresh_digest_changes_for_different_tokens`
- `test_refresh_generator_rejects_insufficient_entropy`
- `test_refresh_digest_rejects_invalid_token_input`

## `test_auth_google.py`

Status: Completed.

- `test_constructor_accepts_and_deduplicates_valid_client_ids`
- `test_constructor_rejects_empty_or_invalid_client_ids`
- `test_verify_uses_google_verifier_with_configured_audience_and_clock_skew`
- `test_verify_maps_verified_claims_to_google_identity`
- `test_verify_accepts_supported_google_issuers`
- `test_verify_rejects_untrusted_issuer`
- `test_verify_rejects_unconfigured_audience`
- `test_verify_rejects_missing_required_claims`
- `test_verify_preserves_email_verified_claim`
- `test_verify_maps_google_auth_failure_to_invalid_credentials`
- `test_verify_maps_transport_failure_to_auth_configuration_error`
- `test_verification_errors_do_not_expose_id_token`

## `test_auth_transactional_store.py`

Status: Completed.

- `test_auth_user_record_exposes_verified_and_disabled_properties`
- `test_auth_session_record_exposes_revoked_property`
- `test_get_user_uses_short_read_session_and_returns_detached_record`
- `test_get_user_by_email_uses_short_read_session`
- `test_get_user_by_google_subject_uses_short_read_session`
- `test_get_session_by_token_hash_uses_short_read_session`
- `test_create_password_user_with_session_commits_user_and_session_together`
- `test_create_google_user_with_session_commits_user_and_session_together`
- `test_create_session_uses_short_write_transaction`
- `test_rotate_session_uses_single_write_transaction`
- `test_rotate_session_by_token_hash_returns_not_found`
- `test_rotate_session_by_token_hash_returns_expired`
- `test_rotate_session_by_token_hash_returns_user_not_found`
- `test_rotate_session_by_token_hash_rotates_active_session_atomically`
- `test_rotate_session_by_token_hash_revokes_family_on_reuse`
- `test_revoke_session_uses_short_write_transaction`
- `test_revoke_user_sessions_uses_short_write_transaction`
- `test_revoke_session_family_uses_short_write_transaction`
- `test_update_password_hash_uses_short_write_transaction`
- `test_invalid_identifiers_raise_user_store_error`

## `test_auth_service.py`

Status: Completed.

- `test_constructor_rejects_refresh_ttl_not_greater_than_access_ttl`
- `test_register_normalizes_input_and_never_sends_plain_password_to_store`
- `test_register_creates_user_and_refresh_session_atomically`
- `test_register_maps_email_conflict_to_invalid_input`
- `test_password_login_uses_dummy_verification_for_unknown_email`
- `test_password_login_returns_same_error_for_unknown_email_and_wrong_password`
- `test_password_login_updates_outdated_password_hash`
- `test_password_login_rejects_disabled_account`
- `test_password_login_creates_refresh_session`
- `test_google_login_uses_verified_google_identity`
- `test_google_login_reuses_account_found_by_google_subject`
- `test_google_login_creates_user_and_session_atomically`
- `test_google_login_rejects_unverified_email`
- `test_google_login_requires_explicit_link_for_matching_local_email`
- `test_google_login_rejects_disabled_account`
- `test_refresh_rotates_token_and_issues_new_token_pair`
- `test_refresh_rejects_non_rotated_session_statuses`
- `test_refresh_revokes_sessions_for_disabled_account`
- `test_logout_revokes_refresh_session_family`
- `test_logout_is_idempotent_for_unknown_or_invalid_token`
- `test_authenticate_access_token_returns_active_principal`
- `test_authenticate_access_token_rejects_missing_or_disabled_user`

## `test_auth_dependencies.py`

Status: Completed.

- `test_get_auth_service_returns_lifespan_service`
- `test_get_auth_service_rejects_missing_or_invalid_service`
- `test_get_current_user_requires_bearer_credentials`
- `test_get_current_user_rejects_wrong_authorization_scheme`
- `test_get_current_user_delegates_access_token_to_auth_service`
- `test_refresh_credentials_require_refresh_cookie`
- `test_refresh_credentials_require_matching_csrf_cookie_and_header`
- `test_refresh_credentials_compare_csrf_tokens_in_constant_time`
- `test_refresh_credentials_require_trusted_origin_or_referer`
- `test_refresh_credentials_accept_configured_cors_origin`
- `test_refresh_credentials_accept_same_origin_request`
- `test_logout_credentials_apply_same_cookie_csrf_and_origin_rules`
- `test_origin_normalization_handles_default_ports_and_case`
- `test_credentials_never_accept_tokens_from_query_parameters`

## `test_auth_public_api.py`

Status: Completed.

- `test_public_api_exports_expected_symbols`
- `test_public_api_does_not_export_internal_stores_or_crypto_helpers`
- `test_public_api_imports_without_circular_dependencies`
