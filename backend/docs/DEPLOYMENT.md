# Deployment guide

This application is a Flask API backed by MySQL in production. Deploy the API
behind a TLS-terminating reverse proxy and run it with a production WSGI server;
do not use Flask's development server for a public deployment.

## Configuration and secrets

Set these values through the deployment platform's secret/environment manager:

- `DATABASE_URL`: MySQL URL using `mysql+pymysql` and `utf8mb4`.
- `SECRET_KEY` and `JWT_SECRET_KEY`: independently generated, persistent secrets.
- `CORS_ORIGINS`: comma-separated exact frontend origins. Avoid wildcard origins.
- `RATELIMIT_STORAGE_URI`: shared Redis URL for multiple API instances.
- `RATELIMIT_DEFAULT_LIMITS`: tune against observed usage and service capacity.
- `MAX_CONTENT_LENGTH`: request size ceiling; the default is 16 MiB.
- `UPLOAD_FOLDER`: durable storage path if the application accepts uploaded files.

Never commit production `.env` files or secrets. Rotate secrets deliberately:
changing `JWT_SECRET_KEY` invalidates existing access tokens. Use TLS for the
database and Redis connections when they cross a network boundary.

## Database rollout

1. Provision MySQL with `utf8mb4`, InnoDB, application-specific credentials,
   and network access limited to the API hosts.
2. Take a database backup and verify that it can be restored to a separate
   database before every production migration.
3. Apply reviewed Alembic revisions with
   `python -m flask --app run db upgrade` as a one-off deployment job. Do not
   run schema migrations independently from every web worker.
4. Seed authorization only for a new installation using
   `python -m flask --app run seed-authorization`.
5. Deploy the application release after migration succeeds. Keep the previous
   application image available for rollback; database rollback requires a
   separately reviewed migration or restore plan.
6. For an existing installation adopting the tracked role matrix, first run
   `python -m flask --app run reconcile-role-permissions` as a dry run. Review
   `untracked_grants_to_remove`, `denied_grants_to_remove`, and unknown
   permissions in the output. If an extra grant is intentional, record it
   through role management before applying the plan; that creates an explicit
   override. Then run
   `python -m flask --app run reconcile-role-permissions --apply` once as a
   deployment job. The command asks for confirmation, writes a JSON snapshot
   under `backend/db_backups` (or the supplied `--snapshot-file`), reconciles
   built-in roles to code defaults plus recorded overrides, and writes an audit
   log entry for each reconciled role. It does not change custom roles. Unknown
   permission catalog rows are reported and hidden from role management until
   reviewed; they are not deleted automatically.
7. For later releases that change built-in defaults, apply migrations first,
   then run `python -m flask --app run sync-role-permissions --yes` once as a
   deployment job. This updates the recorded baseline and preserves explicit
   overrides. Do not run either command from each web worker.

Do not point the deployment migration job at the local legacy `app.db` file.
Use a copy and follow the migration compatibility instructions in
[`../README.md`](../README.md) before adopting legacy data.

## Runtime and scaling

Run the API under a WSGI server such as Gunicorn with a bounded worker count,
request timeout, and graceful shutdown. Put a reverse proxy or load balancer in
front for HTTPS, request size limits, health checks, and connection management.
All instances must use the same MySQL database and shared Redis rate-limit
storage. The default in-memory rate-limit store is per process and is not
suitable for coordinated limits across multiple instances.

Build the frontend as a static asset bundle and serve it from a TLS-enabled
static host or reverse proxy. Set `VITE_API_BASE_URL` at build time to the
public API base path (for example, `/api/v1`) and allow that exact frontend
origin in `CORS_ORIGINS` when the API uses a separate host.

Store user uploads on durable shared storage if uploads are enabled. Local
container filesystems are ephemeral and are not a backup strategy.

## Backups and recovery

Use automated encrypted MySQL backups with retention and point-in-time recovery
where available. Back up uploaded files separately. Monitor backup completion,
and periodically restore a backup into an isolated environment to confirm
recovery works. Document the restore owner, target database, and recovery point
for the operating team.

## Logging and operations

Send structured application, proxy, database, and worker logs to a centralized
retention system. Exclude passwords, authorization headers, JWTs, and payment
secrets from logs. Alert on sustained 5xx responses, database connection
failures, worker restarts, rate-limit backend failures, and exhausted disk or
connection capacity. Expose `/api/v1/health` to the load balancer and keep
deeper dependency checks internal to monitoring.

## Shared rate limits

Configure a Redis-backed `RATELIMIT_STORAGE_URI` for all API instances. Set
limits at the proxy and application layers based on observed traffic; the proxy
should also cap abusive bursts. Confirm that all workers use the same Redis
database and key prefix, and monitor Redis reachability and memory use.
