# Design

## Problem

Publish one blog post as a reliable, scheduled two-platform campaign without
duplicates, plaintext tokens, or untrusted status changes.

## Data model

- `campaigns`: source content and creation time
- `social_posts`: platform, caption, image, schedule, status, idempotency key
- `tokens`: platform token encrypted with AES-GCM and a random nonce
- `publish_attempts`: retry state and next eligible time
- `fake_posts`: fake-platform idempotency ledger
- `schema_migrations`: applied persistence versions
- `failure_alerts`: durable terminal worker failures scoped by tenant

## API surface

- `POST /campaigns`
- `GET /campaigns/{campaign_id}`
- `POST /campaigns/{campaign_id}/publish`
- `POST /webhook/social-delivery`
- `GET /alerts`

Campaign endpoints require an API key and all application records are scoped
to `DEFAULT_TENANT_ID`. Webhooks use their independent HMAC trust boundary.
- fake OAuth, publishing, rate-limit control, and inspection endpoints

## Layers

HTTP routes call campaign and worker services. Services depend on repository
functions and the `SocialPublisher` protocol. Adapters translate protocol calls
to the fake platform. SQLite and HTTP can be replaced independently.

## Non-goal

Publishing to real social networks is explicitly out of scope.
