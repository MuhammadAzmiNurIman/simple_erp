"""Add approval and rejection audit fields to sales orders, purchase orders and transfers.

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-10-26 17:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'a7b8c9d0e1f2'
down_revision = 'f6a7b8c9d0e1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('sales_orders') as batch_op:
        batch_op.add_column(sa.Column('approved_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('rejected_by', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('rejected_at', sa.DateTime(), nullable=True))
        batch_op.create_foreign_key('fk_sales_orders_rejected_by_users', 'users', ['rejected_by'], ['id'])

    with op.batch_alter_table('purchase_orders') as batch_op:
        batch_op.add_column(sa.Column('rejected_by', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('rejected_at', sa.DateTime(), nullable=True))
        batch_op.create_foreign_key('fk_purchase_orders_rejected_by_users', 'users', ['rejected_by'], ['id'])

    with op.batch_alter_table('stock_transfers') as batch_op:
        batch_op.add_column(sa.Column('rejected_by', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('rejected_at', sa.DateTime(), nullable=True))
        batch_op.create_foreign_key('fk_stock_transfers_rejected_by_users', 'users', ['rejected_by'], ['id'])


def downgrade():
    with op.batch_alter_table('stock_transfers') as batch_op:
        batch_op.drop_constraint('fk_stock_transfers_rejected_by_users', type_='foreignkey')
        batch_op.drop_column('rejected_at')
        batch_op.drop_column('rejected_by')

    with op.batch_alter_table('purchase_orders') as batch_op:
        batch_op.drop_constraint('fk_purchase_orders_rejected_by_users', type_='foreignkey')
        batch_op.drop_column('rejected_at')
        batch_op.drop_column('rejected_by')

    with op.batch_alter_table('sales_orders') as batch_op:
        batch_op.drop_constraint('fk_sales_orders_rejected_by_users', type_='foreignkey')
        batch_op.drop_column('rejected_at')
        batch_op.drop_column('rejected_by')
        batch_op.drop_column('approved_at')
