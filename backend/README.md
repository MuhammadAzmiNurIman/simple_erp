# DistribuFlow ERP Backend

## Requirements

- Python 3.10+
- MySQL 8.x for deployment (`InnoDB`)
- Dependencies from `requirements.txt`; use `requirements-dev.txt` for tests

## Code organization

The application code is grouped by business domain so related models and API
routes are easy to find:

```text
app/
  models/
    catalog/       # Product, category, unit, and warehouse
    identity/      # User, roles, permissions, and audit records
    inventory/     # Balances, adjustments, movements, and transfers
    partners/      # Customers and suppliers
    purchasing/    # Purchase orders, receipts, bills, supplier payments
    sales/         # Sales orders, shipments, returns, invoices, customer payments
  routes/
    identity/      # Authentication, user management, audit log
    master_data/   # Products, categories, units, partners, warehouses
    inventory/     # Balance, movement, adjustment, transfer endpoints
    purchasing/    # Purchasing transaction endpoints
    sales/         # Sales transaction endpoints
    reporting/     # Reports and statistics
    system/        # API metadata
```

Use `from app.models import ModelName` for model imports. When adding a model,
export it from its domain package's `__init__.py` and from `app/models/__init__.py`.
Put new endpoints in the matching `routes` domain package and register their
blueprint in `app/routes/__init__.py`. Existing blueprint names and `/api/v1`
URLs are kept stable. The active OpenAPI 3.1 specification is available at
`GET /api/v1/openapi.json`. It is generated from the registered Flask routes,
including path parameters, authentication, required permission metadata,
workflow request schemas, report filters, and response envelopes for the
principal report and inventory workflow endpoints. Some less common payloads
still use a generic JSON object schema and can be refined as those contracts
change.

The purchasing and sales route modules still contain several related workflows
each. Returns, inventory adjustments, and transfers already have separate route
modules; extracting order, shipment, invoice, and payment route handlers from
the remaining large transaction files is a follow-up maintainability task.

Sales returns are created as `DRAFT` records linked to posted shipment items.
Posting restocks only items marked `RESTOCK`; `DAMAGED` items remain recorded
without changing inventory. For the MVP return policy, posting a return does
not change customer invoices or payments.

The PRD canonical routes are available alongside legacy aliases. Inventory
movements and low-stock reports are exposed at `/api/v1/inventory/movements`
and `/api/v1/inventory/low-stock`; shipments can be listed and created through
`/api/v1/shipments`, and purchase/sales order lifecycle actions use their
`submit`, `approve`, `cancel`, or `reserve` routes. Inventory movement details
are available at `/api/v1/inventory/movements/{id}`. Legacy routes remain
available for compatibility, are marked `deprecated` in the OpenAPI document,
and include an `x-canonical-path` extension pointing to their replacement. The
route-to-PRD test in `tests/test_auth.py`
checks the canonical path and method matrix, and the authorization tests check
that registered API operations have permission mappings.

Customer payments use `/api/v1/customer-payments`. Create a `DRAFT` payment
with a customer, amount, and method, then add one or more invoice allocations
through `/api/v1/customer-payments/{id}/allocations` before posting it.
Allocations can only target invoices belonging to that customer, cannot exceed
the payment or outstanding invoice balance, and affect invoice balances only
when the payment is posted. The legacy `/api/v1/payments` single-invoice
endpoints remain available. Supplier payments use the same draft/allocation/
posting lifecycle at `/api/v1/supplier-payments`; the legacy post request may
still include allocations directly.

The Finance UI uses `/api/v1/customer-payments/record-and-post` and
`/api/v1/supplier-payments/record-and-post` for a single invoice or vendor bill.
Each endpoint validates the source balance, creates the payment, records its
allocation, updates the document balance, and posts the payment in one database
transaction. Draft endpoints remain available for multi-document payment
allocations and recovery of older drafts.

Mutation audit rows are inserted as part of the first database commit in an
authenticated write request, so a committed business change and its audit
record succeed or roll back together. Requests rejected before a business
commit are written as audit events after the response is built.

Finance endpoints provide outstanding receivables and payables plus a
company-wide cash summary of posted payment amounts. Sales and purchase reports
use invoice and vendor-bill creation dates, respectively. Inventory reporting
uses weighted average cost when combining balances across warehouses. The
dashboard summary defaults to the current month for sales, purchases, and cash.
Warehouse-scoped cash values use allocations assigned to that warehouse; company-wide
cash values use the full posted payment amounts.
Deployment procedures and the proposed financial return workflow are described
in [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) and
[`docs/CREDIT_NOTE_ROADMAP.md`](docs/CREDIT_NOTE_ROADMAP.md).

