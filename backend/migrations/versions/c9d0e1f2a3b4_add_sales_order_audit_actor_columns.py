"""Add creator and approver references to sales orders.

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-10-26 18:45:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'c9d0e1f2a3b4'
down_revision = 'b8c9d0e1f2a3'
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    columns = {column['name'] for column in inspector.get_columns('sales_orders')}
    foreign_keys = {
        tuple(constraint['constrained_columns'])
        for constraint in inspector.get_foreign_keys('sales_orders')
    }
    missing_columns = {'created_by', 'approved_by'} - columns
    missing_foreign_keys = {
        column for column in ('created_by', 'approved_by')
        if (column,) not in foreign_keys
    }

    if missing_columns or missing_foreign_keys:
        with op.batch_alter_table('sales_orders') as batch_op:
            for column in sorted(missing_columns):
                batch_op.add_column(sa.Column(column, sa.Integer(), nullable=True))
            for column in sorted(missing_foreign_keys):
                batch_op.create_foreign_key(
                    f'fk_sales_orders_{column}_users',
                    'users',
                    [column],
                    ['id'],
                )


def downgrade():
    inspector = sa.inspect(op.get_bind())
    columns = {column['name'] for column in inspector.get_columns('sales_orders')}
    foreign_keys = {
        tuple(constraint['constrained_columns']): constraint['name']
        for constraint in inspector.get_foreign_keys('sales_orders')
    }
    columns_to_remove = [column for column in ('approved_by', 'created_by') if column in columns]
    constraints_to_remove = [
        foreign_keys[(column,)]
        for column in columns_to_remove
        if (column,) in foreign_keys and foreign_keys[(column,)]
    ]

    if columns_to_remove:
        with op.batch_alter_table('sales_orders') as batch_op:
            for constraint in constraints_to_remove:
                batch_op.drop_constraint(constraint, type_='foreignkey')
            for column in columns_to_remove:
                batch_op.drop_column(column)
