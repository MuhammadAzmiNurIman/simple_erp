"""Track intentional grants and denials on built-in roles.

Revision ID: f4b5c6d7e8f9
Revises: f3a4b5c6d7e8
Create Date: 2026-10-27 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'f4b5c6d7e8f9'
down_revision = 'f3a4b5c6d7e8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'role_permission_overrides',
        sa.Column('role_code', sa.String(length=32), nullable=False),
        sa.Column('permission_code', sa.String(length=64), nullable=False),
        sa.Column('is_granted', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['permission_code'], ['permissions.code']),
        sa.ForeignKeyConstraint(['role_code'], ['roles.code']),
        sa.PrimaryKeyConstraint('role_code', 'permission_code'),
    )
    op.create_table(
        'role_default_permissions',
        sa.Column('role_code', sa.String(length=32), nullable=False),
        sa.Column('permission_code', sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(['permission_code'], ['permissions.code']),
        sa.ForeignKeyConstraint(['role_code'], ['roles.code']),
        sa.PrimaryKeyConstraint('role_code', 'permission_code'),
    )


def downgrade():
    op.drop_table('role_default_permissions')
    op.drop_table('role_permission_overrides')
