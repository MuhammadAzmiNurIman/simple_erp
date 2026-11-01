"""Retain source bill for warehouse-scoped supplier payment drafts.

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-10-27 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'f3a4b5c6d7e8'
down_revision = 'e2f3a4b5c6d7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('supplier_payments') as batch_op:
        batch_op.add_column(sa.Column('source_vendor_bill_id', sa.Integer(), nullable=True))
        batch_op.create_index(
            'ix_supplier_payments_source_vendor_bill_id',
            ['source_vendor_bill_id'],
            unique=False
        )
        batch_op.create_foreign_key(
            'fk_supplier_payments_source_vendor_bill_id_vendor_bills',
            'vendor_bills', ['source_vendor_bill_id'], ['id']
        )


def downgrade():
    with op.batch_alter_table('supplier_payments') as batch_op:
        batch_op.drop_constraint(
            'fk_supplier_payments_source_vendor_bill_id_vendor_bills',
            type_='foreignkey'
        )
        batch_op.drop_index('ix_supplier_payments_source_vendor_bill_id')
        batch_op.drop_column('source_vendor_bill_id')
