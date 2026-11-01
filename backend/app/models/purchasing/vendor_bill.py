from app import db
from app.money import decimal_value, money_json, quantize_money


class VendorBill(db.Model):
    __tablename__ = 'vendor_bills'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False)
    goods_receipt_id = db.Column(
        db.Integer,
        db.ForeignKey('goods_receipts.id'),
        nullable=False,
        unique=True
    )
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    total_amount = db.Column(db.Numeric(15, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='OPEN')
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())

    goods_receipt = db.relationship('GoodsReceipt', back_populates='vendor_bill')
    supplier = db.relationship('Supplier')
    allocations = db.relationship(
        'SupplierPaymentAllocation',
        back_populates='vendor_bill',
        cascade='all, delete-orphan'
    )

    @property
    def amount_paid(self):
        return sum(
            (decimal_value(allocation.amount)
            for allocation in self.allocations
            if allocation.payment.status == 'POSTED'),
            decimal_value(0)
        )

    @property
    def balance_due(self):
        return max(
            decimal_value(0),
            quantize_money(decimal_value(self.total_amount) - self.amount_paid)
        )

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'goods_receipt_id': self.goods_receipt_id,
            'supplier_id': self.supplier_id,
            'total_amount': money_json(self.total_amount),
            'amount_paid': money_json(self.amount_paid),
            'balance_due': money_json(self.balance_due),
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
