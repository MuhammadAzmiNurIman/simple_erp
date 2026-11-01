import math
from datetime import date, datetime, time, timezone
from uuid import uuid4

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import or_

from app import db
from app.authorization import has_permission
from app.money import decimal_value, quantize_money
from app.models import (
    Customer, InventoryBalance, Invoice, Payment, Product, SalesOrder,
    SalesOrderItem, Shipment, ShipmentItem, StockMovement, Warehouse,
    CustomerPaymentAllocation, UserWarehouseAccess
)


bp = Blueprint('sales', __name__)


def _positive_number(value):
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
        and value > 0
    )


def _parse_iso_date(value, field_name):
    if not isinstance(value, str):
        raise ValueError(f'{field_name} must use YYYY-MM-DD format')
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f'{field_name} must use YYYY-MM-DD format') from exc


@bp.route('/sales-orders', methods=['GET'])
def get_sales_orders():
    page = max(request.args.get('page', 1, type=int), 1)
    per_page = min(max(request.args.get('per_page', 10, type=int), 1), 100)
    status_filter = request.args.get('status', type=str)

    query = SalesOrder.query
    if status_filter:
        query = query.filter(SalesOrder.status == status_filter.upper())
    warehouse_id = request.args.get('warehouse_id', type=int)
    if warehouse_id is not None:
        query = query.filter_by(warehouse_id=warehouse_id)
    elif not request.current_user.all_warehouses:
        query = query.filter(
            SalesOrder.warehouse_id.in_(request.allowed_warehouse_ids)
        )

    pagination = query.order_by(SalesOrder.id.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    return jsonify({
        'data': [order.to_dict() for order in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
    })


@bp.route('/sales-orders', methods=['POST'])
def create_sales_order():
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({'error': 'A JSON object is required'}), 400

    customer_id = data.get('customer_id')
    warehouse_id = data.get('warehouse_id')
    if not isinstance(customer_id, int) or isinstance(customer_id, bool):
        return jsonify({'error': 'customer_id is required'}), 400
    if not isinstance(warehouse_id, int) or isinstance(warehouse_id, bool):
        return jsonify({'error': 'warehouse_id is required'}), 400
    if not isinstance(data.get('items'), list) or not data['items']:
        return jsonify({'error': 'At least one item is required'}), 400

    customer = db.session.get(Customer, customer_id)
    if not customer or not customer.is_active:
        return jsonify({'error': 'Active customer not found'}), 404
    warehouse = db.session.get(Warehouse, warehouse_id)
    if not warehouse or not warehouse.is_active:
        return jsonify({'error': 'Active warehouse not found'}), 404
    try:
        due_date = _parse_iso_date(data.get('due_date'), 'due_date')
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    validated_items = []
    requested_by_product = {}
    inventory_by_product = {}
    total_amount = decimal_value(0)
    total_qty = 0.0

    raw_items = []
    for item in data['items']:
        if not isinstance(item, dict):
            return jsonify({'error': 'Each item must be a JSON object'}), 400
        product_id = item.get('product_id')
        quantity = item.get('quantity')
        unit_price = item.get('unit_price')
        if not isinstance(product_id, int) or isinstance(product_id, bool):
            return jsonify({'error': 'Each item requires a valid product_id'}), 400
        if not _positive_number(quantity):
            return jsonify({'error': 'Each item quantity must be a positive number'}), 400
        if unit_price is not None and (
            isinstance(unit_price, bool)
            or not isinstance(unit_price, (int, float))
            or not math.isfinite(unit_price)
            or unit_price < 0
        ):
            return jsonify({'error': 'Each item unit_price must be a non-negative number'}), 400

        product = db.session.get(Product, product_id)
        if not product or not product.is_active:
            return jsonify({'error': f'Active product {product_id} not found'}), 404

        raw_items.append((product, quantity, unit_price))
        requested_by_product[product_id] = requested_by_product.get(product_id, 0) + quantity

    # Lock balances in deterministic sorted product_id order to prevent deadlocks
    for product_id in sorted(requested_by_product.keys()):
        balance = InventoryBalance.query.filter_by(
            product_id=product_id,
            warehouse_id=warehouse_id
        ).with_for_update().first()
        if not balance:
            return jsonify({
                'error': f'Inventory balance not found for product {product_id}'
            }), 400
        inventory_by_product[product_id] = balance

    for product_id in sorted(requested_by_product.keys()):
        balance = inventory_by_product[product_id]
        available = balance.quantity_available
        if available < requested_by_product[product_id]:
            product = db.session.get(Product, product_id)
            return jsonify({
                'error': (
                    f'Insufficient stock for {product.name}. Available: {available}, '
                    f'Requested: {requested_by_product[product_id]}'
                )
            }), 400

    for product, quantity, requested_unit_price in raw_items:
        # Keep the old request shape working for existing API clients. New clients
        # should provide unit_price so selling price is independent of stock cost.
        unit_price = quantize_money(
            requested_unit_price
            if requested_unit_price is not None
            else (
                product.sales_price
                if product.sales_price is not None
                else inventory_by_product[product.id].average_cost or 0
            )
        )
        line_total = quantize_money(
            decimal_value(unit_price) * decimal_value(quantity)
        )
        validated_items.append((product, quantity, unit_price, line_total))
        total_amount += line_total
        total_qty += quantity

    order = SalesOrder(
        code=f'SO-{uuid4().hex[:12].upper()}',
        customer_id=customer_id,
        warehouse_id=warehouse_id,
        due_date=due_date,
        status='RESERVED',
        total_amount=quantize_money(total_amount),
        total_qty=total_qty,
        notes=data.get('notes'),
        created_by=request.current_user.id,
    )
    try:
        db.session.add(order)
        db.session.flush()
        for product, quantity, unit_price, line_total in validated_items:
            db.session.add(SalesOrderItem(
                sales_order_id=order.id,
                product_id=product.id,
                quantity=quantity,
                unit_price=unit_price,
                total_price=line_total
            ))
            inventory_by_product[product.id].quantity_reserved += quantity

        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Sales order creation failed')
        return jsonify({'error': 'Unable to create sales order'}), 500

    return jsonify({
        'message': 'Sales order created and reserved successfully',
        'data': order.to_dict()
    }), 201


@bp.route('/sales-orders/<int:so_id>', methods=['GET'])
def get_sales_order(so_id):
    order = db.session.get(SalesOrder, so_id)
    if not order:
        return jsonify({'error': 'Sales order not found'}), 404
    return jsonify({'data': order.to_dict()})


@bp.route('/sales-orders/<int:so_id>', methods=['PATCH'])
def patch_sales_order(so_id):
    order = SalesOrder.query.filter_by(id=so_id).with_for_update().first()
    if not order:
        return jsonify({'error': 'Sales order not found'}), 404
    if order.status != 'RESERVED' or order.approved_by is not None:
        return jsonify({'error': 'Only unsubmitted sales orders can be edited'}), 409
    if order.shipments:
        return jsonify({'error': 'A sales order with shipments cannot be edited'}), 409

    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({'error': 'A JSON object is required'}), 400
    customer_id = data.get('customer_id', order.customer_id)
    warehouse_id = data.get('warehouse_id', order.warehouse_id)
    items_data = data.get('items')
    if not isinstance(customer_id, int) or isinstance(customer_id, bool):
        return jsonify({'error': 'customer_id must be an integer'}), 400
    if not isinstance(warehouse_id, int) or isinstance(warehouse_id, bool):
        return jsonify({'error': 'warehouse_id must be an integer'}), 400
    if not isinstance(items_data, list) or not items_data:
        return jsonify({'error': 'At least one item is required'}), 400
    customer = db.session.get(Customer, customer_id)
    if not customer or not customer.is_active:
        return jsonify({'error': 'Active customer not found'}), 404
    warehouse = db.session.get(Warehouse, warehouse_id)
    if not warehouse or not warehouse.is_active:
        return jsonify({'error': 'Active warehouse not found'}), 404
    try:
        due_date = _parse_iso_date(data.get('due_date', order.due_date.isoformat()), 'due_date')
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    validated_items = []
    requested_by_product = {}
    total_amount = decimal_value(0)
    total_qty = 0.0
    for item in items_data:
        if not isinstance(item, dict):
            return jsonify({'error': 'Each item must be a JSON object'}), 400
        product_id = item.get('product_id')
        quantity = item.get('quantity')
        unit_price = item.get('unit_price')
        if not isinstance(product_id, int) or isinstance(product_id, bool):
            return jsonify({'error': 'Each item requires a valid product_id'}), 400
        if not _positive_number(quantity):
            return jsonify({'error': 'Each item quantity must be a positive number'}), 400
        if unit_price is not None and (
            isinstance(unit_price, bool)
            or not isinstance(unit_price, (int, float))
            or not math.isfinite(unit_price)
            or unit_price < 0
        ):
            return jsonify({'error': 'Each item unit_price must be a non-negative number'}), 400
        product = db.session.get(Product, product_id)
        if not product or not product.is_active:
            return jsonify({'error': f'Active product {product_id} not found'}), 404
        requested_by_product[product_id] = requested_by_product.get(product_id, 0) + quantity
        validated_items.append((product, quantity, unit_price))

    old_reserved_by_product = {}
    for item in order.items:
        old_reserved_by_product[item.product_id] = (
            old_reserved_by_product.get(item.product_id, 0) + item.quantity
        )
    balance_keys = sorted(
        {(product_id, order.warehouse_id) for product_id in old_reserved_by_product}
        | {(product_id, warehouse_id) for product_id in requested_by_product}
    )
    balances = {}
    for product_id, balance_warehouse_id in balance_keys:
        balance = InventoryBalance.query.filter_by(
            product_id=product_id,
            warehouse_id=balance_warehouse_id
        ).with_for_update().first()
        if not balance:
            return jsonify({'error': f'Inventory balance not found for product {product_id}'}), 409
        balances[(product_id, balance_warehouse_id)] = balance
    for product_id in sorted(requested_by_product):
        balance = balances.get((product_id, warehouse_id))
        available_with_current_reservation = (
            balance.quantity_available
            + (old_reserved_by_product.get(product_id, 0) if warehouse_id == order.warehouse_id else 0)
            if balance else 0
        )
        if available_with_current_reservation < requested_by_product[product_id]:
            product = db.session.get(Product, product_id)
            return jsonify({
                'error': f'Insufficient stock for {product.name}. Available: {available_with_current_reservation}, Requested: {requested_by_product[product_id]}'
            }), 400

    items = []
    for product, quantity, requested_price in validated_items:
        balance = balances[(product.id, warehouse_id)]
        price = quantize_money(
            requested_price if requested_price is not None
            else product.sales_price if product.sales_price is not None
            else balance.average_cost or 0
        )
        line_total = quantize_money(decimal_value(price) * decimal_value(quantity))
        items.append((product, quantity, price, line_total))
        total_amount += line_total
        total_qty += quantity

    try:
        for product_id, old_quantity in old_reserved_by_product.items():
            balances[(product_id, order.warehouse_id)].quantity_reserved -= old_quantity
        for product_id, new_quantity in requested_by_product.items():
            balances[(product_id, warehouse_id)].quantity_reserved += new_quantity
        order.customer_id = customer_id
        order.warehouse_id = warehouse_id
        order.due_date = due_date
        order.notes = data.get('notes', order.notes)
        order.total_amount = quantize_money(total_amount)
        order.total_qty = total_qty
        order.items.clear()
        db.session.flush()
        for product, quantity, price, line_total in items:
            order.items.append(SalesOrderItem(
                product_id=product.id,
                quantity=quantity,
                unit_price=price,
                total_price=line_total,
            ))
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Sales order update failed')
        return jsonify({'error': 'Unable to update sales order'}), 500
    return jsonify({'data': order.to_dict()})


@bp.route('/sales-orders/<int:so_id>/submit', methods=['POST'])
def submit_sales_order(so_id):
    order = SalesOrder.query.filter_by(id=so_id).with_for_update().first()
    if not order:
        return jsonify({'error': 'Sales order not found'}), 404
    if order.status != 'RESERVED' or order.approved_by is not None:
        return jsonify({
            'error': 'Only unapproved reserved sales orders can be submitted for approval'
        }), 409
    try:
        order.status = 'SUBMITTED'
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Sales order submission failed')
        return jsonify({'error': 'Unable to submit sales order'}), 500
    return jsonify({
        'message': 'Sales order submitted successfully',
        'data': order.to_dict()
    }), 200


@bp.route('/sales-orders/<int:so_id>/approve', methods=['POST'])
def approve_sales_order(so_id):
    order = SalesOrder.query.filter_by(id=so_id).with_for_update().first()
    if not order:
        return jsonify({'error': 'Sales order not found'}), 404
    if order.status != 'SUBMITTED':
        return jsonify({
            'error': 'Only submitted sales orders can be approved'
        }), 409
    if order.created_by == request.current_user.id:
        return jsonify({'error': 'The sales order creator cannot approve it'}), 403
    try:
        order.status = 'RESERVED'
        order.approved_by = request.current_user.id
        order.approved_at = db.func.current_timestamp()
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Sales order approval failed')
        return jsonify({'error': 'Unable to approve sales order'}), 500
    return jsonify({
        'message': 'Sales order approved successfully',
        'data': order.to_dict()
    }), 200


@bp.route('/sales-orders/<int:so_id>/reject', methods=['POST'])
def reject_sales_order(so_id):
    order = SalesOrder.query.filter_by(id=so_id).with_for_update().first()
    if not order:
        return jsonify({'error': 'Sales order not found'}), 404
    if order.status != 'SUBMITTED':
        return jsonify({'error': 'Only submitted sales orders can be rejected'}), 409
    if order.created_by == request.current_user.id:
        return jsonify({'error': 'The sales order creator cannot reject it'}), 403
    if order.shipped_qty > 0:
        return jsonify({'error': 'A sales order with shipped items cannot be rejected'}), 409

    balances = {}
    for product_id in sorted({item.product_id for item in order.items}):
        balance = InventoryBalance.query.filter_by(
            product_id=product_id,
            warehouse_id=order.warehouse_id
        ).with_for_update().first()
        reserved = sum(item.quantity for item in order.items if item.product_id == product_id)
        if not balance or balance.quantity_reserved < reserved:
            return jsonify({'error': 'Reserved inventory no longer matches the order'}), 409
        balances[product_id] = (balance, reserved)

    try:
        for balance, reserved in balances.values():
            balance.quantity_reserved -= reserved
        order.status = 'REJECTED'
        order.rejected_by = request.current_user.id
        order.rejected_at = db.func.current_timestamp()
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Sales order rejection failed')
        return jsonify({'error': 'Unable to reject sales order'}), 500
    return jsonify({'data': order.to_dict()})


@bp.route('/sales-orders/<int:so_id>/reserve', methods=['POST'])
def reserve_sales_order(so_id):
    order = SalesOrder.query.filter_by(id=so_id).with_for_update().first()
    if not order:
        return jsonify({'error': 'Sales order not found'}), 404
    if order.status != 'DRAFT':
        return jsonify({
            'error': f'Sales order cannot be reserved from {order.status} status'
        }), 409

    required_by_product = {}
    for item in order.items:
        required_by_product[item.product_id] = (
            required_by_product.get(item.product_id, 0) + item.quantity
        )

    balances = {}
    for product_id in sorted(required_by_product.keys()):
        quantity = required_by_product[product_id]
        balance = InventoryBalance.query.filter_by(
            product_id=product_id,
            warehouse_id=order.warehouse_id
        ).with_for_update().first()
        if not balance or balance.quantity_available < quantity:
            return jsonify({'error': f'Insufficient available stock for product {product_id}'}), 400
        balances[product_id] = balance

    try:
        for product_id, quantity in required_by_product.items():
            balances[product_id].quantity_reserved += quantity
        order.status = 'RESERVED'
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Sales order reservation failed')
        return jsonify({'error': 'Unable to reserve sales order'}), 500

    return jsonify({
        'message': 'Sales order reserved successfully',
        'data': order.to_dict()
    }), 200


@bp.route('/sales-orders/<int:so_id>/cancel', methods=['POST'])
def cancel_sales_order(so_id):
    order = SalesOrder.query.filter_by(id=so_id).with_for_update().first()
    if not order:
        return jsonify({'error': 'Sales order not found'}), 404
    if order.status not in {'DRAFT', 'RESERVED', 'SUBMITTED', 'PARTIALLY_SHIPPED'}:
        return jsonify({
            'error': f'Sales order cannot be cancelled from {order.status} status'
        }), 409

    if order.status in {'RESERVED', 'SUBMITTED', 'PARTIALLY_SHIPPED'}:
        required_by_product = {}
        for item in order.items:
            unshipped_qty = item.quantity - item.shipped_qty
            if unshipped_qty > 0:
                required_by_product[item.product_id] = (
                    required_by_product.get(item.product_id, 0) + unshipped_qty
                )
        balances = {}
        for product_id in sorted(required_by_product.keys()):
            quantity = required_by_product[product_id]
            balance = InventoryBalance.query.filter_by(
                product_id=product_id,
                warehouse_id=order.warehouse_id
            ).with_for_update().first()
            if not balance or balance.quantity_reserved < quantity:
                return jsonify({'error': 'Reserved inventory no longer matches the order'}), 409
            balances[product_id] = balance

    try:
        if order.status in {'RESERVED', 'SUBMITTED', 'PARTIALLY_SHIPPED'}:
            for product_id, quantity in required_by_product.items():
                balances[product_id].quantity_reserved -= quantity
        for shipment in order.shipments:
            if shipment.status == 'DRAFT':
                shipment.status = 'CANCELLED'
        order.status = 'CANCELLED'
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Sales order cancellation failed')
        return jsonify({'error': 'Unable to cancel sales order'}), 500

    return jsonify({
        'message': 'Sales order cancelled successfully',
        'data': order.to_dict()
    }), 200


@bp.route('/sales-orders/<int:so_id>/shipment', methods=['POST'])
def shipment_sales_order(so_id):
    order = SalesOrder.query.filter_by(id=so_id).with_for_update().first()
    if not order:
        return jsonify({'error': 'Sales order not found'}), 404
    items = [
        {'sales_order_item_id': item.id, 'quantity': item.quantity - item.shipped_qty}
        for item in order.items
        if item.quantity - item.shipped_qty > 1e-9
    ]
    created = _create_shipment(order, items)
    if not isinstance(created, tuple) or created[1] != 201:
        return created
    shipment_id = created[0].get_json()['data']['id']
    posted = post_shipment(shipment_id)
    if not isinstance(posted, tuple) or posted[1] != 200:
        return posted
    return jsonify({
        'message': 'Sales order shipment posted successfully',
        'data': order.to_dict(),
        'shipment': posted[0].get_json()['data']
    }), 200


def _create_shipment(order, requested_items):
    if order.approved_by is None:
        return jsonify({
            'error': 'Sales order must be approved before shipment'
        }), 409
    if order.status not in {'RESERVED', 'PARTIALLY_SHIPPED'}:
        return jsonify({
            'error': f'Sales order must be reserved before shipment. Current: {order.status}'
        }), 409
    if not requested_items:
        return jsonify({'error': 'No unshipped order quantity remains'}), 409

    order_items = {item.id: item for item in order.items}
    reserved_in_shipments = {}
    for existing in order.shipments:
        if existing.status not in {'DRAFT', 'POSTED'}:
            continue
        for item in existing.items:
            reserved_in_shipments[item.sales_order_item_id] = (
                reserved_in_shipments.get(item.sales_order_item_id, 0) + item.quantity
            )

    validated = []
    requested_by_product = {}
    for requested in requested_items:
        if not isinstance(requested, dict):
            return jsonify({'error': 'Each shipment item must be a JSON object'}), 400
        item_id = requested.get('sales_order_item_id')
        quantity = requested.get('quantity')
        if not isinstance(item_id, int) or isinstance(item_id, bool):
            return jsonify({'error': 'Each item requires sales_order_item_id'}), 400
        if not _positive_number(quantity):
            return jsonify({'error': 'Shipment quantity must be positive'}), 400
        order_item = order_items.get(item_id)
        if not order_item:
            return jsonify({'error': 'Sales order item not found'}), 400
        requested_so_far = sum(qty for requested_id, qty in validated if requested_id == item_id)
        remaining = order_item.quantity - reserved_in_shipments.get(item_id, 0)
        if quantity + requested_so_far > remaining + 1e-9:
            return jsonify({'error': 'Shipment exceeds remaining order quantity'}), 400
        validated.append((item_id, quantity))
        requested_by_product[order_item.product_id] = (
            requested_by_product.get(order_item.product_id, 0) + quantity
        )

    for product_id in sorted(requested_by_product.keys()):
        quantity = requested_by_product[product_id]
        balance = InventoryBalance.query.filter_by(
            product_id=product_id,
            warehouse_id=order.warehouse_id
        ).with_for_update().first()
        if not balance or balance.quantity_reserved < quantity:
            return jsonify({'error': 'Reserved inventory does not cover shipment'}), 409

    shipment = Shipment(
        code=f'SH-{uuid4().hex[:12].upper()}',
        sales_order_id=order.id,
        status='DRAFT',
        created_by=request.current_user.id
    )
    try:
        db.session.add(shipment)
        db.session.flush()
        for item_id, quantity in validated:
            order_item = order_items[item_id]
            db.session.add(ShipmentItem(
                shipment_id=shipment.id,
                sales_order_item_id=item_id,
                product_id=order_item.product_id,
                quantity=quantity,
                unit_price=order_item.unit_price
            ))
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Shipment creation failed')
        return jsonify({'error': 'Unable to create shipment'}), 500
    return jsonify({'data': shipment.to_dict()}), 201


@bp.route('/sales-orders/<int:so_id>/shipments', methods=['POST'])
def create_shipment(so_id):
    order = SalesOrder.query.filter_by(id=so_id).with_for_update().first()
    if not order:
        return jsonify({'error': 'Sales order not found'}), 404
    data = request.get_json()
    if not isinstance(data, dict) or not isinstance(data.get('items'), list):
        return jsonify({'error': 'items must be a JSON list'}), 400
    return _create_shipment(order, data['items'])


@bp.route('/shipments', methods=['GET'])
def get_shipments():
    page = max(request.args.get('page', 1, type=int), 1)
    per_page = min(max(request.args.get('per_page', 10, type=int), 1), 100)
    query = Shipment.query
    status = request.args.get('status', type=str)
    sales_order_id = request.args.get('sales_order_id', type=int)
    warehouse_id = request.args.get('warehouse_id', type=int)
    if status:
        query = query.filter(Shipment.status == status.upper())
    if sales_order_id is not None:
        query = query.filter_by(sales_order_id=sales_order_id)
    if warehouse_id is not None:
        query = query.join(SalesOrder).filter(
            SalesOrder.warehouse_id == warehouse_id
        )
    pagination = query.order_by(Shipment.id.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    return jsonify({
        'data': [shipment.to_dict() for shipment in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
    })


@bp.route('/shipments', methods=['POST'])
def create_shipment_canonical():
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({'error': 'A JSON object is required'}), 400
    sales_order_id = data.get('sales_order_id')
    if not isinstance(sales_order_id, int) or isinstance(sales_order_id, bool):
        return jsonify({'error': 'sales_order_id is required'}), 400
    order = SalesOrder.query.filter_by(
        id=sales_order_id
    ).with_for_update().first()
    if not order:
        return jsonify({'error': 'Sales order not found'}), 404
    items = data.get('items')
    if not isinstance(items, list):
        return jsonify({'error': 'items must be a JSON list'}), 400
    return _create_shipment(order, items)


@bp.route('/shipments/<int:shipment_id>', methods=['GET'])
def get_shipment(shipment_id):
    shipment = db.session.get(Shipment, shipment_id)
    if not shipment:
        return jsonify({'error': 'Shipment not found'}), 404
    return jsonify({'data': shipment.to_dict()})


@bp.route('/shipments/<int:shipment_id>', methods=['PATCH'])
def update_shipment(shipment_id):
    shipment = Shipment.query.filter_by(id=shipment_id).with_for_update().first()
    if not shipment:
        return jsonify({'error': 'Shipment not found'}), 404
    if shipment.status != 'DRAFT' or shipment.invoice:
        return jsonify({'error': 'Only uninvoiced draft shipments can be edited'}), 409
    data = request.get_json()
    requested_items = data.get('items') if isinstance(data, dict) else None
    if not isinstance(requested_items, list) or not requested_items:
        return jsonify({'error': 'At least one shipment item is required'}), 400

    order = SalesOrder.query.filter_by(
        id=shipment.sales_order_id
    ).with_for_update().first()
    if not order or order.approved_by is None or order.status not in {'RESERVED', 'PARTIALLY_SHIPPED'}:
        return jsonify({'error': 'The source sales order is no longer eligible for shipment'}), 409
    order_items = {item.id: item for item in order.items}
    other_quantities = {}
    for other in order.shipments:
        if other.id == shipment.id or other.status not in {'DRAFT', 'POSTED'}:
            continue
        for existing_item in other.items:
            other_quantities[existing_item.sales_order_item_id] = (
                other_quantities.get(existing_item.sales_order_item_id, 0)
                + existing_item.quantity
            )

    validated = []
    requested_by_product = {}
    requested_by_order_item = {}
    for requested in requested_items:
        if not isinstance(requested, dict):
            return jsonify({'error': 'Each shipment item must be a JSON object'}), 400
        item_id = requested.get('sales_order_item_id')
        quantity = requested.get('quantity')
        if not isinstance(item_id, int) or isinstance(item_id, bool) or not _positive_number(quantity):
            return jsonify({'error': 'Each item requires a valid order item and positive quantity'}), 400
        order_item = order_items.get(item_id)
        if not order_item:
            return jsonify({'error': f'Sales order item {item_id} not found'}), 400
        requested_by_order_item[item_id] = requested_by_order_item.get(item_id, 0) + quantity
        if requested_by_order_item[item_id] + other_quantities.get(item_id, 0) > order_item.quantity + 1e-9:
            return jsonify({'error': 'Shipment exceeds remaining order quantity'}), 400
        validated.append((order_item, quantity))
        requested_by_product[order_item.product_id] = requested_by_product.get(order_item.product_id, 0) + quantity

    for product_id, quantity in requested_by_product.items():
        balance = InventoryBalance.query.filter_by(
            product_id=product_id, warehouse_id=order.warehouse_id
        ).with_for_update().first()
        if not balance or balance.quantity_reserved < quantity:
            return jsonify({'error': 'Reserved inventory does not cover updated shipment'}), 409

    try:
        shipment.items.clear()
        db.session.flush()
        for order_item, quantity in validated:
            shipment.items.append(ShipmentItem(
                sales_order_item_id=order_item.id,
                product_id=order_item.product_id,
                quantity=quantity,
                unit_price=order_item.unit_price
            ))
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Shipment draft update failed')
        return jsonify({'error': 'Unable to update shipment draft'}), 500
    return jsonify({'data': shipment.to_dict()})


@bp.route('/shipments/<int:shipment_id>/post', methods=['POST'])
def post_shipment(shipment_id):
    shipment = Shipment.query.filter_by(id=shipment_id).with_for_update().first()
    if not shipment:
        return jsonify({'error': 'Shipment not found'}), 404
    if shipment.status != 'DRAFT':
        return jsonify({'error': 'Only draft shipments can be posted'}), 409
    order = SalesOrder.query.filter_by(
        id=shipment.sales_order_id
    ).with_for_update().first()
    if not order or order.approved_by is None:
        return jsonify({
            'error': 'Sales order must be approved before shipment posting'
        }), 409
    if order.status not in {'RESERVED', 'PARTIALLY_SHIPPED'}:
        return jsonify({
            'error': f'Sales order cannot be shipped from {order.status} status'
        }), 409
    order_items = {item.id: item for item in order.items}
    quantity_by_product = {}

    for item in shipment.items:
        order_item = order_items.get(item.sales_order_item_id)
        if not order_item:
            return jsonify({'error': 'Shipment item is not on its sales order'}), 409
        posted_qty = order_item.shipped_qty
        other_draft_qty = sum(
            other_item.quantity
            for other in order.shipments
            if other.id != shipment.id and other.status == 'DRAFT'
            for other_item in other.items
            if other_item.sales_order_item_id == order_item.id
        )
        if posted_qty + other_draft_qty + item.quantity > order_item.quantity + 1e-9:
            return jsonify({'error': 'Shipment exceeds remaining order quantity'}), 409
        quantity_by_product[item.product_id] = (
            quantity_by_product.get(item.product_id, 0) + item.quantity
        )

    balances = {}
    for product_id in sorted(quantity_by_product.keys()):
        quantity = quantity_by_product[product_id]
        balance = InventoryBalance.query.filter_by(
            product_id=product_id,
            warehouse_id=order.warehouse_id
        ).with_for_update().first()
        if not balance or balance.quantity_reserved < quantity:
            return jsonify({'error': 'Reserved inventory no longer matches shipment'}), 409
        if balance.quantity_on_hand < quantity:
            return jsonify({'error': 'Insufficient on-hand inventory to ship'}), 409
        balances[product_id] = balance

    try:
        for item in shipment.items:
            balance = balances[item.product_id]
            issue_cost = decimal_value(balance.average_cost)
            balance.quantity_reserved -= item.quantity
            balance.quantity_on_hand -= item.quantity
            item.unit_cost = issue_cost
            db.session.add(StockMovement(
                product_id=item.product_id,
                warehouse_id=order.warehouse_id,
                movement_type='OUT',
                quantity_delta=-item.quantity,
                unit_cost=issue_cost,
                reference_type='SHIPMENT',
                reference_id=shipment.id,
                created_by=request.current_user.id
            ))
        shipment.status = 'POSTED'
        shipment.posted_by = request.current_user.id
        shipment.shipped_at = db.func.current_timestamp()
        db.session.flush()
        order.status = 'SHIPPED' if order.remaining_qty <= 1e-9 else 'PARTIALLY_SHIPPED'
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Shipment posting failed')
        return jsonify({'error': 'Unable to post shipment'}), 500
    return jsonify({'message': 'Shipment posted successfully', 'data': shipment.to_dict()}), 200


@bp.route('/shipments/<int:shipment_id>/cancel', methods=['POST'])
def cancel_shipment(shipment_id):
    shipment = Shipment.query.filter_by(id=shipment_id).with_for_update().first()
    if not shipment:
        return jsonify({'error': 'Shipment not found'}), 404
    if shipment.status != 'DRAFT':
        return jsonify({'error': 'Only draft shipments can be cancelled'}), 409
    if shipment.invoice:
        return jsonify({'error': 'A shipment with an invoice cannot be cancelled'}), 409
    shipment.status = 'CANCELLED'
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Shipment cancellation failed')
        return jsonify({'error': 'Unable to cancel shipment'}), 500
    return jsonify({'data': shipment.to_dict()})


@bp.route('/sales-orders/<int:so_id>/invoice', methods=['POST'])
def invoice_sales_order(so_id):
    order = db.session.get(SalesOrder, so_id)
    if not order:
        return jsonify({'error': 'Sales order not found'}), 404
    shipment = next(
        (
            item for item in reversed(order.shipments)
            if item.status == 'POSTED' and item.invoice is None
        ),
        None
    )
    if not shipment:
        return jsonify({'error': 'No uninvoiced posted shipment is available'}), 409
    return create_invoice_for_shipment(shipment)


def create_invoice_for_shipment(shipment):
    if shipment.status != 'POSTED':
        return jsonify({'error': 'Only posted shipments can be invoiced'}), 409
    if shipment.invoice:
        return jsonify({'error': 'Shipment has already been invoiced'}), 409
    invoice = Invoice(
        code=f'INV-{uuid4().hex[:16].upper()}',
        shipment_id=shipment.id,
        due_date=shipment.sales_order.due_date,
        total_amount=quantize_money(sum(
            (
                decimal_value(item.quantity) * decimal_value(item.unit_price)
                for item in shipment.items
            ),
            decimal_value(0)
        )),
        status='OPEN'
    )
    try:
        db.session.add(invoice)
        db.session.flush()
        order = shipment.sales_order
        if (
            order.remaining_qty <= 1e-9
            and all(
                item.id == shipment.id or item.invoice is not None
                for item in order.shipments
                if item.status == 'POSTED'
            )
        ):
            order.status = 'INVOICED'
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Sales invoice creation failed')
        return jsonify({'error': 'Unable to create invoice'}), 500
    return jsonify({'message': 'Invoice created successfully', 'data': invoice.to_dict()}), 201


@bp.route('/shipments/<int:shipment_id>/invoice', methods=['POST'])
def invoice_shipment(shipment_id):
    shipment = db.session.get(Shipment, shipment_id)
    if not shipment:
        return jsonify({'error': 'Shipment not found'}), 404
    return create_invoice_for_shipment(shipment)


@bp.route('/customer-payments', methods=['GET'])
@bp.route('/payments', methods=['GET'])
def get_payments():
    page = max(request.args.get('page', 1, type=int), 1)
    per_page = min(max(request.args.get('per_page', 10, type=int), 1), 100)
    query = Payment.query
    customer_id = request.args.get('customer_id', type=int)
    warehouse_id = request.args.get('warehouse_id', type=int)
    if customer_id is not None:
        query = query.filter_by(customer_id=customer_id)
    if warehouse_id is not None:
        warehouse_invoice_ids = (
            db.session.query(Invoice.id)
            .join(Invoice.shipment)
            .join(Shipment.sales_order)
            .filter(SalesOrder.warehouse_id == warehouse_id)
        )
        allocated_payment_ids = (
            db.session.query(CustomerPaymentAllocation.payment_id)
            .join(CustomerPaymentAllocation.invoice)
            .join(Invoice.shipment)
            .join(Shipment.sales_order)
            .filter(SalesOrder.warehouse_id == warehouse_id)
        )
        query = query.filter(
            or_(
                Payment.invoice_id.in_(warehouse_invoice_ids),
                Payment.id.in_(allocated_payment_ids),
            )
        )
    pagination = query.order_by(Payment.id.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    rows = [payment.to_dict() for payment in pagination.items]
    if request.current_user.role == 'viewer':
        rows = [{
            'id': row['id'],
            'customer_name': row['customer_name'],
            'invoice_code': row['invoice_code'],
            'payment_date': row['payment_date'],
            'status': row['status'],
        } for row in rows]
    return jsonify({
        'data': rows,
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
    })


@bp.route('/sales-invoices', methods=['GET'])
@bp.route('/invoices', methods=['GET'])
def get_invoices():
    page = max(request.args.get('page', 1, type=int), 1)
    per_page = min(max(request.args.get('per_page', 10, type=int), 1), 100)
    status = request.args.get('status', type=str)
    warehouse_id = request.args.get('warehouse_id', type=int)
    query = Invoice.query
    if warehouse_id is not None:
        warehouse_invoice_ids = (
            db.session.query(Invoice.id)
            .join(Invoice.shipment)
            .join(Shipment.sales_order)
            .filter(SalesOrder.warehouse_id == warehouse_id)
        )
        query = query.filter(Invoice.id.in_(warehouse_invoice_ids))
    if request.current_user.role in {'sales', 'viewer'} and not request.current_user.all_warehouses:
        allowed_warehouse_ids = db.session.query(
            UserWarehouseAccess.warehouse_id
        ).filter_by(user_id=request.current_user.id)
        query = query.join(Invoice.shipment).join(Shipment.sales_order).filter(
            SalesOrder.warehouse_id.in_(allowed_warehouse_ids)
        )
    if status:
        query = query.filter_by(status=status.upper())
    pagination = query.order_by(Invoice.id.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    rows = [invoice.to_dict() for invoice in pagination.items]
    if request.current_user.role in {'sales', 'viewer'}:
        for row in rows:
            row.pop('amount_paid', None)
            row.pop('balance_due', None)
            if request.current_user.role == 'viewer':
                row.pop('total_amount', None)
                row.pop('items', None)
    return jsonify({
        'data': rows,
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
    })


@bp.route('/sales-invoices', methods=['POST'])
def create_sales_invoice():
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({'error': 'A JSON object is required'}), 400
    shipment_id = data.get('shipment_id')
    if not isinstance(shipment_id, int) or isinstance(shipment_id, bool):
        return jsonify({'error': 'shipment_id is required'}), 400
    shipment = db.session.get(Shipment, shipment_id)
    if not shipment:
        return jsonify({'error': 'Shipment not found'}), 404
    return create_invoice_for_shipment(shipment)


@bp.route('/sales-invoices/<int:invoice_id>', methods=['GET'])
@bp.route('/invoices/<int:invoice_id>', methods=['GET'])
def get_invoice(invoice_id):
    invoice = db.session.get(Invoice, invoice_id)
    if not invoice:
        return jsonify({'error': 'Invoice not found'}), 404
    if request.current_user.role in {'sales', 'viewer'} and not request.current_user.all_warehouses:
        allowed_warehouse_ids = {
            access.warehouse_id
            for access in UserWarehouseAccess.query.filter_by(
                user_id=request.current_user.id
            ).all()
        }
        if invoice.shipment.sales_order.warehouse_id not in allowed_warehouse_ids:
            return jsonify({'error': 'Access to this invoice is denied'}), 403
    data = invoice.to_dict()
    if request.current_user.role in {'sales', 'viewer'}:
        data.pop('amount_paid', None)
        data.pop('balance_due', None)
        if request.current_user.role == 'viewer':
            data.pop('total_amount', None)
            data.pop('items', None)
    return jsonify({'data': data})


def _draft_allocated_amount(invoice_id, excluding_payment_id=None):
    query = (
        db.session.query(
            db.func.coalesce(db.func.sum(CustomerPaymentAllocation.amount), 0)
        )
        .join(Payment, Payment.id == CustomerPaymentAllocation.payment_id)
        .filter(
            CustomerPaymentAllocation.invoice_id == invoice_id,
            Payment.status == 'DRAFT'
        )
    )
    if excluding_payment_id is not None:
        query = query.filter(Payment.id != excluding_payment_id)
    return decimal_value(query.scalar() or 0)


@bp.route('/customer-payments', methods=['POST'])
@bp.route('/payments', methods=['POST'])
def record_payment():
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({'error': 'A JSON object is required'}), 400

    invoice_id = data.get('invoice_id')
    customer_id = data.get('customer_id')
    amount = data.get('amount')
    payment_method = data.get('payment_method', 'CASH')
    if invoice_id is not None and (
        not isinstance(invoice_id, int) or isinstance(invoice_id, bool)
    ):
        return jsonify({'error': 'invoice_id must be an integer'}), 400
    if customer_id is not None and (
        not isinstance(customer_id, int) or isinstance(customer_id, bool)
    ):
        return jsonify({'error': 'customer_id must be an integer'}), 400
    if invoice_id is None and customer_id is None:
        return jsonify({'error': 'customer_id or invoice_id is required'}), 400
    if not _positive_number(amount):
        return jsonify({'error': 'amount must be a positive number'}), 400
    payment_amount = quantize_money(amount)
    if payment_amount <= 0:
        return jsonify({'error': 'amount must be at least 0.01'}), 400
    allowed_methods = {'CASH', 'BANK_TRANSFER', 'CREDIT_CARD'}
    if not isinstance(payment_method, str) or payment_method not in allowed_methods:
        return jsonify({'error': 'Unsupported payment_method'}), 400

    invoice = None
    if invoice_id is not None:
        invoice = Invoice.query.filter_by(id=invoice_id).with_for_update().first()
        if not invoice:
            return jsonify({'error': 'Invoice not found'}), 404
        invoice_customer_id = invoice.shipment.sales_order.customer_id
        if customer_id is not None and customer_id != invoice_customer_id:
            return jsonify({'error': 'Invoice does not belong to this customer'}), 400
        if (
            invoice.status == 'PAID'
            or payment_amount > invoice.balance_due
        ):
            return jsonify({
                'error': 'Payment exceeds the outstanding invoice balance'
            }), 400
        customer_id = invoice_customer_id
    elif db.session.get(Customer, customer_id) is None:
        return jsonify({'error': 'Customer not found'}), 404

    payment_date_value = data.get('payment_date')
    if payment_date_value is None:
        payment_date = datetime.now(timezone.utc).replace(tzinfo=None)
    else:
        try:
            payment_date = datetime.combine(
                _parse_iso_date(payment_date_value, 'payment_date'),
                time.min
            )
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 400

    payment = Payment(
        customer_id=customer_id,
        invoice_id=invoice.id if invoice else None,
        amount=payment_amount,
        payment_method=payment_method,
        payment_date=payment_date,
        status='DRAFT'
    )
    try:
        db.session.add(payment)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Payment recording failed')
        return jsonify({'error': 'Unable to record payment'}), 500

    return jsonify({
        'message': 'Payment draft created successfully',
        'data': payment.to_dict()
    }), 201


@bp.route('/customer-payments/record-and-post', methods=['POST'])
def record_and_post_customer_payment():
    required = ('customer_payments.create', 'customer_payments.allocate', 'customer_payments.post')
    if any(not has_permission(request.current_user, code) for code in required):
        return jsonify({'error': 'Creating, allocating, and posting customer payments are all required'}), 403
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({'error': 'A JSON object is required'}), 400
    invoice_id = data.get('invoice_id')
    amount = data.get('amount')
    method = data.get('payment_method', 'BANK_TRANSFER')
    if not isinstance(invoice_id, int) or isinstance(invoice_id, bool):
        return jsonify({'error': 'invoice_id is required'}), 400
    if not _positive_number(amount):
        return jsonify({'error': 'amount must be a positive number'}), 400
    amount = quantize_money(amount)
    if amount <= 0:
        return jsonify({'error': 'amount must be at least 0.01'}), 400
    if not isinstance(method, str) or method not in {'CASH', 'BANK_TRANSFER', 'CREDIT_CARD'}:
        return jsonify({'error': 'Unsupported payment_method'}), 400

    invoice = Invoice.query.filter_by(id=invoice_id).with_for_update().first()
    if not invoice:
        return jsonify({'error': 'Invoice not found'}), 404
    reserved = _draft_allocated_amount(invoice.id)
    available = max(decimal_value(0), decimal_value(invoice.balance_due) - reserved)
    if amount > available:
        return jsonify({'error': 'Payment exceeds the invoice balance available to this transaction'}), 409

    payment = Payment(
        customer_id=invoice.shipment.sales_order.customer_id,
        invoice_id=invoice.id,
        amount=amount,
        payment_method=method,
        payment_date=datetime.now(timezone.utc).replace(tzinfo=None),
        status='POSTED'
    )
    payment.allocations.append(CustomerPaymentAllocation(invoice=invoice, amount=amount))
    try:
        db.session.add(payment)
        db.session.flush()
        invoice.status = 'PAID' if invoice.balance_due <= decimal_value('0.005') else 'PARTIALLY_PAID'
        order = invoice.shipment.sales_order
        posted_invoices = [
            item.invoice for item in order.shipments
            if item.status == 'POSTED' and item.invoice is not None
        ]
        if (order.remaining_qty <= 1e-9 and posted_invoices and
                all(item.status == 'PAID' for item in posted_invoices) and
                all(item.invoice is not None for item in order.shipments if item.status == 'POSTED')):
            order.status = 'CLOSED'
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Atomic customer payment failed')
        return jsonify({'error': 'Unable to record and post customer payment'}), 500
    return jsonify({'data': payment.to_dict()}), 201


@bp.route('/customer-payments/<int:payment_id>/allocations', methods=['POST'])
def allocate_customer_payment(payment_id):
    data = request.get_json()
    if not isinstance(data, dict) or not isinstance(data.get('allocations'), list):
        return jsonify({'error': 'allocations must be a non-empty array'}), 400
    requested = data['allocations']
    if not requested:
        return jsonify({'error': 'allocations must be a non-empty array'}), 400

    payment = Payment.query.filter_by(id=payment_id).with_for_update().first()
    if not payment:
        return jsonify({'error': 'Payment not found'}), 404
    if payment.status != 'DRAFT':
        return jsonify({'error': 'Only draft payments can be allocated'}), 409

    allocations_by_invoice = {}
    for item in requested:
        if not isinstance(item, dict):
            return jsonify({'error': 'Each allocation must be an object'}), 400
        invoice_id = item.get('invoice_id')
        amount = item.get('amount')
        if not isinstance(invoice_id, int) or isinstance(invoice_id, bool):
            return jsonify({'error': 'invoice_id must be an integer'}), 400
        if not _positive_number(amount):
            return jsonify({'error': 'allocation amount must be positive'}), 400
        rounded_amount = quantize_money(amount)
        if rounded_amount <= 0:
            return jsonify({
                'error': 'allocation amount must be at least 0.01'
            }), 400
        if invoice_id in allocations_by_invoice:
            return jsonify({
                'error': 'An invoice may appear only once per allocation request'
            }), 400
        allocations_by_invoice[invoice_id] = rounded_amount

    existing_total = sum(
        (decimal_value(allocation.amount) for allocation in payment.allocations),
        decimal_value(0)
    )
    requested_total = sum(allocations_by_invoice.values(), decimal_value(0))
    if quantize_money(existing_total + requested_total) > quantize_money(payment.amount):
        return jsonify({
            'error': 'Allocations exceed the customer payment amount'
        }), 400

    invoices = (
        Invoice.query
        .filter(Invoice.id.in_(sorted(allocations_by_invoice)))
        .order_by(Invoice.id)
        .with_for_update()
        .all()
    )
    invoice_by_id = {invoice.id: invoice for invoice in invoices}
    missing_ids = set(allocations_by_invoice) - set(invoice_by_id)
    if missing_ids:
        return jsonify({'error': 'Invoice not found', 'invoice_ids': sorted(missing_ids)}), 404

    existing_by_invoice = {}
    for allocation in payment.allocations:
        existing_by_invoice[allocation.invoice_id] = (
            existing_by_invoice.get(allocation.invoice_id, decimal_value(0))
            + decimal_value(allocation.amount)
        )
    for invoice_id, amount in allocations_by_invoice.items():
        invoice = invoice_by_id[invoice_id]
        if invoice.shipment.sales_order.customer_id != payment.customer_id:
            return jsonify({
                'error': 'All invoices must belong to the payment customer'
            }), 400
        available_balance = (
            decimal_value(invoice.balance_due)
            - decimal_value(_draft_allocated_amount(
                invoice.id, excluding_payment_id=payment.id
            ))
        )
        already_allocated = existing_by_invoice.get(invoice_id, decimal_value(0))
        if quantize_money(already_allocated + amount) > quantize_money(available_balance):
            return jsonify({
                'error': 'Allocation exceeds the outstanding invoice balance',
                'invoice_id': invoice_id
            }), 400

    try:
        for invoice_id, amount in allocations_by_invoice.items():
            allocation = CustomerPaymentAllocation(
                invoice_id=invoice_id,
                amount=amount
            )
            allocation.invoice = invoice_by_id[invoice_id]
            payment.allocations.append(allocation)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Customer payment allocation failed')
        return jsonify({'error': 'Unable to allocate customer payment'}), 500

    return jsonify({
        'message': 'Customer payment allocations added successfully',
        'data': payment.to_dict()
    }), 200


@bp.route('/customer-payments/<int:payment_id>/post', methods=['POST'])
@bp.route('/payments/<int:payment_id>/post', methods=['POST'])
def post_payment(payment_id):
    payment = Payment.query.filter_by(id=payment_id).with_for_update().first()
    if not payment:
        return jsonify({'error': 'Payment not found'}), 404
    if payment.status != 'DRAFT':
        return jsonify({'error': 'Only draft payments can be posted'}), 409

    if not payment.allocations:
        if payment.invoice_id is None:
            return jsonify({
                'error': 'At least one invoice allocation is required before posting'
            }), 409
        legacy_invoice = (
            Invoice.query
            .filter_by(id=payment.invoice_id)
            .with_for_update()
            .first()
        )
        if not legacy_invoice:
            return jsonify({'error': 'Invoice not found'}), 404
        allocation = CustomerPaymentAllocation(
            invoice=legacy_invoice,
            amount=payment.amount
        )
        payment.allocations.append(allocation)

    allocated_total = quantize_money(sum(
        (decimal_value(allocation.amount) for allocation in payment.allocations),
        decimal_value(0)
    ))
    if allocated_total <= 0 or allocated_total > quantize_money(payment.amount):
        return jsonify({
            'error': 'Payment allocations must be positive and cannot exceed the payment amount'
        }), 409

    invoice_ids = sorted({
        allocation.invoice_id or allocation.invoice.id
        for allocation in payment.allocations
    })
    invoices = (
        Invoice.query
        .filter(Invoice.id.in_(invoice_ids))
        .order_by(Invoice.id)
        .with_for_update()
        .all()
    )
    invoice_by_id = {invoice.id: invoice for invoice in invoices}
    if len(invoice_by_id) != len(invoice_ids):
        return jsonify({'error': 'An allocated invoice no longer exists'}), 404

    allocated_by_invoice = {}
    for allocation in payment.allocations:
        invoice_id = allocation.invoice_id or allocation.invoice.id
        invoice = invoice_by_id[invoice_id]
        if invoice.shipment.sales_order.customer_id != payment.customer_id:
            return jsonify({
                'error': 'All invoices must belong to the payment customer'
            }), 409
        allocated_by_invoice[invoice_id] = (
            allocated_by_invoice.get(invoice_id, decimal_value(0))
            + decimal_value(allocation.amount)
        )
    for invoice_id, amount in allocated_by_invoice.items():
        invoice = invoice_by_id[invoice_id]
        available_balance = (
            decimal_value(invoice.balance_due)
            - decimal_value(_draft_allocated_amount(
                invoice.id, excluding_payment_id=payment.id
            ))
        )
        if quantize_money(amount) > quantize_money(available_balance):
            return jsonify({
                'error': 'Payment allocation exceeds the outstanding invoice balance',
                'invoice_id': invoice_id
            }), 409

    try:
        payment.status = 'POSTED'
        db.session.flush()
        impacted_orders = {}
        for invoice_id in allocated_by_invoice:
            invoice = invoice_by_id[invoice_id]
            invoice.status = (
                'PAID'
                if invoice.balance_due <= decimal_value('0.005')
                else 'PARTIALLY_PAID'
            )
            impacted_orders[invoice.shipment.sales_order_id] = (
                invoice.shipment.sales_order
            )
        for order in impacted_orders.values():
            all_invoices = [
                shipment.invoice
                for shipment in order.shipments
                if shipment.status == 'POSTED' and shipment.invoice is not None
            ]
            if (
                order.remaining_qty <= 1e-9
                and all_invoices
                and all(item.status == 'PAID' for item in all_invoices)
                and all(
                    shipment.invoice is not None
                    for shipment in order.shipments
                    if shipment.status == 'POSTED'
                )
            ):
                order.status = 'CLOSED'
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Payment posting failed')
        return jsonify({'error': 'Unable to post payment'}), 500

    return jsonify({
        'message': 'Payment posted successfully',
        'data': {
            **payment.to_dict(),
            'invoice': (
                invoice_by_id[payment.invoice_id].to_dict()
                if payment.invoice_id in invoice_by_id else None
            ),
            'invoices': [
                invoice_by_id[invoice_id].to_dict()
                for invoice_id in invoice_ids
            ]
        }
    }), 200
