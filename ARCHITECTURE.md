# Architecture

## Local Topology

```text
React/Vite UI --> FastAPI API --> SQLite
                         ^         |
                         |         v
                    scheduler   local worker
                                  |       |
                                arXiv   LLM/PDF
```

The API only accepts requests and creates durable SQLite job records. `app.worker` claims and processes analysis/refresh jobs. `app.scheduler_process` queues the daily refresh and must run as exactly one local process.

## Workspace

A local installation has one `Workspace`. First-run setup creates it with its research scope, arXiv configuration, optional labels, generic prompts, and knowledge base. The workspace is the domain boundary used by relevance analysis; no navigation-specific query, labels, or prompt text are seeded.

The schema carries workspace references on domain records to keep a future multi-workspace migration possible, while the current UI/API intentionally operates on one local workspace.

## Analysis Flow

1. Search or refresh creates a `BackgroundJob`.
2. The worker claims it atomically and records retries/failures.
3. Refresh jobs import arXiv metadata and enqueue paper-analysis jobs.
4. Analysis downloads an allowed arXiv PDF to a temporary location, with size/page/time limits.
5. The LLM evaluates configured workspace relevance, then produces the technical summary, category, route, trend, quality, and labels.
6. Accepted papers are listed normally. Rejected papers remain in storage with their relevance reason and `AnalysisRun` audit record.

## Persistence

SQLite is created by `Base.metadata.create_all()` on a new installation. This release deliberately has no migration path from previous MVP database schemas. Existing database files are ignored and must not be bundled with a release.

PDF full text is not persisted. Stored data includes metadata, analysis output, label/trend links, knowledge-base content, run history, and background-job state.
