# app/models/unit.py
# Model Unit untuk satuan mengukur
from app import db


class Unit(db.Model):
    __tablename__ = 'units'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)  # pcs, box, kg, liter, dsb
    symbol = db.Column(db.String(10), nullable=True)  # satuan simbol
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp()
    )

    products = db.relationship('Product', back_populates='unit', lazy='select')

    def __repr__(self):
        return f'<Unit {self.name}>'

    @property
    def product_count(self):
        """Jumlah produk menggunakan satuan ini"""
        return len(self.products)