# app/models/product.py
# Model Product untuk master data barang
from app import db
from .category import Category
from .unit import Unit


class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    unit_id = db.Column(db.Integer, db.ForeignKey('units.id'), nullable=True)
    sales_price = db.Column(db.Numeric(15, 2), nullable=True)
    min_stock = db.Column(db.Numeric(15, 4, asdecimal=False), default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp()
    )

    category = db.relationship('Category', back_populates='products', lazy='select')
    unit = db.relationship('Unit', back_populates='products', lazy='select')

    def __repr__(self):
        return f'<Product {self.sku} - {self.name}>'

    @property
    def total_value(self):
        """Calculate total inventory value for this product across all warehouses"""
        from app.models import InventoryBalance
        balances = InventoryBalance.query.filter_by(product_id=self.id).all()
        return sum(b.quantity_on_hand * b.average_cost for b in balances)