## Configuration

Configure `DATABASE_URL`, `SECRET_KEY`, `JWT_SECRET_KEY`, `CORS_ORIGINS`, and
`RATELIMIT_STORAGE_URI` through environment variables. `CORS_ORIGINS` is a
comma-separated allowlist and defaults to `*` in development; production
requires explicit origins (wildcards are rejected). `RATELIMIT_DEFAULT_LIMITS`
accepts a semicolon-separated list (default `20000 per day;2000 per hour`) so
dashboard polling and reporting calls are not throttled. A MySQL URL uses the
PyMySQL driver:

```text
mysql+pymysql://USER:PASSWORD@HOST:3306/DATABASE?charset=utf8mb4
```

URL-encode special characters in the username or password. Use stable secrets in
deployment and a shared rate-limit backend such as Redis when running multiple
application instances.

For local development, create `.env` in the backend directory and set
`FLASK_ENV=development` plus a `DATABASE_URL` for your local MySQL user. The
application loads this file on startup. Do not use the production-oriented
`.env.example` unchanged for local development. If development secrets are
omitted, temporary secrets are generated automatically and sessions will not
survive an application restart. `MAX_CONTENT_LENGTH` is configurable in bytes
and defaults to 16 MiB.

## Database schema

The application factory does not create or alter tables. Initialize or upgrade an
empty/deployed schema explicitly:

```powershell
python -m flask --app run db upgrade
python -m flask --app run seed-authorization
```

Review generated changes before creating a revision:

```powershell
python -m flask --app run db migrate -m "Describe schema change"
```

The first revision is a baseline for a new database. A guarded adoption path
also supports the recognized legacy SQLite schema when business transaction
tables are empty; compatible account and master-data records are retained.
Unknown schemas, existing non-SQLite legacy databases, or legacy databases with
transaction data are rejected before schema changes. In particular, invoice
records linked to the old sales-order model are not silently converted because
the current model requires a posted shipment.

The local `app.db` file is legacy data. Do not run `db upgrade` against it or
any operational database without first creating and verifying a backup, testing
the migration on a copy, reviewing any blocked legacy records, and obtaining
operator approval. Do not use `db stamp` to bypass compatibility checks.

Migrations must be tested against a disposable database first. Production
migrations require a verified backup and explicit operator approval.

## Local user bootstrap

After applying migrations, create the first administrator and application users:

```powershell
python -m flask --app run create-admin
python -m flask --app run create-user
```

The built-in roles are `admin`, `purchasing`, `warehouse`, `sales`, `finance`,
and `manager`; `operator` and `viewer` remain for compatibility. Configure
warehouse scopes for users through the administrator API. Public self-registration
is disabled.

## Inventory adjustments

Inventory adjustments are available at `/api/v1/inventory/adjustments` (the
legacy `/inventory/adjusters` routes remain supported). A request starts as
`PENDING`; a different authorized user must approve or reject it. Approval does
not change stock. Only an authorized `POST /api/v1/inventory/adjustments/{id}/post`
changes the balance and writes the corresponding stock movement. A posted
adjustment cannot be posted again.

## Tests

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Tests use an isolated in-memory SQLite database. They never initialize the local
`app.db` schema.

## MySQL migration verification

The configured local MySQL server can be tested against the disposable
`erp_test` database without changing the supplied `erp` database. After
reviewing that `erp_test` is empty, set `DATABASE_URL` to the test database and
run:

```powershell
$env:DATABASE_URL = "mysql+pymysql://root:@localhost:3306/erp_test?charset=utf8mb4"
python -m flask --app run db upgrade
python -m flask --app run db check
```

The `erp` database is not an upgrade target. To run the opt-in purchase, sales,
inventory, payment, and finance workflow test, point `ERP_MYSQL_TEST_URL` at the
disposable `_test` database (the schema must already be upgraded and contain no
business data):

```powershell
$env:ERP_MYSQL_TEST_URL = "mysql+pymysql://root:@localhost:3306/erp_test?charset=utf8mb4"
python -m pytest tests/test_mysql_workflows.py -q
```

The test refuses database names without the `_test` suffix, requires Alembic
revision `b2c3d4e5f6a7`, checks that business tables are empty, and removes test
records afterward. This verifies the tested workflow on that MySQL schema; it
does not certify production readiness or authorize migrating `erp`.
