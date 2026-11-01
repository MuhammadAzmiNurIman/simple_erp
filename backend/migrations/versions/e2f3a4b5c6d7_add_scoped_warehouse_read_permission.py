"""Allow users to list only their assigned warehouses.

Revision ID: e2f3a4b5c6d7
Revises: e1f2a3b4c5d6
Create Date: 2026-10-26 21:30:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'e2f3a4b5c6d7'
down_revision = 'e1f2a3b4c5d6'
branch_labels = None
depends_on = None


WAREHOUSE_READ_ROLES = (
    'admin', 'operator', 'viewer', 'purchasing',
    'warehouse', 'sales', 'finance', 'manager',
)


def upgrade():
    op.execute(sa.text("""
        INSERT INTO permissions (code, name, module, action, warehouse_scoped)
        SELECT 'warehouses.read', 'Read assigned warehouses', 'warehouses', 'read', 1
        WHERE NOT EXISTS (
            SELECT 1 FROM permissions WHERE code = 'warehouses.read'
        )
    """))
    op.execute(sa.text("""
        UPDATE permissions
        SET warehouse_scoped = 1
        WHERE code = 'warehouses.read'
    """))
    op.execute(sa.text("""
        INSERT INTO role_permissions (role_code, permission_code)
        SELECT roles.code, 'warehouses.read'
        FROM roles
        WHERE roles.code IN (
            'admin', 'operator', 'viewer', 'purchasing',
            'warehouse', 'sales', 'finance', 'manager'
        )
        AND NOT EXISTS (
            SELECT 1 FROM role_permissions
            WHERE role_permissions.role_code = roles.code
              AND role_permissions.permission_code = 'warehouses.read'
        )
    """))


def downgrade():
    role_permissions = sa.table(
        'role_permissions',
        sa.column('role_code', sa.String(32)),
        sa.column('permission_code', sa.String(64)),
    )
    permissions = sa.table(
        'permissions',
        sa.column('code', sa.String(64)),
    )
    op.execute(sa.delete(role_permissions).where(
        role_permissions.c.permission_code == 'warehouses.read'
    ))
    op.execute(sa.delete(permissions).where(permissions.c.code == 'warehouses.read'))
