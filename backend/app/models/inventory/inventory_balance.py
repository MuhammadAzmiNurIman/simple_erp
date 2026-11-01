# app/models/inventory_balance.py
# Model Inventory Balance - saldo stok per kombinasi product + warehouse
# KRUSIAL: Setiap saldo diidentifikasi oleh product_id + warehouse_id yang UNIQUE
from app import db
from app.money import decimal_value, money_json


class InventoryBalance(db.Model):
    __tablename__ = 'inventory_balances'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    quantity_on_hand = db.Column(db.Numeric(15, 4, asdecimal=False), default=0)  # Stok fisik total
    quantity_reserved = db.Column(db.Numeric(15, 4, asdecimal=False), default=0)  # Stok yang dipesan (untuk SO)
    average_cost = db.Column(db.Numeric(15, 4), default=0)  # Biaya rata-rata per unit
    last_cost = db.Column(db.Numeric(15, 4), default=0)  # Biaya terakhir (saat receipt/pembelian)
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())

    # UNIQUE Constraint: Satu product hanya bisa punya satu balance per warehouse
    __table_args__ = (
        db.UniqueConstraint('product_id', 'warehouse_id', name='uq_product_warehouse'),
    )

    # Relationship ke Product
    product = db.relationship('Product', backref='inv_balance', lazy='select')

    # Relationship ke Warehouse - with back_populates to match Warehouse.inventory_balances
    warehouse = db.relationship('Warehouse', back_populates='inventory_balances', lazy='select')

    # Property: Stok Tersedia = On Hand - Reserved
    @property
    def quantity_available(self):
        return max(0, self.quantity_on_hand - self.quantity_reserved)

    # Property: Nilai Total Stok = On Hand * Average Cost
    @property
    def total_value(self):
        return money_json(
            decimal_value(self.quantity_on_hand) * decimal_value(self.average_cost)
        )

    # Property: Sisa Reservasi = Berapa masih bisa di-reservasi
    @property
    def reserved_remaining(self):
        return max(0, self.quantity_on_hand - self.quantity_reserved)

    @classmethod
    def get_or_create(cls, product_id, warehouse_id, for_update=True, average_cost=0, last_cost=0):
        """
        Safely retrieves or atomically creates an InventoryBalance row.
        Prevents race conditions on unique constraint (uq_product_warehouse)
        by using a savepoint nested transaction if concurrent creation collides.
        """
        query = cls.query.filter_by(product_id=product_id, warehouse_id=warehouse_id)
        if for_update:
            balance = query.with_for_update().first()
        else:
            balance = query.first()

        if balance is not None:
            return balance

        try:
            with db.session.begin_nested():
                balance = cls(
                    product_id=product_id,
                    warehouse_id=warehouse_id,
                    quantity_on_hand=0,
                    quantity_reserved=0,
                    average_cost=average_cost,
                    last_cost=last_cost
                )
                db.session.add(balance)
                db.session.flush()
                return balance
        except Exception:
            query = cls.query.filter_by(product_id=product_id, warehouse_id=warehouse_id)
            if for_update:
                return query.with_for_update().first()
            return query.first()

    def __repr__(self):
        return f'<InventoryBalance P{self.product_id} W{self.warehouse_id} - OnHand:{self.quantity_on_hand} Reserved:{self.quantity_reserved}>'