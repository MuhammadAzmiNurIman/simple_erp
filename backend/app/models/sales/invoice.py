from app import db
from app.money import decimal_value, money_json, quantize_money


class Invoice(db.Model):
    __tablename__ = 'invoices'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False)
    shipment_id = db.Column(
        db.Integer,
        db.ForeignKey('shipments.id'),
        nullable=False,
        unique=True
    )
    due_date = db.Column(db.Date, nullable=False)
    total_amount = db.Column(db.Numeric(15, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='OPEN')
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())

    shipment = db.relationship('Shipment', back_populates='invoice')
    payments = db.relationship('Payment', back_populates='invoice', cascade='all, delete-orphan')
    allocations = db.relationship(
        'CustomerPaymentAllocation',
        back_populates='invoice',
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
        order = self.shipment.sales_order
        return {
            'id': self.id,
            'code': self.code,
            'shipment_id': self.shipment_id,
            'shipment_code': self.shipment.code,
            'sales_order_id': order.id,
            'sales_order_code': order.code,
            'customer_id': order.customer_id,
            'customer_code': order.customer.code,
            'customer_name': order.customer.name,
            'customer_email': order.customer.email,
            'customer_phone': order.customer.phone,
            'customer_address': order.customer.address,
            'warehouse_id': order.warehouse_id,
            'warehouse_code': order.warehouse.code,
            'warehouse_name': order.warehouse.name,
            'due_date': self.due_date.isoformat(),
            'total_amount': money_json(self.total_amount),
            'amount_paid': money_json(self.amount_paid),
            'balance_due': money_json(self.balance_due),
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'items': [
                {
                    'product_id': item.product_id,
                    'sku': item.product.sku,
                    'product_name': item.product.name,
                    'unit': item.product.unit.name if item.product.unit else None,
                    'quantity': item.quantity,
                    'unit_price': money_json(item.unit_price),
                    'total_price': money_json(
                        decimal_value(item.unit_price) * decimal_value(item.quantity)
                    ),
                }
                for item in self.shipment.items
            ],
        }
