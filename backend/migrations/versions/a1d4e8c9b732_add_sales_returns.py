"""Add sales return records and items.

Revision ID: a1d4e8c9b732
Revises: 5f2e8b9c14a7
Create Date: 2026-10-25 16:55:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'a1d4e8c9b732'
down_revision = '5f2e8b9c14a7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'sales_returns',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('return_number', sa.String(length=40), nullable=False),
        sa.Column('shipment_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('posted_by', sa.Integer(), nullable=True),
        sa.Column('posted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['posted_by'], ['users.id']),
        sa.ForeignKeyConstraint(['shipment_id'], ['shipments.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('return_number'),
        sa.Index('ix_sales_returns_shipment_id', 'shipment_id')
    )
    op.create_table(
        'sales_return_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sales_return_id', sa.Integer(), nullable=False),
        sa.Column('shipment_item_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('disposition', sa.String(length=20), nullable=False),
        sa.CheckConstraint(
            'quantity > 0',
            name='ck_sales_return_items_quantity'
        ),
        sa.CheckConstraint(
            "disposition IN ('RESTOCK', 'DAMAGED')",
            name='ck_sales_return_items_disposition'
        ),
        sa.ForeignKeyConstraint(['sales_return_id'], ['sales_returns.id']),
        sa.ForeignKeyConstraint(['shipment_item_id'], ['shipment_items.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_sales_return_items_sales_return_id', 'sales_return_id'),
        sa.Index('ix_sales_return_items_shipment_item_id', 'shipment_item_id')
    )


def downgrade():
    op.drop_table('sales_return_items')
    op.drop_table('sales_returns')
