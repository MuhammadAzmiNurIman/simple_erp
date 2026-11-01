import math
from uuid import uuid4

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import or_
from app import db
from app.money import decimal_value, quantize_cost
from app.models import (
    InventoryBalance, Product, StockMovement, StockTransfer,
    StockTransferItem, Warehouse
)


bp = Blueprint('inventory_transfers', __name__)


def _valid_quantity(value):
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
        and value > 0
    )


@bp.route('/inventory/transfers', methods=['GET'])
def get_transfers():
    page = max(request.args.get('page', 1, type=int), 1)
    per_page = min(max(request.args.get('per_page', 10, type=int), 1), 100)
    query = StockTransfer.query
    status = request.args.get('status', type=str)
    source_id = request.args.get('source_warehouse_id', type=int)
    destination_id = request.args.get('destination_warehouse_id', type=int)
    warehouse_id = request.args.get('warehouse_id', type=int)
    if status:
        query = query.filter_by(status=status.upper())
    if warehouse_id is not None:
        query = query.filter(or_(
            StockTransfer.source_warehouse_id == warehouse_id,
            StockTransfer.destination_warehouse_id == warehouse_id,
        ))
    else:
        if source_id is not None:
            query = query.filter_by(source_warehouse_id=source_id)
        if destination_id is not None:
            query = query.filter_by(destination_warehouse_id=destination_id)
    if not request.current_user.all_warehouses:
        allowed_ids = request.allowed_warehouse_ids
        query = query.filter(or_(
            StockTransfer.source_warehouse_id.in_(allowed_ids),
            StockTransfer.destination_warehouse_id.in_(allowed_ids),
        ))
    pagination = query.order_by(StockTransfer.id.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    return jsonify({
        'data': [transfer.to_dict() for transfer in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
    })


@bp.route('/inventory/transfers', methods=['POST'])
def create_transfer():
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({'error': 'A JSON object is required'}), 400
    source_id = data.get('source_warehouse_id')
    destination_id = data.get('destination_warehouse_id')
    reason = data.get('reason')
    items = data.get('items')
    if (
        not isinstance(source_id, int) or isinstance(source_id, bool)
        or not isinstance(destination_id, int) or isinstance(destination_id, bool)
    ):
        return jsonify({'error': 'Source and destination warehouse IDs are required'}), 400
    if source_id == destination_id:
        return jsonify({'error': 'Source and destination warehouses must differ'}), 400
    if not isinstance(reason, str) or not reason.strip():
        return jsonify({'error': 'A transfer reason is required'}), 400
    if not isinstance(items, list) or not items:
        return jsonify({'error': 'At least one transfer item is required'}), 400

    warehouses = Warehouse.query.filter(
        Warehouse.id.in_([source_id, destination_id])
    ).all()
    if len(warehouses) != 2:
        return jsonify({'error': 'One or both warehouses were not found'}), 404
    if any(not warehouse.is_active for warehouse in warehouses):
        return jsonify({'error': 'Both warehouses must be active'}), 409

    validated = []
    seen_products = set()
    for item_data in items:
        if not isinstance(item_data, dict):
            return jsonify({'error': 'Each transfer item must be a JSON object'}), 400
        product_id = item_data.get('product_id')
        quantity = item_data.get('quantity')
        if not isinstance(product_id, int) or isinstance(product_id, bool):
            return jsonify({'error': 'Each item requires a valid product_id'}), 400
        if not _valid_quantity(quantity):
            return jsonify({'error': 'Each item quantity must be positive'}), 400
        if product_id in seen_products:
            return jsonify({'error': 'Duplicate products must be combined into one item'}), 400
        product = db.session.get(Product, product_id)
        if not product or not product.is_active:
            return jsonify({'error': f'Active product {product_id} not found'}), 404
        seen_products.add(product_id)
        validated.append((product_id, quantity))

    transfer = StockTransfer(
        transfer_number=f'TR-{uuid4().hex[:16].upper()}',
        source_warehouse_id=source_id,
        destination_warehouse_id=destination_id,
        reason=reason.strip(),
        status='DRAFT',
        created_by=request.current_user.id
    )
    try:
        db.session.add(transfer)
        db.session.flush()
        for product_id, quantity in validated:
            db.session.add(StockTransferItem(
                stock_transfer_id=transfer.id,
                product_id=product_id,
                quantity=quantity
            ))
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Stock transfer creation failed')
        return jsonify({'error': 'Unable to create stock transfer'}), 500
    return jsonify({'data': transfer.to_dict()}), 201


@bp.route('/inventory/transfers/<int:transfer_id>', methods=['GET'])
def get_transfer(transfer_id):
    transfer = db.session.get(StockTransfer, transfer_id)
    if not transfer:
        return jsonify({'error': 'Stock transfer not found'}), 404
    return jsonify({'data': transfer.to_dict()})


@bp.route('/inventory/transfers/<int:transfer_id>/submit', methods=['POST'])
def submit_transfer(transfer_id):
    transfer = StockTransfer.query.filter_by(id=transfer_id).with_for_update().first()
    if not transfer:
        return jsonify({'error': 'Stock transfer not found'}), 404
    if transfer.status != 'DRAFT':
        return jsonify({'error': 'Only draft transfers can be submitted'}), 409
    balances = _lock_source_balances(transfer)
    if isinstance(balances, tuple):
        return balances
    try:
        transfer.status = 'SUBMITTED'
        transfer.submitted_at = db.func.current_timestamp()
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Stock transfer submission failed')
        return jsonify({'error': 'Unable to submit stock transfer'}), 500
    return jsonify({'data': transfer.to_dict()})


@bp.route('/inventory/transfers/<int:transfer_id>/approve', methods=['POST'])
def approve_transfer(transfer_id):
    transfer = StockTransfer.query.filter_by(id=transfer_id).with_for_update().first()
    if not transfer:
        return jsonify({'error': 'Stock transfer not found'}), 404
    if transfer.status != 'SUBMITTED':
        return jsonify({'error': 'Only submitted transfers can be approved'}), 409
    if transfer.created_by == request.current_user.id:
        return jsonify({'error': 'The transfer creator cannot approve it'}), 403
    try:
        transfer.status = 'APPROVED'
        transfer.approved_by = request.current_user.id
        transfer.approved_at = db.func.current_timestamp()
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Stock transfer approval failed')
        return jsonify({'error': 'Unable to approve stock transfer'}), 500
    return jsonify({'data': transfer.to_dict()})


@bp.route('/inventory/transfers/<int:transfer_id>/reject', methods=['POST'])
def reject_transfer(transfer_id):
    transfer = StockTransfer.query.filter_by(id=transfer_id).with_for_update().first()
    if not transfer:
        return jsonify({'error': 'Stock transfer not found'}), 404
    if transfer.status != 'SUBMITTED':
        return jsonify({'error': 'Only submitted transfers can be rejected'}), 409
    if transfer.created_by == request.current_user.id:
        return jsonify({'error': 'The transfer creator cannot reject it'}), 403
    try:
        transfer.status = 'REJECTED'
        transfer.rejected_by = request.current_user.id
        transfer.rejected_at = db.func.current_timestamp()
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Stock transfer rejection failed')
        return jsonify({'error': 'Unable to reject stock transfer'}), 500
    return jsonify({'data': transfer.to_dict()})


@bp.route('/inventory/transfers/<int:transfer_id>/post', methods=['POST'])
def post_transfer(transfer_id):
    transfer = StockTransfer.query.filter_by(id=transfer_id).with_for_update().first()
    if not transfer:
        return jsonify({'error': 'Stock transfer not found'}), 404
    if transfer.status != 'APPROVED':
        return jsonify({'error': 'Only approved transfers can be posted'}), 409
    if (
        not transfer.source_warehouse.is_active
        or not transfer.destination_warehouse.is_active
    ):
        return jsonify({'error': 'Both transfer warehouses must be active'}), 409

    warehouse_ids = sorted([
        transfer.source_warehouse_id,
        transfer.destination_warehouse_id
    ])
    Warehouse.query.filter(Warehouse.id.in_(warehouse_ids)).order_by(
        Warehouse.id
    ).with_for_update().all()
    balances = _lock_source_balances(transfer)
    if isinstance(balances, tuple):
        return balances

    destination_product_ids = sorted({item.product_id for item in transfer.items})
    destination_balances = {
        product_id: InventoryBalance.get_or_create(
            product_id=product_id,
            warehouse_id=transfer.destination_warehouse_id,
            for_update=True
        )
        for product_id in destination_product_ids
    }

    try:
        for item in transfer.items:
            source_balance = balances[item.product_id]
            destination_balance = destination_balances[item.product_id]
            transfer_cost = decimal_value(source_balance.average_cost)

            source_balance.quantity_on_hand -= item.quantity
            incoming_value = decimal_value(item.quantity) * transfer_cost
            previous_value = (
                decimal_value(destination_balance.quantity_on_hand)
                * decimal_value(destination_balance.average_cost)
            )
            new_quantity = destination_balance.quantity_on_hand + item.quantity
            destination_balance.quantity_on_hand = new_quantity
            if new_quantity > 0:
                destination_balance.average_cost = quantize_cost(
                    (previous_value + incoming_value)
                    / decimal_value(new_quantity)
                )
            destination_balance.last_cost = transfer_cost

            db.session.add_all([
                StockMovement(
                    product_id=item.product_id,
                    warehouse_id=transfer.source_warehouse_id,
                    movement_type='TRANSFER_OUT',
                    quantity_delta=-item.quantity,
                    unit_cost=transfer_cost,
                    reference_type='STOCK_TRANSFER',
                    reference_id=transfer.id,
                    created_by=request.current_user.id
                ),
                StockMovement(
                    product_id=item.product_id,
                    warehouse_id=transfer.destination_warehouse_id,
                    movement_type='TRANSFER_IN',
                    quantity_delta=item.quantity,
                    unit_cost=transfer_cost,
                    reference_type='STOCK_TRANSFER',
                    reference_id=transfer.id,
                    created_by=request.current_user.id
                )
            ])
        transfer.status = 'POSTED'
        transfer.posted_by = request.current_user.id
        transfer.posted_at = db.func.current_timestamp()
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Stock transfer posting failed')
        return jsonify({'error': 'Unable to post stock transfer'}), 500
    return jsonify({'data': transfer.to_dict()})


def _lock_source_balances(transfer):
    required_by_product = {}
    for item in transfer.items:
        required_by_product[item.product_id] = (
            required_by_product.get(item.product_id, 0) + item.quantity
        )

    balances = {}
    for product_id in sorted(required_by_product.keys()):
        balance = InventoryBalance.query.filter_by(
            product_id=product_id,
            warehouse_id=transfer.source_warehouse_id
        ).with_for_update().first()
        if not balance or balance.quantity_available < required_by_product[product_id]:
            return jsonify({
                'error': f'Insufficient available stock for product {product_id}'
            }), 409
        balances[product_id] = balance
    return balances
