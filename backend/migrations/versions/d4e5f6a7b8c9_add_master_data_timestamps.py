"""Add created_at and updated_at timestamps to product master data.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-10-26 10:30:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'd4e5f6a7b8c9'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def _add_timestamps(table):
    with op.batch_alter_table(table) as batch_op:
        batch_op.add_column(sa.Column(
            'created_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP')
        ))
        batch_op.add_column(sa.Column(
            'updated_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP')
        ))


def upgrade():
    for table in ('products', 'categories', 'units'):
        _add_timestamps(table)


def downgrade():
    for table in ('units', 'categories', 'products'):
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_column('updated_at')
            batch_op.drop_column('created_at')
