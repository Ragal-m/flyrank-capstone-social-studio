# Build log

## AI assistance

AI helped translate the brief into acceptance checks, draft the layered
implementation, and enumerate failure cases. I reviewed the boundaries,
renamed unclear concepts, kept captions deterministic, and chose SQLite so the
demo remains free and reproducible.

## Corrections made

- Rejected real-platform integration because the brief requires sandbox-first.
- Kept delivery status webhook-driven instead of marking posts published from
  an outbound HTTP 200.
- Stored idempotency before retry behavior so a timeout cannot double-publish.
- Used random AES-GCM nonces rather than a fixed IV.

## Ownership

The code uses small functions and explicit data flow so every line can be
explained during review.


