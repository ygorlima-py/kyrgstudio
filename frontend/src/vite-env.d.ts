/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_AUTH_CSRF_COOKIE_NAME: string
  readonly VITE_MAX_UPLOAD_BYTES: string
  readonly VITE_ACCEPTED_MEDIA_TYPES: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
