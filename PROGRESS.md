# Release Progress

## Implemented Release Baseline

- Generic local workspace setup replaces hard-coded VLN/navigation defaults.
- Clean installations create their SQLite database at startup; databases and backups are ignored by Git.
- Search, refresh, and analysis now use a SQLite-backed durable job queue.
- API, worker, and scheduler have separate portable entry points.
- Relevance screening retains rejected papers instead of deleting them.
- PDF ingestion restricts hosts/redirects and applies type, size, page, and timeout limits.
- Frontend setup and settings pages use the canonical workspace API.
- Documentation now describes the local release model and clean-database policy.

## Remaining Release Work

- Add Alembic only when supporting upgrades from this clean-release schema.
- Add automated frontend tests, linting, and formatting gates.
- Add richer job progress/retry controls and knowledge-base revision history.
- Add a dedicated rejected-paper administration view.
