from app import db
from app.money import decimal_value, money_json, quantize_money


class SupplierPayment(db.Model):
    __tablename__ = 'supplier_payments'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    source_vendor_bill_id = db.Column(
        db.Integer, db.ForeignKey('vendor_bills.id'), nullable=True, index=True
    )
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    payment_method = db.Column(db.String(30), nullable=False)
    payment_date = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    status = db.Column(db.String(20), nullable=False, default='DRAFT')
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())

    supplier = db.relationship('Supplier')
    source_vendor_bill = db.relationship('VendorBill')
    allocations = db.relationship(
        'SupplierPaymentAllocation',
        back_populates='payment',
        cascade='all, delete-orphan'
    )

    @property
    def allocated_amount(self):
        return sum(
            (decimal_value(allocation.amount) for allocation in self.allocations),
            decimal_value(0)
        )

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'supplier_id': self.supplier_id,
            'source_vendor_bill_id': self.source_vendor_bill_id,
            'supplier_code': self.supplier.code,
            'supplier_name': self.supplier.name,
            'supplier_email': self.supplier.email,
            'supplier_phone': self.supplier.phone,
            'supplier_address': self.supplier.address,
            'amount': money_json(self.amount),
            'allocated_amount': money_json(self.allocated_amount),
            'unallocated_amount': money_json(
                max(decimal_value(0), quantize_money(
                    decimal_value(self.amount) - self.allocated_amount
                ))
            ),
            'payment_method': self.payment_method,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'allocations': [
                {
                    **allocation.to_dict(),
                    'vendor_bill_code': allocation.vendor_bill.code,
                }
                for allocation in self.allocations
            ],
        }


class SupplierPaymentAllocation(db.Model):
    __tablename__ = 'supplier_payment_allocations'

    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(
        db.Integer,
        db.ForeignKey('supplier_payments.id'),
        nullable=False
    )
    vendor_bill_id = db.Column(db.Integer, db.ForeignKey('vendor_bills.id'), nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)

    payment = db.relationship('SupplierPayment', back_populates='allocations')
    vendor_bill = db.relationship('VendorBill', back_populates='allocations')

    def to_dict(self):
        return {
            'id': self.id,
            'payment_id': self.payment_id,
            'vendor_bill_id': self.vendor_bill_id,
            'amount': money_json(self.amount),
        }
