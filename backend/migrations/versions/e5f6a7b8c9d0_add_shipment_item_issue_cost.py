"""Store inventory cost captured when shipment items are posted.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-10-26 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'e5f6a7b8c9d0'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('shipment_items') as batch_op:
        batch_op.add_column(sa.Column('unit_cost', sa.Numeric(15, 4), nullable=True))


def downgrade():
    with op.batch_alter_table('shipment_items') as batch_op:
        batch_op.drop_column('unit_cost')
