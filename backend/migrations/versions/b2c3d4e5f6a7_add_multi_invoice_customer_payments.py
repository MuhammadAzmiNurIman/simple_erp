"""Support customer payments allocated across multiple invoices.

Revision ID: b2c3d4e5f6a7
Revises: a1d4e8c9b732
Create Date: 2026-10-25 17:10:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'b2c3d4e5f6a7'
down_revision = 'a1d4e8c9b732'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    invoice_columns = {
        column['name']
        for column in sa.inspect(connection).get_columns('invoices')
    }
    if 'sales_order_id' in invoice_columns:
        invoice_count = connection.execute(
            sa.text('SELECT COUNT(*) FROM invoices')
        ).scalar_one()
        if invoice_count:
            raise RuntimeError(
                'Cannot migrate legacy invoices: rows reference sales orders, '
                'but no historical shipment mapping exists.'
            )
        with op.batch_alter_table(
            'invoices',
            naming_convention={
                'fk': 'fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s',
                'uq': 'uq_%(table_name)s_%(column_0_name)s',
            }
        ) as batch_op:
            batch_op.drop_constraint(
                'fk_invoices_sales_order_id_sales_orders',
                type_='foreignkey'
            )
            batch_op.drop_constraint(
                'uq_invoices_sales_order_id',
                type_='unique'
            )
            batch_op.alter_column(
                'sales_order_id',
                new_column_name='shipment_id',
                existing_type=sa.Integer(),
                nullable=False
            )
            batch_op.create_foreign_key(
                'fk_invoices_shipment_id_shipments',
                'shipments',
                ['shipment_id'],
                ['id']
            )
            batch_op.create_unique_constraint(
                'uq_invoices_shipment_id',
                ['shipment_id']
            )

    payment_inspector = sa.inspect(connection)
    payment_columns = {
        column['name']: column
        for column in payment_inspector.get_columns('payments')
    }
    payment_foreign_key_columns = {
        column
        for constraint in payment_inspector.get_foreign_keys('payments')
        for column in constraint['constrained_columns']
    }
    payment_indexes = {
        index['name'] for index in payment_inspector.get_indexes('payments')
    }
    status_was_missing = 'status' not in payment_columns
    with op.batch_alter_table('payments') as batch_op:
        if 'customer_id' not in payment_columns:
            batch_op.add_column(sa.Column('customer_id', sa.Integer(), nullable=True))
        if status_was_missing:
            batch_op.add_column(sa.Column(
                'status',
                sa.String(length=20),
                nullable=True
            ))
        if not payment_columns['invoice_id']['nullable']:
            batch_op.alter_column(
                'invoice_id',
                existing_type=sa.Integer(),
                nullable=True
            )
        if 'customer_id' not in payment_foreign_key_columns:
            batch_op.create_foreign_key(
                'fk_payments_customer_id_customers',
                'customers',
                ['customer_id'],
                ['id']
            )
        if 'ix_payments_customer_id' not in payment_indexes:
            batch_op.create_index('ix_payments_customer_id', ['customer_id'])

    op.execute(sa.text("""
        UPDATE payments
        SET customer_id = (
            SELECT sales_orders.customer_id
            FROM invoices
            JOIN shipments ON shipments.id = invoices.shipment_id
            JOIN sales_orders ON sales_orders.id = shipments.sales_order_id
            WHERE invoices.id = payments.invoice_id
        )
        WHERE customer_id IS NULL
    """))

    with op.batch_alter_table('payments') as batch_op:
        if status_was_missing:
            batch_op.alter_column(
                'status',
                existing_type=sa.String(length=20),
                nullable=False
            )
        batch_op.alter_column(
            'customer_id',
            existing_type=sa.Integer(),
            nullable=False
        )


def downgrade():
    connection = op.get_bind()
    unrepresentable_payments = connection.execute(sa.text("""
        SELECT COUNT(*)
        FROM payments
        WHERE invoice_id IS NULL
           OR id IN (
               SELECT payment_id
               FROM customer_payment_allocations
               GROUP BY payment_id
               HAVING COUNT(DISTINCT invoice_id) > 1
           )
    """)).scalar_one()
    if unrepresentable_payments:
        raise RuntimeError(
            'Cannot downgrade: customer payments are not representable as '
            'single-invoice payments.'
        )

    with op.batch_alter_table('payments') as batch_op:
        batch_op.drop_index('ix_payments_customer_id')
        batch_op.drop_constraint(
            'fk_payments_customer_id_customers',
            type_='foreignkey'
        )
        batch_op.drop_column('customer_id')
        batch_op.alter_column(
            'invoice_id',
            existing_type=sa.Integer(),
            nullable=False
        )
