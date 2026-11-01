# app/routes/inventory.py
# CRUD Inventory Balance - Stok per Product + Warehouse
import math

from flask import Blueprint, current_app, request, jsonify
from app import db, ma
from app.money import cost_json, decimal_value, money_json
from app.models import Product, Warehouse, InventoryBalance, StockMovement
from app.schemas import inventory_balance_schema, inventory_balances_schema

bp = Blueprint('inventory', __name__)


@bp.route('/inventory/balances', methods=['GET', 'POST'])
def manage_inventory_balances():
    """Get or create inventory balances"""
    if request.method == 'POST':
        # Create new inventory balance
        try:
            data = request.get_json()
            if not isinstance(data, dict):
                return jsonify({'error': 'A JSON object is required'}), 400

            product_id = data.get('product_id')
            warehouse_id = data.get('warehouse_id')
            quantity_on_hand = data.get('quantity_on_hand', 0)
            average_cost = data.get('average_cost', 0)

            if (
                not isinstance(product_id, int) or isinstance(product_id, bool)
                or not isinstance(warehouse_id, int) or isinstance(warehouse_id, bool)
            ):
                return jsonify({'error': 'product_id and warehouse_id are required'}), 400
            for field, value in (
                ('quantity_on_hand', quantity_on_hand),
                ('average_cost', average_cost)
            ):
                if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(value)
                    or value < 0
                ):
                    return jsonify({'error': f'{field} must be a non-negative number'}), 400

            product = db.session.get(Product, product_id)
            warehouse = db.session.get(Warehouse, warehouse_id)
            if not product or not product.is_active:
                return jsonify({'error': 'Active product not found'}), 404
            if not warehouse or not warehouse.is_active:
                return jsonify({'error': 'Active warehouse not found'}), 404

            # Check if inventory balance already exists (unique constraint)
            existing = InventoryBalance.query.filter_by(
                product_id=product_id, warehouse_id=warehouse_id
            ).first()
            if existing:
                return jsonify({'error': 'Inventory balance already exists for this product and warehouse'}), 409

            balance = InventoryBalance(
                product_id=product_id,
                warehouse_id=warehouse_id,
                quantity_on_hand=quantity_on_hand,
                average_cost=average_cost,
                last_cost=average_cost
            )
            db.session.add(balance)
            db.session.flush()
            if quantity_on_hand > 0:
                db.session.add(StockMovement(
                    product_id=product_id,
                    warehouse_id=warehouse_id,
                    movement_type='IN',
                    quantity_delta=quantity_on_hand,
                    unit_cost=average_cost,
                    reference_type='OPENING_BALANCE',
                    reference_id=balance.id,
                    created_by=request.current_user.id
                ))
            db.session.commit()
            return jsonify({
                'message': 'Inventory balance created successfully',
                'data': inventory_balance_schema.dump(balance)
            }), 201
        except Exception:
            db.session.rollback()
            current_app.logger.exception('Inventory balance creation failed')
            return jsonify({'error': 'Unable to create inventory balance'}), 500

    # GET logic
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    product_filter = request.args.get('product_id', type=int)
    warehouse_filter = request.args.get('warehouse_id', type=int)
    active_only = request.args.get('active', 'true', type=str).lower() == 'true'

    query = InventoryBalance.query

    if warehouse_filter:
        query = query.filter_by(warehouse_id=warehouse_filter)

    if product_filter:
        query = query.filter_by(product_id=product_filter)

    if active_only:
        # Filter by products that are active
        query = query.join(Product).filter(Product.is_active == True)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    balances = pagination.items

    return jsonify({
        'data': inventory_balances_schema.dump(balances),
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
    })


@bp.route('/inventory/balances/<int:balance_id>', methods=['GET'])
def get_inventory_balance(balance_id):
    """Get single inventory balance"""
    balance = db.get_or_404(InventoryBalance, balance_id)
    return jsonify({
        'data': inventory_balance_schema.dump(balance)
    })


# Property methods accessible via GET params
@bp.route('/inventory/summary', methods=['GET'])
def get_inventory_summary():
    """Get inventory summary per warehouse"""
    warehouse_id = request.args.get('warehouse_id', type=int)

    from sqlalchemy import func
    query = db.session.query(
        InventoryBalance.warehouse_id,
        InventoryBalance.product_id,
        InventoryBalance.quantity_on_hand,
        InventoryBalance.quantity_reserved,
        InventoryBalance.average_cost,
        Product.name.label('product_name'),
        Warehouse.code.label('warehouse_code')
    ).join(Product, InventoryBalance.product_id == Product.id
    ).join(Warehouse, InventoryBalance.warehouse_id == Warehouse.id)

    if warehouse_id:
        query = query.filter(InventoryBalance.warehouse_id == warehouse_id)

    results = query.all()

    summary = []
    for row in results:
        available = max(0, row.quantity_on_hand - row.quantity_reserved)
        summary.append({
            'warehouse_code': row.warehouse_code,
            'product_name': row.product_name,
            'on_hand': row.quantity_on_hand,
            'reserved': row.quantity_reserved,
            'available': available,
            'average_cost': cost_json(row.average_cost),
            'total_value': money_json(
                decimal_value(row.quantity_on_hand) * decimal_value(row.average_cost)
            )
        })

    return jsonify({'data': summary})
