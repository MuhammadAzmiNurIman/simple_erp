"""Scope financial read permissions to assigned warehouses.

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-10-26 21:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'e1f2a3b4c5d6'
down_revision = 'd0e1f2a3b4c5'
branch_labels = None
depends_on = None


SCOPED_FINANCE_READ_PERMISSIONS = (
    'vendor_bills.read',
    'sales_invoices.read',
    'customer_payments.read',
    'supplier_payments.read',
    'finance.read',
    'finance.cash.read',
)


def upgrade():
    permissions = sa.table(
        'permissions',
        sa.column('code', sa.String(64)),
        sa.column('warehouse_scoped', sa.Boolean()),
    )
    op.execute(
        sa.update(permissions)
        .where(permissions.c.code.in_(SCOPED_FINANCE_READ_PERMISSIONS))
        .values(warehouse_scoped=True)
    )


def downgrade():
    permissions = sa.table(
        'permissions',
        sa.column('code', sa.String(64)),
        sa.column('warehouse_scoped', sa.Boolean()),
    )
    op.execute(
        sa.update(permissions)
        .where(permissions.c.code.in_(SCOPED_FINANCE_READ_PERMISSIONS))
        .values(warehouse_scoped=False)
    )
