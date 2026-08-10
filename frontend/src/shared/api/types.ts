import type { components, operations, paths } from './generated/schema'

type ApiSchemas = components['schemas']

export type ApiErrorResponse = ApiSchemas['ApiErrorResponse']
export type AccessTokenResponse = ApiSchemas['AccessTokenResponse']
export type CurrentUserResponse = ApiSchemas['CurrentUserResponse']
export type GoogleLoginRequest = ApiSchemas['GoogleLoginRequest']
export type PasswordLoginRequest = ApiSchemas['PasswordLoginRequest']
export type RegisterRequest = ApiSchemas['RegisterRequest']
export type RegisterResponse = ApiSchemas['RegisterResponse']
export type ResendEmailVerificationRequest = ApiSchemas['ResendEmailVerificationRequest']
export type ResendEmailVerificationResponse = ApiSchemas['ResendEmailVerificationResponse']

export type HealthResponse = ApiSchemas['HealthResponse']
export type JobSubmissionResponse = ApiSchemas['JobSubmissionResponse']
export type JobStatusResponse = ApiSchemas['JobStatusResponse']
export type JobResultResponse = ApiSchemas['JobResultResponse']
export type JobResultOutput = ApiSchemas['JobResultOutput']
export type PublicTranscriptionOutput = ApiSchemas['PublicTranscriptionOutput']
export type PublicAdaptedScriptOutput = ApiSchemas['PublicAdaptedScriptOutput']

export type ApiPaths = paths
export type ApiOperations = operations
