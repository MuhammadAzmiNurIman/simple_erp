from app import db
from app.money import money_json


class Shipment(db.Model):
    __tablename__ = 'shipments'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False)
    sales_order_id = db.Column(db.Integer, db.ForeignKey('sales_orders.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='DRAFT')
    shipped_at = db.Column(db.DateTime)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    posted_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())

    sales_order = db.relationship('SalesOrder', back_populates='shipments')
    items = db.relationship(
        'ShipmentItem',
        back_populates='shipment',
        cascade='all, delete-orphan'
    )
    invoice = db.relationship('Invoice', back_populates='shipment', uselist=False)
    returns = db.relationship('SalesReturn', back_populates='shipment')
    created_by_user = db.relationship('User', foreign_keys=[created_by])
    posted_by_user = db.relationship('User', foreign_keys=[posted_by])

    def to_dict(self):
        order = self.sales_order
        return {
            'id': self.id,
            'code': self.code,
            'sales_order_id': self.sales_order_id,
            'sales_order_code': order.code,
            'customer_code': order.customer.code,
            'customer_name': order.customer.name,
            'customer_phone': order.customer.phone,
            'customer_address': order.customer.address,
            'warehouse_code': order.warehouse.code,
            'warehouse_name': order.warehouse.name,
            'status': self.status,
            'shipped_at': self.shipped_at.isoformat() if self.shipped_at else None,
            'created_by': self.created_by,
            'posted_by': self.posted_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'items': [item.to_dict() for item in self.items],
            'invoice_id': self.invoice.id if self.invoice else None,
        }


class ShipmentItem(db.Model):
    __tablename__ = 'shipment_items'

    id = db.Column(db.Integer, primary_key=True)
    shipment_id = db.Column(db.Integer, db.ForeignKey('shipments.id'), nullable=False)
    sales_order_item_id = db.Column(
        db.Integer,
        db.ForeignKey('sales_order_items.id'),
        nullable=False
    )
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Numeric(15, 4, asdecimal=False), nullable=False)
    unit_price = db.Column(db.Numeric(15, 2), nullable=False)
    # Weighted-average inventory cost captured when the shipment is posted.
    # Nullable for shipments created before this field was introduced.
    unit_cost = db.Column(db.Numeric(15, 4))

    shipment = db.relationship('Shipment', back_populates='items')
    sales_order_item = db.relationship('SalesOrderItem', back_populates='shipment_items')
    product = db.relationship('Product')

    def to_dict(self):
        return {
            'id': self.id,
            'sales_order_item_id': self.sales_order_item_id,
            'product_id': self.product_id,
            'sku': self.product.sku,
            'product_name': self.product.name,
            'unit': self.product.unit.name if self.product.unit else None,
            'quantity': self.quantity,
            'unit_price': money_json(self.unit_price),
        }
