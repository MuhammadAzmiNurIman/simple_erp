from app import db
from app.money import cost_json


class GoodsReceipt(db.Model):
    __tablename__ = 'goods_receipts'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False)
    purchase_order_id = db.Column(
        db.Integer,
        db.ForeignKey('purchase_orders.id'),
        nullable=False
    )
    received_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='DRAFT')
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    posted_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    posted_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())

    purchase_order = db.relationship('PurchaseOrder', back_populates='goods_receipts')
    items = db.relationship(
        'GoodsReceiptItem',
        back_populates='goods_receipt',
        cascade='all, delete-orphan'
    )
    created_by_user = db.relationship('User', foreign_keys=[created_by])
    posted_by_user = db.relationship('User', foreign_keys=[posted_by])
    vendor_bill = db.relationship('VendorBill', back_populates='goods_receipt', uselist=False)

    def to_dict(self):
        order = self.purchase_order
        return {
            'id': self.id,
            'code': self.code,
            'purchase_order_id': self.purchase_order_id,
            'purchase_order_code': order.code,
            'supplier_code': order.supplier.code,
            'supplier_name': order.supplier.name,
            'supplier_address': order.supplier.address,
            'warehouse_code': order.warehouse.code,
            'warehouse_name': order.warehouse.name,
            'received_date': self.received_date.isoformat(),
            'status': self.status,
            'notes': self.notes,
            'created_by': self.created_by,
            'posted_by': self.posted_by,
            'posted_at': self.posted_at.isoformat() if self.posted_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'items': [item.to_dict() for item in self.items],
            'vendor_bill_id': self.vendor_bill.id if self.vendor_bill else None,
        }


class GoodsReceiptItem(db.Model):
    __tablename__ = 'goods_receipt_items'

    id = db.Column(db.Integer, primary_key=True)
    goods_receipt_id = db.Column(
        db.Integer,
        db.ForeignKey('goods_receipts.id'),
        nullable=False
    )
    purchase_order_item_id = db.Column(
        db.Integer,
        db.ForeignKey('purchase_order_items.id'),
        nullable=False
    )
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Numeric(15, 4, asdecimal=False), nullable=False)
    unit_cost = db.Column(db.Numeric(15, 4), nullable=False)

    goods_receipt = db.relationship('GoodsReceipt', back_populates='items')
    purchase_order_item = db.relationship('PurchaseOrderItem')
    product = db.relationship('Product')

    def to_dict(self):
        return {
            'id': self.id,
            'purchase_order_item_id': self.purchase_order_item_id,
            'product_id': self.product_id,
            'sku': self.product.sku,
            'product_name': self.product.name,
            'unit': self.product.unit.name if self.product.unit else None,
            'quantity': self.quantity,
            'unit_cost': cost_json(self.unit_cost),
        }
