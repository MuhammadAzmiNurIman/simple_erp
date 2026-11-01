"""Keep stock adjustment and transfer actions with the warehouse role.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-10-26 18:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'b8c9d0e1f2a3'
down_revision = 'a7b8c9d0e1f2'
branch_labels = None
depends_on = None


operator_stock_permissions = (
    'inventory.adjust.create',
    'inventory.transfer.create',
    'inventory.transfer.submit',
)
workflow_read_permissions = (
    ('inventory.adjust.read', 'Read inventory adjustments'),
    ('inventory.transfer.read', 'Read transfers'),
)


def upgrade():
    permissions = sa.table(
        'permissions',
        sa.column('code', sa.String(64)),
        sa.column('name', sa.String(100)),
        sa.column('module', sa.String(40)),
        sa.column('action', sa.String(30)),
        sa.column('warehouse_scoped', sa.Boolean()),
    )
    role_permissions = sa.table(
        'role_permissions',
        sa.column('role_code', sa.String(32)),
        sa.column('permission_code', sa.String(64)),
    )
    permission_rows = [
        {
            'code': 'inventory.adjust.read',
            'name': 'Read inventory adjustments',
            'module': 'inventory',
            'action': 'read',
            'warehouse_scoped': True,
        },
        {
            'code': 'inventory.transfer.read',
            'name': 'Read transfers',
            'module': 'inventory',
            'action': 'read',
            'warehouse_scoped': True,
        },
    ]
    existing_permission_codes = {
        row[0]
        for row in op.get_bind().execute(
            sa.text('SELECT code FROM permissions')
        ).fetchall()
    }
    op.bulk_insert(permissions, [
        row for row in permission_rows
        if row['code'] not in existing_permission_codes
    ])
    op.execute(
        sa.delete(role_permissions).where(
            role_permissions.c.role_code == 'operator',
            role_permissions.c.permission_code.in_(operator_stock_permissions),
        )
    )
    existing_role_codes = {
        row[0]
        for row in op.get_bind().execute(
            sa.text('SELECT code FROM roles')
        ).fetchall()
    }
    op.bulk_insert(role_permissions, [
        {'role_code': role_code, 'permission_code': permission_code}
        for role_code in ('manager', 'warehouse')
        if role_code in existing_role_codes
        for permission_code in ('inventory.adjust.read', 'inventory.transfer.read')
    ])


def downgrade():
    role_permissions = sa.table(
        'role_permissions',
        sa.column('role_code', sa.String(32)),
        sa.column('permission_code', sa.String(64)),
    )
    op.bulk_insert(role_permissions, [
        {'role_code': 'operator', 'permission_code': permission_code}
        for permission_code in operator_stock_permissions
    ])
    op.execute(
        sa.delete(role_permissions).where(
            role_permissions.c.role_code.in_(('manager', 'warehouse')),
            role_permissions.c.permission_code.in_(
                ('inventory.adjust.read', 'inventory.transfer.read')
            ),
        )
    )
    permissions = sa.table(
        'permissions',
        sa.column('code', sa.String(64)),
    )
    op.execute(
        sa.delete(permissions).where(
            permissions.c.code.in_(('inventory.adjust.read', 'inventory.transfer.read'))
        )
    )
