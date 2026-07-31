/**
 * Optional controls shared by regular HTTP requests.
 */
export interface ApiRequestOptions {
  /**
   * Allows the caller to cancel the request using `AbortController`.
   */
  readonly signal?: AbortSignal
}

/**
 * Safe upload progress information exposed to the interface.
 */
export interface UploadProgress {
  readonly loadedBytes: number
  readonly totalBytes: number | null
  readonly percentage: number | null
}

/**
 * Callback invoked while an upload is being transferred.
 */
export type UploadProgressCallback = (progress: UploadProgress) => void

/**
 * Optional controls used by requests that upload files.
 */
export interface UploadRequestOptions extends ApiRequestOptions {
  readonly onUploadProgress?: UploadProgressCallback
}
