"""Track damaged customer returns in quarantine through final disposition.

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-10-26 19:15:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'd0e1f2a3b4c5'
down_revision = 'c9d0e1f2a3b4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'inventory_quarantines',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_sales_return_item_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('warehouse_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Numeric(15, 4, asdecimal=False), nullable=False),
        sa.Column('unit_cost', sa.Numeric(15, 4), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.CheckConstraint('quantity > 0', name='ck_inventory_quarantines_quantity'),
        sa.CheckConstraint(
            "status IN ('QUARANTINED', 'RELEASED', 'SCRAPPED')",
            name='ck_inventory_quarantines_status',
        ),
        sa.ForeignKeyConstraint(['source_sales_return_item_id'], ['sales_return_items.id']),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_sales_return_item_id', name='uq_quarantine_sales_return_item'),
    )
    op.create_index(
        'ix_inventory_quarantines_warehouse_status',
        'inventory_quarantines',
        ['warehouse_id', 'status'],
    )
    op.create_index(
        'ix_inventory_quarantines_product',
        'inventory_quarantines',
        ['product_id'],
    )

    op.create_table(
        'inventory_quarantine_actions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('quarantine_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('posted_by', sa.Integer(), nullable=True),
        sa.Column('posted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.CheckConstraint(
            "action IN ('RELEASE', 'SCRAP')",
            name='ck_inventory_quarantine_actions_action',
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'APPROVED', 'REJECTED', 'POSTED')",
            name='ck_inventory_quarantine_actions_status',
        ),
        sa.ForeignKeyConstraint(['quarantine_id'], ['inventory_quarantines.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id']),
        sa.ForeignKeyConstraint(['posted_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_inventory_quarantine_actions_quarantine_id',
        'inventory_quarantine_actions',
        ['quarantine_id'],
    )

    permissions = sa.table(
        'permissions',
        sa.column('code', sa.String(64)),
        sa.column('name', sa.String(100)),
        sa.column('module', sa.String(40)),
        sa.column('action', sa.String(30)),
        sa.column('warehouse_scoped', sa.Boolean()),
    )
    op.bulk_insert(permissions, [
        {'code': 'inventory.quarantine.read', 'name': 'Read quarantined stock', 'module': 'inventory', 'action': 'read', 'warehouse_scoped': True},
        {'code': 'inventory.quarantine.action.create', 'name': 'Request quarantine disposition', 'module': 'inventory', 'action': 'create', 'warehouse_scoped': True},
        {'code': 'inventory.quarantine.action.approve', 'name': 'Approve quarantine disposition', 'module': 'inventory', 'action': 'approve', 'warehouse_scoped': True},
        {'code': 'inventory.quarantine.action.post', 'name': 'Post quarantine disposition', 'module': 'inventory', 'action': 'post', 'warehouse_scoped': True},
    ])
    role_permissions = sa.table(
        'role_permissions',
        sa.column('role_code', sa.String(32)),
        sa.column('permission_code', sa.String(64)),
    )
    grants = {
        'admin': (
            'inventory.quarantine.read',
            'inventory.quarantine.action.create',
            'inventory.quarantine.action.approve',
            'inventory.quarantine.action.post',
        ),
        'warehouse': (
            'inventory.quarantine.read',
            'inventory.quarantine.action.create',
            'inventory.quarantine.action.post',
        ),
        'manager': (
            'inventory.quarantine.read',
            'inventory.quarantine.action.approve',
        ),
    }
    existing_role_codes = {
        row[0]
        for row in op.get_bind().execute(sa.text('SELECT code FROM roles')).fetchall()
    }
    op.bulk_insert(role_permissions, [
        {'role_code': role_code, 'permission_code': permission_code}
        for role_code, permission_codes in grants.items()
        if role_code in existing_role_codes
        for permission_code in permission_codes
    ])

    # Earlier releases stored damaged returns only on the return document. Move
    # those posted lines into quarantine so existing data is visible as well.
    op.execute(sa.text("""
        INSERT INTO inventory_quarantines (
            source_sales_return_item_id, product_id, warehouse_id, quantity,
            unit_cost, reason, status, created_by, created_at
        )
        SELECT
            sri.id,
            si.product_id,
            so.warehouse_id,
            sri.quantity,
            COALESCE(si.unit_cost, si.unit_price, 0),
            sr.reason,
            'QUARANTINED',
            sr.posted_by,
            COALESCE(sr.posted_at, sr.created_at)
        FROM sales_return_items AS sri
        JOIN sales_returns AS sr ON sr.id = sri.sales_return_id
        JOIN shipments AS sh ON sh.id = sr.shipment_id
        JOIN sales_orders AS so ON so.id = sh.sales_order_id
        JOIN shipment_items AS si ON si.id = sri.shipment_item_id
        WHERE sr.status = 'POSTED' AND sri.disposition = 'DAMAGED'
    """))


def downgrade():
    role_permissions = sa.table(
        'role_permissions',
        sa.column('role_code', sa.String(32)),
        sa.column('permission_code', sa.String(64)),
    )
    permission_codes = (
        'inventory.quarantine.read',
        'inventory.quarantine.action.create',
        'inventory.quarantine.action.approve',
        'inventory.quarantine.action.post',
    )
    op.execute(sa.delete(role_permissions).where(
        role_permissions.c.permission_code.in_(permission_codes)
    ))
    permissions = sa.table('permissions', sa.column('code', sa.String(64)))
    op.execute(sa.delete(permissions).where(permissions.c.code.in_(permission_codes)))

    op.drop_index(
        'ix_inventory_quarantine_actions_quarantine_id',
        table_name='inventory_quarantine_actions',
    )
    op.drop_table('inventory_quarantine_actions')
    op.drop_index(
        'ix_inventory_quarantines_product',
        table_name='inventory_quarantines',
    )
    op.drop_index(
        'ix_inventory_quarantines_warehouse_status',
        table_name='inventory_quarantines',
    )
    op.drop_table('inventory_quarantines')
