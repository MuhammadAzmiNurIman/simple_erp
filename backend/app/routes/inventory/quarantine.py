from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import func

from app import db
from app.money import decimal_value, quantize_cost
from app.models import (
    InventoryBalance, InventoryQuarantine, InventoryQuarantineAction,
    StockMovement,
)


bp = Blueprint('inventory_quarantine', __name__)
VALID_ACTIONS = {'RELEASE', 'SCRAP'}


@bp.route('/inventory/quarantines', methods=['GET'])
def get_quarantines():
    page = max(request.args.get('page', 1, type=int), 1)
    per_page = min(max(request.args.get('per_page', 25, type=int), 1), 100)
    query = InventoryQuarantine.query
    status = request.args.get('status', type=str)
    warehouse_id = request.args.get('warehouse_id', type=int)
    product_id = request.args.get('product_id', type=int)

    if status:
        status = status.upper()
        if status not in {'QUARANTINED', 'RELEASED', 'SCRAPPED'}:
            return jsonify({'error': 'Invalid quarantine status'}), 400
        query = query.filter(InventoryQuarantine.status == status)
    if warehouse_id is not None:
        query = query.filter(InventoryQuarantine.warehouse_id == warehouse_id)
    if product_id is not None:
        query = query.filter(InventoryQuarantine.product_id == product_id)
    if not request.current_user.all_warehouses:
        query = query.filter(
            InventoryQuarantine.warehouse_id.in_(request.allowed_warehouse_ids)
        )

    open_quantity_query = InventoryQuarantine.query.filter(
        InventoryQuarantine.status == 'QUARANTINED'
    )
    if warehouse_id is not None:
        open_quantity_query = open_quantity_query.filter(
            InventoryQuarantine.warehouse_id == warehouse_id
        )
    if product_id is not None:
        open_quantity_query = open_quantity_query.filter(
            InventoryQuarantine.product_id == product_id
        )
    if not request.current_user.all_warehouses:
        open_quantity_query = open_quantity_query.filter(
            InventoryQuarantine.warehouse_id.in_(request.allowed_warehouse_ids)
        )
    quarantined_quantity = open_quantity_query.with_entities(
        func.coalesce(func.sum(InventoryQuarantine.quantity), 0)
    ).scalar()

    pagination = query.order_by(InventoryQuarantine.id.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False,
    )
    rows = pagination.items
    return jsonify({
        'data': [row.to_dict() for row in rows],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
        'quarantined_quantity': float(quarantined_quantity or 0),
    })


@bp.route('/inventory/quarantines/<int:quarantine_id>/actions', methods=['POST'])
def request_quarantine_action(quarantine_id):
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({'error': 'A JSON object is required'}), 400
    action_type = data.get('action')
    reason = data.get('reason')
    if not isinstance(action_type, str) or action_type not in VALID_ACTIONS:
        return jsonify({'error': 'action must be RELEASE or SCRAP'}), 400
    if not isinstance(reason, str) or not reason.strip():
        return jsonify({'error': 'A disposition reason is required'}), 400

    quarantine = InventoryQuarantine.query.filter_by(
        id=quarantine_id
    ).with_for_update().first()
    if not quarantine:
        return jsonify({'error': 'Quarantined stock record not found'}), 404
    if quarantine.status != 'QUARANTINED':
        return jsonify({'error': 'Only quarantined stock can be resolved'}), 409

    active_action = InventoryQuarantineAction.query.filter(
        InventoryQuarantineAction.quarantine_id == quarantine.id,
        InventoryQuarantineAction.status.in_(('PENDING', 'APPROVED')),
    ).first()
    if active_action:
        return jsonify({'error': 'A disposition action is already in progress'}), 409

    action = InventoryQuarantineAction(
        quarantine_id=quarantine.id,
        action=action_type,
        status='PENDING',
        reason=reason.strip(),
        created_by=request.current_user.id,
    )
    try:
        db.session.add(action)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Quarantine disposition request failed')
        return jsonify({'error': 'Unable to request quarantine disposition'}), 500
    return jsonify({'data': action.to_dict()}), 201


def _review_quarantine_action(action_id, approve):
    action = InventoryQuarantineAction.query.filter_by(
        id=action_id
    ).with_for_update().first()
    if not action:
        return jsonify({'error': 'Quarantine disposition action not found'}), 404
    if action.status != 'PENDING':
        return jsonify({'error': 'Only pending disposition actions can be reviewed'}), 409
    if action.created_by == request.current_user.id:
        return jsonify({'error': 'The disposition requester cannot review it'}), 403

    action.status = 'APPROVED' if approve else 'REJECTED'
    action.reviewed_by = request.current_user.id
    action.reviewed_at = db.func.current_timestamp()
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Quarantine disposition review failed')
        return jsonify({'error': 'Unable to review quarantine disposition'}), 500
    return jsonify({'data': action.to_dict()})


@bp.route('/inventory/quarantine-actions/<int:action_id>/approve', methods=['POST'])
def approve_quarantine_action(action_id):
    return _review_quarantine_action(action_id, approve=True)


@bp.route('/inventory/quarantine-actions/<int:action_id>/reject', methods=['POST'])
def reject_quarantine_action(action_id):
    return _review_quarantine_action(action_id, approve=False)


@bp.route('/inventory/quarantine-actions/<int:action_id>/post', methods=['POST'])
def post_quarantine_action(action_id):
    action = InventoryQuarantineAction.query.filter_by(
        id=action_id
    ).with_for_update().first()
    if not action:
        return jsonify({'error': 'Quarantine disposition action not found'}), 404
    if action.status != 'APPROVED':
        return jsonify({'error': 'Only approved disposition actions can be posted'}), 409

    quarantine = InventoryQuarantine.query.filter_by(
        id=action.quarantine_id
    ).with_for_update().first()
    if not quarantine or quarantine.status != 'QUARANTINED':
        return jsonify({'error': 'Quarantined stock is no longer available'}), 409

    try:
        if action.action == 'RELEASE':
            balance = InventoryBalance.query.filter_by(
                product_id=quarantine.product_id,
                warehouse_id=quarantine.warehouse_id,
            ).with_for_update().first()
            if not balance:
                return jsonify({'error': 'Inventory balance not found'}), 409

            old_quantity = decimal_value(balance.quantity_on_hand)
            released_quantity = decimal_value(quarantine.quantity)
            released_cost = decimal_value(quarantine.unit_cost)
            new_quantity = old_quantity + released_quantity
            if new_quantity > 0:
                balance.average_cost = quantize_cost(
                    (
                        old_quantity * decimal_value(balance.average_cost)
                        + released_quantity * released_cost
                    ) / new_quantity
                )
            balance.last_cost = quantize_cost(released_cost)
            balance.quantity_on_hand = new_quantity
            db.session.add(StockMovement(
                product_id=quarantine.product_id,
                warehouse_id=quarantine.warehouse_id,
                movement_type='RETURN_IN',
                quantity_delta=quarantine.quantity,
                unit_cost=quarantine.unit_cost,
                reference_type='QUARANTINE_RELEASE',
                reference_id=action.id,
                created_by=request.current_user.id,
            ))
            quarantine.status = 'RELEASED'
        else:
            quarantine.status = 'SCRAPPED'

        quarantine.resolved_at = db.func.current_timestamp()
        action.status = 'POSTED'
        action.posted_by = request.current_user.id
        action.posted_at = db.func.current_timestamp()
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Quarantine disposition posting failed')
        return jsonify({'error': 'Unable to post quarantine disposition'}), 500

    return jsonify({'data': quarantine.to_dict()})
