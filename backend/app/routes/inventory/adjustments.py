import math
from uuid import uuid4

from flask import Blueprint, current_app, jsonify, request

from app import db
from app.models import InventoryAdjuster, InventoryBalance, StockMovement


bp = Blueprint('inventory_adjuster', __name__)


def _review_adjustment(adjuster_id, approve):
    adjuster = InventoryAdjuster.query.filter_by(
        id=adjuster_id
    ).with_for_update().first()
    if not adjuster:
        return jsonify({'error': 'Inventory adjustment not found'}), 404
    if adjuster.status != 'PENDING':
        return jsonify({'error': 'Only pending adjustments can be reviewed'}), 409
    if adjuster.created_by == request.current_user.id:
        return jsonify({'error': 'The adjustment creator cannot review it'}), 403

    if not approve:
        adjuster.status = 'REJECTED'
        adjuster.reviewed_by = request.current_user.id
        adjuster.reviewed_at = db.func.current_timestamp()
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            current_app.logger.exception('Inventory adjustment rejection failed')
            return jsonify({'error': 'Unable to reject inventory adjustment'}), 500
        return jsonify({'data': adjuster.to_dict()})

    try:
        adjuster.status = 'APPROVED'
        adjuster.reviewed_by = request.current_user.id
        adjuster.reviewed_at = db.func.current_timestamp()
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Inventory adjustment approval failed')
        return jsonify({'error': 'Unable to approve inventory adjustment'}), 500

    return jsonify({'data': adjuster.to_dict()})


def _post_adjustment(adjuster_id):
    adjuster = InventoryAdjuster.query.filter_by(
        id=adjuster_id
    ).with_for_update().first()
    if not adjuster:
        return jsonify({'error': 'Inventory adjustment not found'}), 404
    if adjuster.status != 'APPROVED':
        return jsonify({'error': 'Only approved adjustments can be posted'}), 409

    balance = InventoryBalance.query.filter_by(
        id=adjuster.inventory_balance_id
    ).with_for_update().first()
    if not balance:
        return jsonify({'error': 'Inventory balance not found'}), 404

    if (
        adjuster.adjustment_type == 'REDUCE'
        and balance.quantity_available < adjuster.quantity
    ):
        return jsonify({
            'error': (
                f'Insufficient available stock. Available: {balance.quantity_available}, '
                f'Requested: {adjuster.quantity}'
            )
        }), 400

    try:
        if adjuster.adjustment_type == 'ADD':
            balance.quantity_on_hand += adjuster.quantity
        else:
            balance.quantity_on_hand -= adjuster.quantity

        adjuster.status = 'POSTED'
        adjuster.posted_by = request.current_user.id
        adjuster.posted_at = db.func.current_timestamp()
        movement_delta = (
            adjuster.quantity
            if adjuster.adjustment_type == 'ADD'
            else -adjuster.quantity
        )
        db.session.add(StockMovement(
            product_id=adjuster.product_id,
            warehouse_id=adjuster.warehouse_id,
            movement_type='ADJUSTMENT',
            quantity_delta=movement_delta,
            unit_cost=balance.average_cost or 0,
            reference_type='INVENTORY_ADJUSTMENT',
            reference_id=adjuster.id
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Inventory adjustment posting failed')
        return jsonify({'error': 'Unable to post inventory adjustment'}), 500

    return jsonify({'data': adjuster.to_dict()})


@bp.route('/inventory/adjustments', methods=['GET'])
@bp.route('/inventory/adjusters', methods=['GET'])
def get_inventory_adjusters():
    page = max(request.args.get('page', 1, type=int), 1)
    per_page = min(max(request.args.get('per_page', 10, type=int), 1), 100)
    adjustment_type = request.args.get('type', type=str)
    status = request.args.get('status', type=str)
    warehouse_id = request.args.get('warehouse_id', type=int)

    query = InventoryAdjuster.query
    if adjustment_type:
        query = query.filter(
            InventoryAdjuster.adjustment_type == adjustment_type.upper()
        )
    if status:
        query = query.filter(InventoryAdjuster.status == status.upper())
    if warehouse_id is not None:
        query = query.filter(InventoryAdjuster.warehouse_id == warehouse_id)

    pagination = query.order_by(InventoryAdjuster.id.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    return jsonify({
        'data': [adjustment.to_dict() for adjustment in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
    })


@bp.route('/inventory/adjustments', methods=['POST'])
@bp.route('/inventory/adjusters', methods=['POST'])
def create_inventory_adjuster():
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({'error': 'A JSON object is required'}), 400

    balance_id = data.get('inventory_balance_id')
    adjustment_type = data.get('adjustment_type')
    quantity = data.get('quantity')
    if not isinstance(balance_id, int) or isinstance(balance_id, bool):
        return jsonify({'error': 'inventory_balance_id is required'}), 400
    if adjustment_type not in {'ADD', 'REDUCE'}:
        return jsonify({'error': 'adjustment_type must be ADD or REDUCE'}), 400
    if (
        isinstance(quantity, bool)
        or not isinstance(quantity, (int, float))
        or not math.isfinite(quantity)
        or quantity <= 0
    ):
        return jsonify({'error': 'quantity must be a positive number'}), 400

    balance = InventoryBalance.query.filter_by(id=balance_id).with_for_update().first()
    if not balance:
        return jsonify({'error': 'Inventory balance not found'}), 404

    if adjustment_type == 'REDUCE' and balance.quantity_available < quantity:
        return jsonify({
            'error': (
                f'Insufficient available stock. Available: {balance.quantity_available}, '
                f'Requested: {quantity}'
            )
        }), 400

    adjuster = InventoryAdjuster(
        code=f'ADJ-{uuid4().hex[:12].upper()}',
        inventory_balance_id=balance.id,
        product_id=balance.product_id,
        warehouse_id=balance.warehouse_id,
        adjustment_type=adjustment_type,
        quantity=quantity,
        description=data.get('description'),
        status='PENDING',
        created_by=request.current_user.id
    )
    try:
        db.session.add(adjuster)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Inventory adjustment request failed')
        return jsonify({'error': 'Unable to create inventory adjustment'}), 500

    return jsonify({
        'message': 'Inventory adjustment submitted for approval',
        'data': adjuster.to_dict()
    }), 201


@bp.route('/inventory/adjustments/<int:adjuster_id>/approve', methods=['POST'])
@bp.route('/inventory/adjusters/<int:adjuster_id>/approve', methods=['POST'])
def approve_inventory_adjuster(adjuster_id):
    return _review_adjustment(adjuster_id, approve=True)


@bp.route('/inventory/adjustments/<int:adjuster_id>/reject', methods=['POST'])
@bp.route('/inventory/adjusters/<int:adjuster_id>/reject', methods=['POST'])
def reject_inventory_adjuster(adjuster_id):
    return _review_adjustment(adjuster_id, approve=False)


@bp.route('/inventory/adjustments/<int:adjuster_id>/post', methods=['POST'])
@bp.route('/inventory/adjusters/<int:adjuster_id>/post', methods=['POST'])
def post_inventory_adjuster(adjuster_id):
    return _post_adjustment(adjuster_id)
