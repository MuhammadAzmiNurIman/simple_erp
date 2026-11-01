from app import db
from app.money import money_json


class CustomerPaymentAllocation(db.Model):
    __tablename__ = 'customer_payment_allocations'

    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id'), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)

    payment = db.relationship('Payment', back_populates='allocations')
    invoice = db.relationship('Invoice', back_populates='allocations')

    def to_dict(self):
        return {
            'id': self.id,
            'payment_id': self.payment_id,
            'invoice_id': self.invoice_id,
            'amount': money_json(self.amount),
        }
