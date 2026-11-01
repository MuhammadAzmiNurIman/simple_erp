# app/models/sales_order.py
# Model Sales Order dan Item untuk modul Sales
from app import db
from app.money import money_json
from datetime import datetime


class SalesOrder(db.Model):
    __tablename__ = 'sales_orders'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, default='SO-001')
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='DRAFT')
    # DRAFT → RESERVED → SHIPPED → INVOICED → CLOSED
    total_amount = db.Column(db.Numeric(15, 2), default=0)
    total_qty = db.Column(db.Numeric(15, 4, asdecimal=False), default=0.0)
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_at = db.Column(db.DateTime)
    rejected_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    rejected_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    # Relationships
    customer = db.relationship('Customer', backref='sales_orders')
    warehouse = db.relationship('Warehouse', backref='sales_orders')
    created_by_user = db.relationship('User', foreign_keys=[created_by])
    approved_by_user = db.relationship('User', foreign_keys=[approved_by])
    rejected_by_user = db.relationship('User', foreign_keys=[rejected_by])
    items = db.relationship('SalesOrderItem', backref='sales_order', cascade='all, delete-orphan')
    shipments = db.relationship(
        'Shipment',
        back_populates='sales_order',
        cascade='all, delete-orphan'
    )

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'customer_id': self.customer_id,
            'warehouse_id': self.warehouse_id,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'status': self.status,
            'total_amount': money_json(self.total_amount),
            'total_qty': self.total_qty,
            'notes': self.notes,
            'created_by': self.created_by,
            'approved_by': self.approved_by,
            'approved_by_username': self.approved_by_user.username if self.approved_by_user else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'rejected_by': self.rejected_by,
            'rejected_by_username': self.rejected_by_user.username if self.rejected_by_user else None,
            'rejected_at': self.rejected_at.isoformat() if self.rejected_at else None,
            'shipped_qty': self.shipped_qty,
            'remaining_qty': self.remaining_qty,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'items': [item.to_dict() for item in self.items]
        }

    @property
    def shipped_qty(self):
        return sum(item.shipped_qty for item in self.items)

    @property
    def remaining_qty(self):
        return max(0, self.total_qty - self.shipped_qty)

    def __repr__(self):
        return f'<SalesOrder {self.code}: {self.status}>'


class SalesOrderItem(db.Model):
    __tablename__ = 'sales_order_items'

    id = db.Column(db.Integer, primary_key=True)
    sales_order_id = db.Column(db.Integer, db.ForeignKey('sales_orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Numeric(15, 4, asdecimal=False), nullable=False)
    unit_price = db.Column(db.Numeric(15, 2), nullable=False)
    total_price = db.Column(db.Numeric(15, 2), nullable=False)

    # Relationships
    product = db.relationship('Product', backref='sales_order_items')
    shipment_items = db.relationship('ShipmentItem', back_populates='sales_order_item')

    @property
    def shipped_qty(self):
        return sum(
            shipment_item.quantity
            for shipment_item in self.shipment_items
            if shipment_item.shipment.status == 'POSTED'
        )

    def to_dict(self):
        return {
            'id': self.id,
            'sales_order_id': self.sales_order_id,
            'product_id': self.product_id,
            'sku': self.product.sku,
            'product_name': self.product.name,
            'unit': self.product.unit.name if self.product.unit else None,
            'quantity': self.quantity,
            'shipped_qty': self.shipped_qty,
            'remaining_qty': max(0, self.quantity - sum(
                shipment_item.quantity
                for shipment_item in self.shipment_items
                if shipment_item.shipment.status in {'DRAFT', 'POSTED'}
            )),
            'unit_price': money_json(self.unit_price),
            'total_price': money_json(self.total_price)
        }

    def __repr__(self):
        return f'<SalesOrderItem {self.product_id} x {self.quantity} >'
