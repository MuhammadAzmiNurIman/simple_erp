import math
from uuid import uuid4

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import func

from app import db
from app.money import decimal_value, quantize_cost
from app.models import (
    InventoryBalance, InventoryQuarantine, SalesReturn, SalesReturnItem,
    Shipment, ShipmentItem, StockMovement, SalesOrder
)


bp = Blueprint('sales_returns', __name__)
VALID_CONDITIONS = {'RESTOCK', 'DAMAGED'}


def _valid_quantity(value):
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
        and value > 0
    )


def _returned_quantity(shipment_item_id):
    return db.session.query(func.coalesce(func.sum(SalesReturnItem.quantity), 0)).join(
        SalesReturn
    ).filter(
        SalesReturnItem.shipment_item_id == shipment_item_id,
        SalesReturn.status == 'POSTED'
    ).scalar()


@bp.route('/sales-returns', methods=['GET'])
def get_sales_returns():
    page = max(request.args.get('page', 1, type=int), 1)
    per_page = min(max(request.args.get('per_page', 10, type=int), 1), 100)
    query = SalesReturn.query

    status = request.args.get('status', type=str)
    warehouse_id = request.args.get('warehouse_id', type=int)
    shipment_id = request.args.get('shipment_id', type=int)
    if status:
        query = query.filter(SalesReturn.status == status.upper())
    if warehouse_id is not None:
        query = query.join(SalesReturn.shipment).join(
            Shipment.sales_order
        ).filter(SalesOrder.warehouse_id == warehouse_id)
    if shipment_id is not None:
        query = query.filter_by(shipment_id=shipment_id)

    pagination = query.order_by(SalesReturn.id.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    return jsonify({
        'data': [sales_return.to_dict() for sales_return in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
    })


@bp.route('/sales-returns', methods=['POST'])
def create_sales_return():
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({'error': 'A JSON object is required'}), 400

    shipment_id = data.get('shipment_id')
    reason = data.get('reason')
    items = data.get('items')
    if not isinstance(shipment_id, int) or isinstance(shipment_id, bool):
        return jsonify({'error': 'shipment_id is required'}), 400
    if not isinstance(reason, str) or not reason.strip():
        return jsonify({'error': 'A return reason is required'}), 400
    if not isinstance(items, list) or not items:
        return jsonify({'error': 'At least one returned item is required'}), 400

    shipment = Shipment.query.filter_by(id=shipment_id).with_for_update().first()
    if not shipment:
        return jsonify({'error': 'Shipment not found'}), 404
    if shipment.status != 'POSTED':
        return jsonify({'error': 'Only posted shipments can be returned'}), 409

    shipment_items = {item.id: item for item in shipment.items}
    validated = []
    seen_items = set()
    for item_data in items:
        if not isinstance(item_data, dict):
            return jsonify({'error': 'Each returned item must be a JSON object'}), 400
        shipment_item_id = item_data.get('shipment_item_id')
        quantity = item_data.get('quantity')
        condition = item_data.get('condition')
        if (
            not isinstance(shipment_item_id, int)
            or isinstance(shipment_item_id, bool)
            or shipment_item_id not in shipment_items
        ):
            return jsonify({'error': 'Each item must reference an item on the shipment'}), 400
        if shipment_item_id in seen_items:
            return jsonify({'error': 'Duplicate shipment items must be combined'}), 400
        if not _valid_quantity(quantity):
            return jsonify({'error': 'Returned quantity must be positive'}), 400
        if condition not in VALID_CONDITIONS:
            return jsonify({'error': 'condition must be RESTOCK or DAMAGED'}), 400
        shipment_item = shipment_items[shipment_item_id]
        if _returned_quantity(shipment_item_id) + quantity > shipment_item.quantity + 1e-9:
            return jsonify({'error': 'Returned quantity exceeds the remaining shipped quantity'}), 409
        seen_items.add(shipment_item_id)
        validated.append((shipment_item_id, quantity, condition))

    sales_return = SalesReturn(
        return_number=f'SR-{uuid4().hex[:16].upper()}',
        shipment_id=shipment.id,
        status='DRAFT',
        reason=reason.strip(),
        created_by=request.current_user.id
    )
    try:
        db.session.add(sales_return)
        db.session.flush()
        for shipment_item_id, quantity, condition in validated:
            db.session.add(SalesReturnItem(
                sales_return_id=sales_return.id,
                shipment_item_id=shipment_item_id,
                quantity=quantity,
                disposition=condition
            ))
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Sales return creation failed')
        return jsonify({'error': 'Unable to create sales return'}), 500

    return jsonify({'data': sales_return.to_dict()}), 201


@bp.route('/sales-returns/<int:return_id>', methods=['GET'])
def get_sales_return(return_id):
    sales_return = db.session.get(SalesReturn, return_id)
    if not sales_return:
        return jsonify({'error': 'Sales return not found'}), 404
    return jsonify({'data': sales_return.to_dict()})


@bp.route('/sales-returns/<int:return_id>/post', methods=['POST'])
def post_sales_return(return_id):
    sales_return = SalesReturn.query.filter_by(
        id=return_id
    ).with_for_update().first()
    if not sales_return:
        return jsonify({'error': 'Sales return not found'}), 404
    if sales_return.status != 'DRAFT':
        return jsonify({'error': 'Only draft sales returns can be posted'}), 409

    shipment = Shipment.query.filter_by(
        id=sales_return.shipment_id
    ).with_for_update().first()
    if not shipment or shipment.status != 'POSTED':
        return jsonify({'error': 'Return shipment is not posted'}), 409

    shipment_items = {
        item.id: item
        for item in ShipmentItem.query.filter_by(
            shipment_id=shipment.id
        ).order_by(ShipmentItem.id).with_for_update().all()
    }
    prior_returns = SalesReturn.query.filter_by(
        shipment_id=shipment.id,
        status='POSTED'
    ).filter(SalesReturn.id != sales_return.id).order_by(SalesReturn.id).with_for_update().all()
    returned_by_item = {}
    for prior_return in prior_returns:
        for returned_item in prior_return.items:
            returned_by_item[returned_item.shipment_item_id] = (
                returned_by_item.get(returned_item.shipment_item_id, 0)
                + returned_item.quantity
            )

    restock_by_product = {}
    return_value_by_product = {}
    warehouse_id = shipment.sales_order.warehouse_id
    for item in sales_return.items:
        shipment_item = shipment_items.get(item.shipment_item_id)
        if not shipment_item:
            return jsonify({'error': 'Returned item is not on the shipment'}), 409
        already_returned = returned_by_item.get(item.shipment_item_id, 0)
        if already_returned + item.quantity > shipment_item.quantity + 1e-9:
            return jsonify({
                'error': 'Returned quantity exceeds the remaining shipped quantity'
            }), 409
        if item.disposition == 'RESTOCK':
            product_id = shipment_item.product_id
            restock_by_product[product_id] = (
                restock_by_product.get(product_id, 0) + item.quantity
            )
            historical_unit_cost = (
                shipment_item.unit_cost
                if shipment_item.unit_cost is not None
                else shipment_item.unit_price
            )
            return_value_by_product[product_id] = (
                return_value_by_product.get(product_id, decimal_value(0))
                + decimal_value(item.quantity) * decimal_value(historical_unit_cost)
            )
        else:
            historical_unit_cost = (
                shipment_item.unit_cost
                if shipment_item.unit_cost is not None
                else shipment_item.unit_price
            )
            db.session.add(InventoryQuarantine(
                source_sales_return_item_id=item.id,
                product_id=shipment_item.product_id,
                warehouse_id=warehouse_id,
                quantity=item.quantity,
                unit_cost=historical_unit_cost,
                reason=sales_return.reason,
                status='QUARANTINED',
                created_by=request.current_user.id,
            ))

    balances = {}
    for product_id in sorted(restock_by_product):
        balance = InventoryBalance.query.filter_by(
            product_id=product_id,
            warehouse_id=warehouse_id
        ).with_for_update().first()
        if not balance:
            return jsonify({
                'error': f'Inventory balance not found for product {product_id}'
            }), 409
        balances[product_id] = balance

    try:
        for product_id, quantity in restock_by_product.items():
            balance = balances[product_id]
            old_quantity = decimal_value(balance.quantity_on_hand)
            returned_quantity = decimal_value(quantity)
            return_cost = quantize_cost(
                return_value_by_product[product_id] / returned_quantity
            )
            new_quantity = old_quantity + returned_quantity
            balance.average_cost = quantize_cost(
                (
                    old_quantity * decimal_value(balance.average_cost)
                    + returned_quantity * decimal_value(return_cost)
                )
                / decimal_value(new_quantity)
            )
            balance.last_cost = return_cost
            balance.quantity_on_hand = new_quantity
            db.session.add(StockMovement(
                product_id=product_id,
                warehouse_id=warehouse_id,
                movement_type='RETURN_IN',
                quantity_delta=quantity,
                unit_cost=return_cost,
                reference_type='SALES_RETURN',
                reference_id=sales_return.id,
                created_by=request.current_user.id
            ))
        sales_return.status = 'POSTED'
        sales_return.posted_by = request.current_user.id
        sales_return.posted_at = db.func.current_timestamp()
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Sales return posting failed')
        return jsonify({'error': 'Unable to post sales return'}), 500

    return jsonify({'data': sales_return.to_dict()})
