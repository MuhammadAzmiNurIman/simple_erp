from app import db


class SalesReturn(db.Model):
    __tablename__ = 'sales_returns'

    id = db.Column(db.Integer, primary_key=True)
    return_number = db.Column(db.String(40), unique=True, nullable=False)
    shipment_id = db.Column(
        db.Integer,
        db.ForeignKey('shipments.id'),
        nullable=False,
        index=True
    )
    status = db.Column(db.String(20), nullable=False, default='DRAFT')
    reason = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    posted_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    posted_at = db.Column(db.DateTime)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=db.func.current_timestamp()
    )

    shipment = db.relationship('Shipment', back_populates='returns')
    items = db.relationship(
        'SalesReturnItem',
        back_populates='sales_return',
        cascade='all, delete-orphan'
    )
    creator = db.relationship('User', foreign_keys=[created_by])
    poster = db.relationship('User', foreign_keys=[posted_by])

    def to_dict(self):
        return {
            'id': self.id,
            'return_number': self.return_number,
            'shipment_id': self.shipment_id,
            'shipment_code': self.shipment.code,
            'sales_order_id': self.shipment.sales_order_id,
            'customer_id': self.shipment.sales_order.customer_id,
            'warehouse_id': self.shipment.sales_order.warehouse_id,
            'status': self.status,
            'reason': self.reason,
            'created_by': self.created_by,
            'posted_by': self.posted_by,
            'posted_at': self.posted_at.isoformat() if self.posted_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'items': [item.to_dict() for item in self.items],
        }


class SalesReturnItem(db.Model):
    __tablename__ = 'sales_return_items'
    __table_args__ = (
        db.CheckConstraint('quantity > 0', name='ck_sales_return_items_quantity'),
        db.CheckConstraint(
            "disposition IN ('RESTOCK', 'DAMAGED')",
            name='ck_sales_return_items_disposition'
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    sales_return_id = db.Column(
        db.Integer,
        db.ForeignKey('sales_returns.id'),
        nullable=False,
        index=True
    )
    shipment_item_id = db.Column(
        db.Integer,
        db.ForeignKey('shipment_items.id'),
        nullable=False,
        index=True
    )
    quantity = db.Column(db.Numeric(15, 4, asdecimal=False), nullable=False)
    disposition = db.Column(db.String(20), nullable=False)

    sales_return = db.relationship('SalesReturn', back_populates='items')
    shipment_item = db.relationship('ShipmentItem')

    def to_dict(self):
        return {
            'id': self.id,
            'shipment_item_id': self.shipment_item_id,
            'product_id': self.shipment_item.product_id,
            'product_name': self.shipment_item.product.name,
            'quantity': self.quantity,
            'condition': self.disposition,
        }
