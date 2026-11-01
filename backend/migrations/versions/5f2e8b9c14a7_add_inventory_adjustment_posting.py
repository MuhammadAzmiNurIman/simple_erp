"""Add inventory adjustment posting metadata.

Revision ID: 5f2e8b9c14a7
Revises: 762c02201f47
Create Date: 2026-10-25 16:15:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '5f2e8b9c14a7'
down_revision = '762c02201f47'
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    columns = {
        column['name']
        for column in inspector.get_columns('inventory_adjusters')
    }
    foreign_key_columns = {
        column
        for constraint in inspector.get_foreign_keys('inventory_adjusters')
        for column in constraint['constrained_columns']
    }
    nullable_user_columns = {'created_by', 'reviewed_by', 'posted_by'}
    missing_columns = {
        'created_by', 'reviewed_by', 'reviewed_at', 'posted_by', 'posted_at'
    } - columns
    missing_foreign_keys = nullable_user_columns - foreign_key_columns
    if missing_columns or missing_foreign_keys:
        with op.batch_alter_table('inventory_adjusters') as batch_op:
            for column in sorted(missing_columns):
                batch_op.add_column(sa.Column(
                    column,
                    sa.DateTime() if column.endswith('_at') else sa.Integer(),
                    nullable=True
                ))
            for column in sorted(missing_foreign_keys):
                batch_op.create_foreign_key(
                    f'fk_inventory_adjusters_{column}_users',
                    'users',
                    [column],
                    ['id']
                )


def downgrade():
    with op.batch_alter_table('inventory_adjusters') as batch_op:
        batch_op.drop_constraint(
            'fk_inventory_adjusters_posted_by_users',
            type_='foreignkey'
        )
        batch_op.drop_column('posted_at')
        batch_op.drop_column('posted_by')
