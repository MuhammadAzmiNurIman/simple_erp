# app/routes/stock_movements.py
# CRUD Stock Movements - Ledger Pergerakan Stok
from flask import Blueprint, request, jsonify
from app import db, ma
from app.models import Product, Warehouse, StockMovement
from app.schemas import stock_movement_schema, stock_movements_schema

bp = Blueprint('stock_movements', __name__)


@bp.route('/inventory/movements', methods=['GET'])
@bp.route('/movements', methods=['GET'])
def get_stock_movements():
    """Get stock movements with pagination and filtering"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    product_filter = request.args.get('product_id', type=int)
    warehouse_filter = request.args.get('warehouse_id', type=int)
    category_filter = request.args.get('category_id', type=int)
    movement_type_filter = request.args.get('movement_type', type=str)
    from_date = request.args.get('from_date', type=str)
    to_date = request.args.get('to_date', type=str)

    query = StockMovement.query

    if product_filter:
        query = query.filter_by(product_id=product_filter)

    if category_filter is not None:
        query = query.join(Product).filter(Product.category_id == category_filter)

    if warehouse_filter:
        query = query.filter_by(warehouse_id=warehouse_filter)

    if movement_type_filter:
        query = query.filter_by(movement_type=movement_type_filter)

    if from_date:
        query = query.filter(StockMovement.created_at >= from_date)

    if to_date:
        query = query.filter(StockMovement.created_at <= to_date)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    movements = pagination.items

    return jsonify({
        'data': stock_movements_schema.dump(movements),
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
    })


@bp.route('/inventory/movements/<int:movement_id>', methods=['GET'])
@bp.route('/movements/<int:movement_id>', methods=['GET'])
def get_stock_movement(movement_id):
    """Get single stock movement"""
    movement = db.get_or_404(StockMovement, movement_id)
    return jsonify({
        'data': stock_movement_schema.dump(movement)
    })