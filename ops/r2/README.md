# R2 Security Configuration

The application uses a private R2 bucket and returns only short-lived
presigned `PUT` URLs to authenticated users.

## Bucket

- Keep **Public Access** disabled.
- Do not configure an `r2.dev` public domain for uploaded media.
- Keep `R2_ACCOUNT_ID`, `R2_ACCESS_KEY`, and `R2_SECRET_KEY` only in the API
  and worker environment.
- The API currently limits presigned upload URLs to 900 seconds.

## CORS

Apply `cors.beta.json` to the beta bucket in the R2 dashboard under
**Settings -> CORS Policy**. The policy intentionally allows only the beta
origin, `PUT`, and the `Content-Type` request header.

Use `cors.local.json` only with a local development bucket. Do not apply it to
the production bucket, because allowing localhost on a production bucket is
unnecessary.

If using Wrangler instead of the dashboard, use the Wrangler-specific file:

```bash
npx wrangler r2 bucket cors set kyrgstudio-media \
  --file ops/r2/cors.beta.wrangler.json
npx wrangler r2 bucket cors list kyrgstudio-media
```

Replace the bucket name when the deployment uses another value. Never put an
API token or R2 secret in this repository or in a frontend environment file.

## Verification checklist

1. Request `POST /v1/jobs/upload-url` without authentication and expect `401`.
2. Send an unsupported MIME type or oversized file metadata and expect a
   validation error before a storage URL is generated.
3. Confirm the response contains only `job_id`, `object_key`, `upload_url`, and
   `expires_in`.
4. Confirm the browser upload sends `Content-Type` equal to the signed type.
5. After 900 seconds, the same presigned URL must be rejected by R2.
6. Search frontend build output and browser responses for `R2_ACCESS_KEY`,
   `R2_SECRET_KEY`, and `R2_ACCOUNT_ID`; none may be present.

The R2 dashboard policy is an external account setting. The JSON files in this
directory are the reviewed, versioned source for that setting; adding them to
the repository does not apply the policy remotely by itself.
