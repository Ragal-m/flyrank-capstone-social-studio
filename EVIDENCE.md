# Evidence

Run `python -m pytest -q` to reproduce the acceptance evidence.

## Verified test run

```text
.........                                                                [100%]
9 passed, 1 warning
```

The warning is a dependency deprecation notice from FastAPI's test client and
does not affect behavior.

## Definition of done

| Requirement | Reproducible proof |
|---|---|
| Image dimensions and safe centered crop | `test_platform_image_dimensions` asserts 1080x1080 and 1600x900 artifacts. |
| Distinct platform captions | `test_platform_captions_are_distinct` checks voice and length differences. |
| One interface, two adapters | `SocialPublisher`, `FakeInstagramPublisher`, and `FakeXPublisher` in `app/publishers.py`. |
| Encrypted tokens with random IV | `test_tokens_use_random_nonce_and_round_trip` proves ciphertext differs and plaintext is absent from the database. |
| Duplicate prevention | `test_duplicate_publish_creates_one_platform_post` proves two calls create one fake post. |
| Timeout safety | `test_timeout_retry_reuses_idempotency_key` proves the same key is reused. |
| Retry-After behavior | `test_rate_limit_honors_retry_after` proves one wait of exactly three seconds and one retry. |
| Crash recovery | `test_expired_worker_lease_is_reclaimed_without_changing_key` proves an expired job is reclaimed with its original key. |
| Forged webhook rejection | `test_forged_webhook_is_rejected_and_valid_webhook_updates_status` proves 400 plus unchanged state, then verified publication. |
| Modified payload rejection | `test_modified_signed_body_is_rejected` proves a signature cannot be reused for changed content. |

## Submission-pack checks

- `capstone.yaml` contains run, seed, test, base URL, and probe endpoints.
- `README.md` contains architecture, setup, demo, and limitations.
- `.env.example` lists every configurable value without real credentials.
- `BUILDLOG.md` records AI assistance and corrections honestly.
- The fake platform is included; no real social account is contacted.

