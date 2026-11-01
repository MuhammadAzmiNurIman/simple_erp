# app/models/category.py
# Model Category untuk master data
from app import db


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp()
    )

    products = db.relationship('Product', back_populates='category', lazy='select')

    def __repr__(self):
        return f'<Category {self.name}>'

    @property
    def product_count(self):
        """Jumlah produk di kategori ini"""
        return len(self.products)