"""Migrate float columns to numeric for currency and quantity precision.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-10-26 08:15:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('products') as batch_op:
        batch_op.alter_column('min_stock', existing_type=sa.Float(), type_=sa.Numeric(15, 4), existing_nullable=True)

    with op.batch_alter_table('inventory_balances') as batch_op:
        batch_op.alter_column('quantity_on_hand', existing_type=sa.Float(), type_=sa.Numeric(15, 4), existing_nullable=True)
        batch_op.alter_column('quantity_reserved', existing_type=sa.Float(), type_=sa.Numeric(15, 4), existing_nullable=True)
        batch_op.alter_column('average_cost', existing_type=sa.Float(), type_=sa.Numeric(15, 4), existing_nullable=True)
        batch_op.alter_column('last_cost', existing_type=sa.Float(), type_=sa.Numeric(15, 4), existing_nullable=True)

    with op.batch_alter_table('inventory_adjusters') as batch_op:
        batch_op.alter_column('quantity', existing_type=sa.Float(), type_=sa.Numeric(15, 4), existing_nullable=False)

    with op.batch_alter_table('stock_movements') as batch_op:
        batch_op.alter_column('quantity_delta', existing_type=sa.Float(), type_=sa.Numeric(15, 4), existing_nullable=False)
        batch_op.alter_column('unit_cost', existing_type=sa.Float(), type_=sa.Numeric(15, 4), existing_nullable=False)

    with op.batch_alter_table('stock_transfer_items') as batch_op:
        batch_op.alter_column('quantity', existing_type=sa.Float(), type_=sa.Numeric(15, 4), existing_nullable=False)

    with op.batch_alter_table('purchase_orders') as batch_op:
        batch_op.alter_column('total_amount', existing_type=sa.Float(), type_=sa.Numeric(15, 2), existing_nullable=False)
        batch_op.alter_column('total_qty', existing_type=sa.Float(), type_=sa.Numeric(15, 4), existing_nullable=False)

    with op.batch_alter_table('purchase_order_items') as batch_op:
        batch_op.alter_column('quantity', existing_type=sa.Float(), type_=sa.Numeric(15, 4), existing_nullable=False)
        batch_op.alter_column('unit_cost', existing_type=sa.Float(), type_=sa.Numeric(15, 4), existing_nullable=False)
        batch_op.alter_column('total_cost', existing_type=sa.Float(), type_=sa.Numeric(15, 2), existing_nullable=False)

    with op.batch_alter_table('goods_receipt_items') as batch_op:
        batch_op.alter_column('quantity', existing_type=sa.Float(), type_=sa.Numeric(15, 4), existing_nullable=False)
        batch_op.alter_column('unit_cost', existing_type=sa.Float(), type_=sa.Numeric(15, 4), existing_nullable=False)

    with op.batch_alter_table('vendor_bills') as batch_op:
        batch_op.alter_column('total_amount', existing_type=sa.Float(), type_=sa.Numeric(15, 2), existing_nullable=False)

    with op.batch_alter_table('supplier_payments') as batch_op:
        batch_op.alter_column('amount', existing_type=sa.Float(), type_=sa.Numeric(15, 2), existing_nullable=False)

    with op.batch_alter_table('supplier_payment_allocations') as batch_op:
        batch_op.alter_column('amount', existing_type=sa.Float(), type_=sa.Numeric(15, 2), existing_nullable=False)

    with op.batch_alter_table('sales_orders') as batch_op:
        batch_op.alter_column('total_amount', existing_type=sa.Float(), type_=sa.Numeric(15, 2), existing_nullable=True)
        batch_op.alter_column('total_qty', existing_type=sa.Float(), type_=sa.Numeric(15, 4), existing_nullable=True)

    with op.batch_alter_table('sales_order_items') as batch_op:
        batch_op.alter_column('quantity', existing_type=sa.Float(), type_=sa.Numeric(15, 4), existing_nullable=False)
        batch_op.alter_column('unit_price', existing_type=sa.Float(), type_=sa.Numeric(15, 2), existing_nullable=False)
        batch_op.alter_column('total_price', existing_type=sa.Float(), type_=sa.Numeric(15, 2), existing_nullable=False)

    with op.batch_alter_table('shipment_items') as batch_op:
        batch_op.alter_column('quantity', existing_type=sa.Float(), type_=sa.Numeric(15, 4), existing_nullable=False)
        batch_op.alter_column('unit_price', existing_type=sa.Float(), type_=sa.Numeric(15, 2), existing_nullable=False)

    with op.batch_alter_table('invoices') as batch_op:
        batch_op.alter_column('total_amount', existing_type=sa.Float(), type_=sa.Numeric(15, 2), existing_nullable=False)

    with op.batch_alter_table('payments') as batch_op:
        batch_op.alter_column('amount', existing_type=sa.Float(), type_=sa.Numeric(15, 2), existing_nullable=False)

    with op.batch_alter_table('customer_payment_allocations') as batch_op:
        batch_op.alter_column('amount', existing_type=sa.Float(), type_=sa.Numeric(15, 2), existing_nullable=False)

    with op.batch_alter_table('sales_return_items') as batch_op:
        batch_op.alter_column('quantity', existing_type=sa.Float(), type_=sa.Numeric(15, 4), existing_nullable=False)


def downgrade():
    with op.batch_alter_table('sales_return_items') as batch_op:
        batch_op.alter_column('quantity', existing_type=sa.Numeric(15, 4), type_=sa.Float(), existing_nullable=False)

    with op.batch_alter_table('customer_payment_allocations') as batch_op:
        batch_op.alter_column('amount', existing_type=sa.Numeric(15, 2), type_=sa.Float(), existing_nullable=False)

    with op.batch_alter_table('payments') as batch_op:
        batch_op.alter_column('amount', existing_type=sa.Numeric(15, 2), type_=sa.Float(), existing_nullable=False)

    with op.batch_alter_table('invoices') as batch_op:
        batch_op.alter_column('total_amount', existing_type=sa.Numeric(15, 2), type_=sa.Float(), existing_nullable=False)

    with op.batch_alter_table('shipment_items') as batch_op:
        batch_op.alter_column('quantity', existing_type=sa.Numeric(15, 4), type_=sa.Float(), existing_nullable=False)
        batch_op.alter_column('unit_price', existing_type=sa.Numeric(15, 2), type_=sa.Float(), existing_nullable=False)

    with op.batch_alter_table('sales_order_items') as batch_op:
        batch_op.alter_column('quantity', existing_type=sa.Numeric(15, 4), type_=sa.Float(), existing_nullable=False)
        batch_op.alter_column('unit_price', existing_type=sa.Numeric(15, 2), type_=sa.Float(), existing_nullable=False)
        batch_op.alter_column('total_price', existing_type=sa.Numeric(15, 2), type_=sa.Float(), existing_nullable=False)

    with op.batch_alter_table('sales_orders') as batch_op:
        batch_op.alter_column('total_amount', existing_type=sa.Numeric(15, 2), type_=sa.Float(), existing_nullable=True)
        batch_op.alter_column('total_qty', existing_type=sa.Numeric(15, 4), type_=sa.Float(), existing_nullable=True)

    with op.batch_alter_table('supplier_payment_allocations') as batch_op:
        batch_op.alter_column('amount', existing_type=sa.Numeric(15, 2), type_=sa.Float(), existing_nullable=False)

    with op.batch_alter_table('supplier_payments') as batch_op:
        batch_op.alter_column('amount', existing_type=sa.Numeric(15, 2), type_=sa.Float(), existing_nullable=False)

    with op.batch_alter_table('vendor_bills') as batch_op:
        batch_op.alter_column('total_amount', existing_type=sa.Numeric(15, 2), type_=sa.Float(), existing_nullable=False)

    with op.batch_alter_table('goods_receipt_items') as batch_op:
        batch_op.alter_column('quantity', existing_type=sa.Numeric(15, 4), type_=sa.Float(), existing_nullable=False)
        batch_op.alter_column('unit_cost', existing_type=sa.Numeric(15, 4), type_=sa.Float(), existing_nullable=False)

    with op.batch_alter_table('purchase_order_items') as batch_op:
        batch_op.alter_column('quantity', existing_type=sa.Numeric(15, 4), type_=sa.Float(), existing_nullable=False)
        batch_op.alter_column('unit_cost', existing_type=sa.Numeric(15, 4), type_=sa.Float(), existing_nullable=False)
        batch_op.alter_column('total_cost', existing_type=sa.Numeric(15, 2), type_=sa.Float(), existing_nullable=False)

    with op.batch_alter_table('purchase_orders') as batch_op:
        batch_op.alter_column('total_amount', existing_type=sa.Numeric(15, 2), type_=sa.Float(), existing_nullable=False)
        batch_op.alter_column('total_qty', existing_type=sa.Numeric(15, 4), type_=sa.Float(), existing_nullable=False)

    with op.batch_alter_table('stock_transfer_items') as batch_op:
        batch_op.alter_column('quantity', existing_type=sa.Numeric(15, 4), type_=sa.Float(), existing_nullable=False)

    with op.batch_alter_table('stock_movements') as batch_op:
        batch_op.alter_column('quantity_delta', existing_type=sa.Numeric(15, 4), type_=sa.Float(), existing_nullable=False)
        batch_op.alter_column('unit_cost', existing_type=sa.Numeric(15, 4), type_=sa.Float(), existing_nullable=False)

    with op.batch_alter_table('inventory_adjusters') as batch_op:
        batch_op.alter_column('quantity', existing_type=sa.Numeric(15, 4), type_=sa.Float(), existing_nullable=False)

    with op.batch_alter_table('inventory_balances') as batch_op:
        batch_op.alter_column('quantity_on_hand', existing_type=sa.Numeric(15, 4), type_=sa.Float(), existing_nullable=True)
        batch_op.alter_column('quantity_reserved', existing_type=sa.Numeric(15, 4), type_=sa.Float(), existing_nullable=True)
        batch_op.alter_column('average_cost', existing_type=sa.Numeric(15, 4), type_=sa.Float(), existing_nullable=True)
        batch_op.alter_column('last_cost', existing_type=sa.Numeric(15, 4), type_=sa.Float(), existing_nullable=True)

    with op.batch_alter_table('products') as batch_op:
        batch_op.alter_column('min_stock', existing_type=sa.Numeric(15, 4), type_=sa.Float(), existing_nullable=True)
