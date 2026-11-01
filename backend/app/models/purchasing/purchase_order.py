from app import db
from app.money import money_json


class PurchaseOrder(db.Model):
    __tablename__ = 'purchase_orders'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), unique=True, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    order_date = db.Column(db.Date, nullable=False, default=db.func.current_date())
    status = db.Column(db.String(20), nullable=False, default='DRAFT')
    total_amount = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    total_qty = db.Column(db.Numeric(15, 4, asdecimal=False), nullable=False, default=0)
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_at = db.Column(db.DateTime)
    rejected_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    rejected_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp()
    )

    supplier = db.relationship('Supplier')
    warehouse = db.relationship('Warehouse')
    created_by_user = db.relationship('User', foreign_keys=[created_by])
    approved_by_user = db.relationship('User', foreign_keys=[approved_by])
    rejected_by_user = db.relationship('User', foreign_keys=[rejected_by])
    items = db.relationship(
        'PurchaseOrderItem',
        back_populates='purchase_order',
        cascade='all, delete-orphan'
    )
    goods_receipts = db.relationship(
        'GoodsReceipt',
        back_populates='purchase_order',
        cascade='all, delete-orphan'
    )

    @property
    def received_qty(self):
        return sum(item.received_qty for item in self.items)

    @property
    def remaining_qty(self):
        return max(0, self.total_qty - self.received_qty)

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'supplier_id': self.supplier_id,
            'supplier_code': self.supplier.code,
            'supplier_name': self.supplier.name,
            'supplier_email': self.supplier.email,
            'supplier_phone': self.supplier.phone,
            'supplier_address': self.supplier.address,
            'warehouse_id': self.warehouse_id,
            'warehouse_code': self.warehouse.code,
            'warehouse_name': self.warehouse.name,
            'order_date': self.order_date.isoformat() if self.order_date else None,
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
            'received_qty': self.received_qty,
            'remaining_qty': self.remaining_qty,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'items': [
                {
                    **item.to_dict(),
                    'received_qty': item.received_qty,
                    'remaining_qty': item.remaining_qty,
                }
                for item in self.items
            ],
        }


class PurchaseOrderItem(db.Model):
    __tablename__ = 'purchase_order_items'

    id = db.Column(db.Integer, primary_key=True)
    purchase_order_id = db.Column(
        db.Integer,
        db.ForeignKey('purchase_orders.id'),
        nullable=False
    )
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Numeric(15, 4, asdecimal=False), nullable=False)
    unit_cost = db.Column(db.Numeric(15, 4), nullable=False)
    total_cost = db.Column(db.Numeric(15, 2), nullable=False)

    purchase_order = db.relationship('PurchaseOrder', back_populates='items')
    product = db.relationship('Product')
    goods_receipt_items = db.relationship('GoodsReceiptItem', back_populates='purchase_order_item')

    @property
    def received_qty(self):
        return sum(
            receipt_item.quantity
            for receipt_item in self.goods_receipt_items
            if receipt_item.goods_receipt.status == 'POSTED'
        )

    @property
    def remaining_qty(self):
        return max(0, self.quantity - self.received_qty)

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'sku': self.product.sku,
            'product_name': self.product.name,
            'unit': self.product.unit.name if self.product.unit else None,
            'quantity': self.quantity,
            'unit_cost': float(self.unit_cost),
            'total_cost': money_json(self.total_cost),
        }
