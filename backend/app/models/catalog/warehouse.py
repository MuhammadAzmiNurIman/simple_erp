# app/models/warehouse.py
# Model Warehouse untuk mengelola multiple gudang dalam satu perusahaan
from app import db


class Warehouse(db.Model):
    __tablename__ = 'warehouses'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)  # Kode gudang unik (misal: WH-A, WH-B)
    name = db.Column(db.String(50), nullable=False)  # Nama gudang
    address = db.Column(db.String(200), nullable=True)  # Alamat opsional
    is_active = db.Column(db.Boolean, default=True)  # Status aktif/inaktif
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())

    # Relationship: Satu gudang memiliki many inventory balances
    # Gunakan back_populates untuk menghindari konflik nama
    inventory_balances = db.relationship(
        'InventoryBalance', back_populates='warehouse', lazy='select'
    )

    def __repr__(self):
        return f'<Warehouse {self.code} - {self.name}>'

    @property
    def active_status(self):
        return self.is_active

    @property
    def transfer_out_count(self):
        """Jumlah transfer keluar dari gudang ini (placeholder untuk fitur depan)"""
        return 0

    @property
    def transfer_in_count(self):
        """Jumlah transfer masuk ke gudang ini (placeholder untuk fitur depan)"""
        return 0