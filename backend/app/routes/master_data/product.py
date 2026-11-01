# app/routes/product.py
# CRUD Produk - Master Data Barang
import math

from flask import Blueprint, current_app, request, jsonify
from app import db, ma
from app.models import Product, Category, Unit
from app.schemas import product_schema, products_schema

bp = Blueprint('product', __name__)


@bp.route('/products', methods=['GET'])
def get_products():
    """Get all products with pagination and filtering"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    name_filter = request.args.get('name', '', type=str)
    category_filter = request.args.get('category_id', type=int)
    unit_filter = request.args.get('unit_id', type=int)
    active_only = request.args.get('active', 'true', type=str).lower() == 'true'

    query = Product.query

    if active_only:
        query = query.filter_by(is_active=True)

    if name_filter:
        query = query.filter(Product.name.ilike(f'%{name_filter}%'))

    if category_filter:
        query = query.filter_by(category_id=category_filter)

    if unit_filter:
        query = query.filter_by(unit_id=unit_filter)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    products = pagination.items

    return jsonify({
        'data': products_schema.dump(products),
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
    })


@bp.route('/products', methods=['POST'])
def create_product():
    """Create new product"""
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({'error': 'A JSON object is required'}), 400
    sku = data.get('sku')
    name = data.get('name')
    category_id = data.get('category_id')
    unit_id = data.get('unit_id')
    sales_price = data.get('sales_price')
    min_stock = data.get('min_stock', 0)

    if not isinstance(sku, str) or not sku.strip() or len(sku) > 50:
        return jsonify({'error': 'SKU is required'}), 400
    if not isinstance(name, str) or not name.strip() or len(name) > 100:
        return jsonify({'error': 'Product name is required'}), 400
    if (
        isinstance(min_stock, bool)
        or not isinstance(min_stock, (int, float))
        or not math.isfinite(min_stock)
        or min_stock < 0
    ):
        return jsonify({'error': 'min_stock must be a non-negative number'}), 400
    if sales_price is not None and (
        isinstance(sales_price, bool)
        or not isinstance(sales_price, (int, float))
        or not math.isfinite(sales_price)
        or sales_price < 0
    ):
        return jsonify({'error': 'sales_price must be a non-negative number'}), 400
    if category_id is not None and (
        not isinstance(category_id, int) or isinstance(category_id, bool)
    ):
        return jsonify({'error': 'category_id must be an integer or null'}), 400
    if unit_id is not None and (
        not isinstance(unit_id, int) or isinstance(unit_id, bool)
    ):
        return jsonify({'error': 'unit_id must be an integer or null'}), 400

    # Validate category exists if provided
    if category_id:
        from app.models import Category
        category = db.session.get(Category, category_id)
        if not category or not category.is_active:
            return jsonify({'error': 'Invalid category'}), 400

    # Validate unit exists if provided
    if unit_id:
        from app.models import Unit
        unit = db.session.get(Unit, unit_id)
        if not unit or not unit.is_active:
            return jsonify({'error': 'Invalid unit'}), 400

    # Check if SKU already exists
    existing = Product.query.filter_by(sku=sku).first()
    if existing:
        return jsonify({'error': 'SKU already exists'}), 409

    product = Product(
        sku=sku.strip(),
        name=name.strip(),
        category_id=category_id if category_id else None,
        unit_id=unit_id if unit_id else None,
        sales_price=sales_price,
        min_stock=min_stock if min_stock else 0,
        is_active=True
    )
    try:
        db.session.add(product)
        db.session.commit()

        return jsonify({
            'message': 'Product created successfully',
            'data': product_schema.dump(product)
        }), 201
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Product creation failed')
        return jsonify({'error': 'Unable to create product'}), 500


@bp.route('/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """Get single product"""
    product = db.get_or_404(Product, product_id)
    return jsonify({
        'data': product_schema.dump(product)
    })


@bp.route('/products/<int:product_id>', methods=['PATCH'])
def update_product(product_id):
    """Update product"""
    product = db.get_or_404(Product, product_id)
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({'error': 'A JSON object is required'}), 400

    if 'sku' in data:
        if not isinstance(data['sku'], str) or not data['sku'].strip() or len(data['sku']) > 50:
            return jsonify({'error': 'SKU is required and must be at most 50 characters'}), 400
        # Check if new SKU conflicts
        existing = Product.query.filter(
            Product.sku == data['sku'].strip(),
            Product.id != product_id
        ).first()
        if existing:
            return jsonify({'error': 'SKU already exists'}), 409
        product.sku = data['sku'].strip()

    if 'name' in data:
        if not isinstance(data['name'], str) or not data['name'].strip() or len(data['name']) > 100:
            return jsonify({'error': 'Product name is required and must be at most 100 characters'}), 400
        product.name = data['name'].strip()

    if 'category_id' in data:
        from app.models import Category
        if data['category_id'] is None:
            product.category_id = None
        else:
            if not isinstance(data['category_id'], int) or isinstance(data['category_id'], bool):
                return jsonify({'error': 'category_id must be an integer or null'}), 400
            category = db.session.get(Category, data['category_id'])
            if not category or not category.is_active:
                return jsonify({'error': 'Invalid category'}), 400
            product.category_id = data['category_id']

    if 'unit_id' in data:
        from app.models import Unit
        if data['unit_id'] is None:
            product.unit_id = None
        else:
            if not isinstance(data['unit_id'], int) or isinstance(data['unit_id'], bool):
                return jsonify({'error': 'unit_id must be an integer or null'}), 400
            unit = db.session.get(Unit, data['unit_id'])
            if not unit or not unit.is_active:
                return jsonify({'error': 'Invalid unit'}), 400
            product.unit_id = data['unit_id']

    if 'sales_price' in data:
        sales_price = data['sales_price']
        if sales_price is not None and (
            isinstance(sales_price, bool)
            or not isinstance(sales_price, (int, float))
            or not math.isfinite(sales_price)
            or sales_price < 0
        ):
            return jsonify({'error': 'sales_price must be a non-negative number or null'}), 400
        product.sales_price = sales_price

    if 'min_stock' in data:
        min_stock = data['min_stock']
        if (
            isinstance(min_stock, bool)
            or not isinstance(min_stock, (int, float))
            or not math.isfinite(min_stock)
            or min_stock < 0
        ):
            return jsonify({'error': 'min_stock must be a non-negative number'}), 400
        product.min_stock = min_stock

    try:
        db.session.commit()
        return jsonify({
            'message': 'Product updated successfully',
            'data': product_schema.dump(product)
        })
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Product update failed')
        return jsonify({'error': 'Unable to update product'}), 500


@bp.route('/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """Soft delete product"""
    product = db.get_or_404(Product, product_id)
    try:
        product.is_active = False
        db.session.commit()
        return jsonify({'message': 'Product deactivated successfully'})
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Product deactivation failed')
        return jsonify({'error': 'Unable to deactivate product'}), 500
