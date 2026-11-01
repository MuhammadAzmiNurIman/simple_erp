from app import db
from app.money import money_json


class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(
        db.Integer,
        db.ForeignKey('customers.id'),
        nullable=False,
        index=True
    )
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=True)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    payment_method = db.Column(db.String(30), nullable=False)
    payment_date = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    status = db.Column(db.String(20), nullable=False, default='DRAFT')
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())

    customer = db.relationship('Customer', backref='payments')
    invoice = db.relationship('Invoice', back_populates='payments')
    allocations = db.relationship(
        'CustomerPaymentAllocation',
        back_populates='payment',
        cascade='all, delete-orphan'
    )

    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'customer_code': self.customer.code,
            'customer_name': self.customer.name,
            'customer_email': self.customer.email,
            'customer_phone': self.customer.phone,
            'customer_address': self.customer.address,
            'invoice_id': self.invoice_id,
            'invoice_code': self.invoice.code if self.invoice else None,
            'amount': money_json(self.amount),
            'payment_method': self.payment_method,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'allocations': [
                {
                    **allocation.to_dict(),
                    'invoice_code': allocation.invoice.code,
                }
                for allocation in self.allocations
            ],
        }
