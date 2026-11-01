# app/models/inventory_adjuster.py
# Model Inventory Adjuster untuk penyesuaian stok
from app import db
from datetime import datetime


class InventoryAdjuster(db.Model):
    __tablename__ = 'inventory_adjusters'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, default='ADJ-001')
    inventory_balance_id = db.Column(db.Integer, db.ForeignKey('inventory_balances.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)

    # Tipe adjustment: ADD (menambah stok) atau REDUCE (mengurangi stok)
    adjustment_type = db.Column(db.String(10), nullable=False)  # 'ADD' or 'REDUCE'

    # Kuantitas adjustment
    quantity = db.Column(db.Numeric(15, 4, asdecimal=False), nullable=False)

    # Keterangan/deskripsi adjustment
    description = db.Column(db.Text, nullable=True)

    # Status validasi
    status = db.Column(db.String(20), nullable=False, default='PENDING')  # PENDING, APPROVED, REJECTED, POSTED
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewed_at = db.Column(db.DateTime)
    posted_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    posted_at = db.Column(db.DateTime)

    # Timestamps
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    # Relationships
    inventory_balance = db.relationship('InventoryBalance', backref='adjusters')
    product = db.relationship('Product', backref='adjusters')
    warehouse = db.relationship('Warehouse', backref='adjusters')
    creator = db.relationship('User', foreign_keys=[created_by])
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])
    poster = db.relationship('User', foreign_keys=[posted_by])

    def __repr__(self):
        return f'<InventoryAdjuster {self.code}: {self.adjustment_type} {self.quantity}>'

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'inventory_balance_id': self.inventory_balance_id,
            'product_id': self.product_id,
            'warehouse_id': self.warehouse_id,
            'adjustment_type': self.adjustment_type,
            'quantity': self.quantity,
            'description': self.description,
            'status': self.status,
            'created_by': self.created_by,
            'reviewed_by': self.reviewed_by,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'posted_by': self.posted_by,
            'posted_at': self.posted_at.isoformat() if self.posted_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }