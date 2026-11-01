# app/models/stock_movement.py
# Model Stock Movement - Ledger pergerakan stok lengkap
# Setiap transaksi (pembelian, penjualan, transfer, penyesuaian) mencatat entry ini
from app import db
from datetime import datetime


class StockMovement(db.Model):
    __tablename__ = 'stock_movements'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    movement_type = db.Column(
        db.String(20), nullable=False
    )  # IN, OUT, ADJUSTMENT, TRANSFER_IN, TRANSFER_OUT, RETURN_IN
    quantity_delta = db.Column(db.Numeric(15, 4, asdecimal=False), nullable=False)  # Positif untuk Masuk, Negatif untuk Keluar
    unit_cost = db.Column(db.Numeric(15, 4), nullable=False)  # Harga per unit pada saat transaksi
    reference_type = db.Column(
        db.String(30), nullable=True
    )  # PURCHASE, SALE, ADJUSTMENT, TRANSFER
    reference_id = db.Column(db.Integer, nullable=True)  # ID dari tabel transaksi pembuat
    created_by = db.Column(db.Integer, nullable=True)  # User yang membuat (belum diintegrasi auth)
    created_at = db.Column(db.DateTime, default=db.func.now())

    # Relationship ke Product
    product = db.relationship('Product', backref='stock_movements', lazy='select')

    # Relationship ke Warehouse
    warehouse = db.relationship('Warehouse', backref='stock_movements', lazy='select')

    def __repr__(self):
        return (f'<StockMovement {self.movement_type} P{self.product_id} '
                f'W{self.warehouse_id} Qty:{self.quantity_delta} Cost:{self.unit_cost}>')

    # Property: Menentukan apakah movement adalah Masuk atau Keluar
    @property
    def is_inbound(self):
        return self.movement_type in ['IN', 'TRANSFER_IN']

    # Property: Menentukan apakah movement adalah Keluar
    @property
    def is_outbound(self):
        return self.movement_type in ['OUT', 'TRANSFER_OUT']

    # Property: Tipe movement yang valid
    @property
    def valid_types(self):
        return ['IN', 'OUT', 'ADJUSTMENT', 'TRANSFER_IN', 'TRANSFER_OUT', 'RETURN_IN']