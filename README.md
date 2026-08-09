# FlyRank Capstone Social Studio

A sandbox-first multi-platform campaign publisher. One blog post becomes
Instagram and X image variants, distinct captions, durable scheduled jobs, and
idempotent fake-platform publishes whose status changes only after a verified
delivery webhook.

No real social account is used.

## Architecture

```text
Blog post -> caption composer -> Instagram/X captions
          -> image pipeline   -> 1080x1080 / 1600x900 images
          -> SQLite campaign  -> durable worker
                              -> SocialPublisher interface
                                 -> Instagram adapter
                                 -> X adapter
                              -> fake platform
                              -> signed webhook -> verified status
```

## Quick start

```bash
docker compose up --build
docker compose exec app python -m app.seed
```

The included defaults are safe only for the local fake-platform demo. To use
your own local secrets, copy `.env.example` to `.env`, generate a 32-byte
base64 encryption key, and pass the values through your environment.

Open `http://localhost:8000/docs` for the API.

## Demo flow

1. Seed a campaign and wait five seconds.
2. Inspect it with `GET /campaigns/{campaign_id}`.
3. Call `POST /campaigns/{campaign_id}/publish` repeatedly and confirm the
   fake post count remains two.
4. Configure a one-request 429 with
   `POST /fake/control/rate-limit/x` and watch the safe retry.
5. Send a forged delivery webhook and receive 400; use a correctly signed
   event and watch the post become published.

## Tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

## Limitations

The core intentionally supports only Instagram and X against the included fake
platform. The worker is single-node and SQLite-backed; a multi-node deployment
would replace its claim transaction with a database queue such as PostgreSQL
`SKIP LOCKED`. Caption generation is deterministic so the project needs no
paid model or API key.

