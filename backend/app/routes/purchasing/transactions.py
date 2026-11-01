import math
from datetime import date
from uuid import uuid4

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import or_

from app import db
from app.authorization import has_permission
from app.money import decimal_value, quantize_cost, quantize_money
from app.models import (
    GoodsReceipt, GoodsReceiptItem, InventoryBalance, Product,
    PurchaseOrder, PurchaseOrderItem, StockMovement, Supplier,
    SupplierPayment, SupplierPaymentAllocation, VendorBill, Warehouse
)


bp = Blueprint('purchasing', __name__)


def _parse_order_date(value):
    if value is None:
        return date.today()
    if not isinstance(value, str):
        raise ValueError('order_date must use YYYY-MM-DD format')
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError('order_date must use YYYY-MM-DD format') from exc


def _valid_number(value, *, allow_zero=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if not math.isfinite(value):
        return False
    return value >= 0 if allow_zero else value > 0


@bp.route('/purchase-orders', methods=['GET'])
def get_purchase_orders():
    page = max(request.args.get('page', 1, type=int), 1)
    per_page = min(max(request.args.get('per_page', 10, type=int), 1), 100)
    status_filter = request.args.get('status', type=str)
    warehouse_filter = request.args.get('warehouse_id', type=int)

    query = PurchaseOrder.query
    if status_filter:
        query = query.filter_by(status=status_filter.upper())
    if warehouse_filter:
        query = query.filter_by(warehouse_id=warehouse_filter)

    pagination = query.order_by(PurchaseOrder.id.desc()).paginate(
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


@bp.route('/purchase-orders', methods=['POST'])
def create_purchase_order():
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({'error': 'A JSON object is required'}), 400

    supplier_id = data.get('supplier_id')
    warehouse_id = data.get('warehouse_id')
    items = data.get('items')
    if not isinstance(supplier_id, int) or isinstance(supplier_id, bool):
        return jsonify({'error': 'supplier_id is required'}), 400
    if not isinstance(warehouse_id, int) or isinstance(warehouse_id, bool):
        return jsonify({'error': 'warehouse_id is required'}), 400
    if not isinstance(items, list) or not items:
        return jsonify({'error': 'At least one item is required'}), 400

    supplier = db.session.get(Supplier, supplier_id)
    if not supplier or not supplier.is_active:
        return jsonify({'error': 'Active supplier not found'}), 404
    warehouse = db.session.get(Warehouse, warehouse_id)
    if not warehouse or not warehouse.is_active:
        return jsonify({'error': 'Active warehouse not found'}), 404

    try:
        order_date = _parse_order_date(data.get('order_date'))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    validated_items = []
    total_amount = decimal_value(0)
    total_qty = 0.0
    for item in items:
        if not isinstance(item, dict):
            return jsonify({'error': 'Each item must be a JSON object'}), 400
        product_id = item.get('product_id')
        quantity = item.get('quantity')
        unit_cost = item.get('unit_cost')
        if not isinstance(product_id, int) or isinstance(product_id, bool):
            return jsonify({'error': 'Each item requires a valid product_id'}), 400
        if not _valid_number(quantity):
            return jsonify({'error': 'Each item quantity must be a positive number'}), 400
        if not _valid_number(unit_cost, allow_zero=True):
            return jsonify({'error': 'Each item unit_cost must be a non-negative number'}), 400

        product = db.session.get(Product, product_id)
        if not product or not product.is_active:
            return jsonify({'error': f'Active product {product_id} not found'}), 404

        unit_cost = quantize_cost(unit_cost)
        total_cost = quantize_money(decimal_value(quantity) * unit_cost)
        validated_items.append((product, quantity, unit_cost, total_cost))
        total_amount += total_cost
        total_qty += quantity

    order = PurchaseOrder(
        code=f'PO-{uuid4().hex[:12].upper()}',
        supplier_id=supplier.id,
        warehouse_id=warehouse.id,
        order_date=order_date,
        status='DRAFT',
        total_amount=quantize_money(total_amount),
        total_qty=total_qty,
        notes=data.get('notes'),
        created_by=request.current_user.id
    )
    try:
        db.session.add(order)
        db.session.flush()
        for product, quantity, unit_cost, total_cost in validated_items:
            db.session.add(PurchaseOrderItem(
                purchase_order_id=order.id,
                product_id=product.id,
                quantity=quantity,
                unit_cost=unit_cost,
                total_cost=total_cost
            ))
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Purchase order creation failed')
        return jsonify({'error': 'Unable to create purchase order'}), 500

    return jsonify({
        'message': 'Purchase order created successfully',
        'data': order.to_dict()
    }), 201


@bp.route('/purchase-orders/<int:po_id>', methods=['PATCH'])
def patch_purchase_order(po_id):
    order = PurchaseOrder.query.filter_by(id=po_id).with_for_update().first()
    if not order:
        return jsonify({'error': 'Purchase order not found'}), 404
    if order.status != 'DRAFT':
        return jsonify({'error': 'Only draft purchase orders can be edited'}), 409
    if order.goods_receipts:
        return jsonify({'error': 'Purchase orders with receipts cannot be edited'}), 409

    data = request.get_json()
    if not isinstance(data, dict) or not data:
        return jsonify({'error': 'A non-empty JSON object is required'}), 400

    supplier_id = data.get('supplier_id', order.supplier_id)
    warehouse_id = data.get('warehouse_id', order.warehouse_id)
    raw_items = data.get('items')
    if not isinstance(supplier_id, int) or isinstance(supplier_id, bool):
        return jsonify({'error': 'supplier_id must be an integer'}), 400
    if not isinstance(warehouse_id, int) or isinstance(warehouse_id, bool):
        return jsonify({'error': 'warehouse_id must be an integer'}), 400
    supplier = db.session.get(Supplier, supplier_id)
    if not supplier or not supplier.is_active:
        return jsonify({'error': 'Active supplier not found'}), 404
    warehouse = db.session.get(Warehouse, warehouse_id)
    if not warehouse or not warehouse.is_active:
        return jsonify({'error': 'Active warehouse not found'}), 404

    order_date = order.order_date
    if 'order_date' in data:
        try:
            order_date = _parse_order_date(data['order_date'])
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 400
    if raw_items is None:
        raw_items = [
            {
                'product_id': item.product_id,
                'quantity': item.quantity,
                'unit_cost': float(item.unit_cost),
            }
            for item in order.items
        ]
    if not isinstance(raw_items, list) or not raw_items:
        return jsonify({'error': 'At least one item is required'}), 400

    validated_items = []
    total_amount = decimal_value(0)
    total_qty = 0.0
    for item in raw_items:
        if not isinstance(item, dict):
            return jsonify({'error': 'Each item must be a JSON object'}), 400
        product_id = item.get('product_id')
        quantity = item.get('quantity')
        unit_cost = item.get('unit_cost')
        if not isinstance(product_id, int) or isinstance(product_id, bool):
            return jsonify({'error': 'Each item requires a valid product_id'}), 400
        if not _valid_number(quantity):
            return jsonify({'error': 'Each item quantity must be positive'}), 400
        if not _valid_number(unit_cost, allow_zero=True):
            return jsonify({'error': 'Each item unit_cost must be a non-negative number'}), 400
        product = db.session.get(Product, product_id)
        if not product or not product.is_active:
            return jsonify({'error': f'Active product {product_id} not found'}), 404
        unit_cost = quantize_cost(unit_cost)
        total_cost = quantize_money(decimal_value(quantity) * unit_cost)
        validated_items.append((product, quantity, unit_cost, total_cost))
        total_amount += total_cost
        total_qty += quantity

    if 'notes' in data and data['notes'] is not None and not isinstance(data['notes'], str):
        return jsonify({'error': 'notes must be a string or null'}), 400

    try:
        order.supplier = supplier
        order.warehouse = warehouse
        order.order_date = order_date
        order.notes = data.get('notes', order.notes)
        order.total_amount = quantize_money(total_amount)
        order.total_qty = total_qty
        order.items.clear()
        for product, quantity, unit_cost, total_cost in validated_items:
            order.items.append(PurchaseOrderItem(
                product=product,
                quantity=quantity,
                unit_cost=unit_cost,
                total_cost=total_cost,
            ))
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Purchase order update failed')
        return jsonify({'error': 'Unable to update purchase order'}), 500
    return jsonify({'data': order.to_dict()})


@bp.route('/purchase-orders/<int:po_id>/approve', methods=['POST'])
def approve_purchase_order(po_id):
    order = PurchaseOrder.query.filter_by(id=po_id).with_for_update().first()
    if not order:
        return jsonify({'error': 'Purchase order not found'}), 404
    if order.status != 'SUBMITTED':
        return jsonify({
            'error': 'Only submitted purchase orders can be approved'
        }), 409
    if order.created_by == request.current_user.id:
        return jsonify({'error': 'The purchase order creator cannot approve it'}), 403

    try:
        order.status = 'APPROVED'
        order.approved_by = request.current_user.id
        order.approved_at = db.func.current_timestamp()
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Purchase order approval failed')
        return jsonify({'error': 'Unable to approve purchase order'}), 500
    return jsonify({'data': order.to_dict()})


@bp.route('/purchase-orders/<int:po_id>/reject', methods=['POST'])
def reject_purchase_order(po_id):
    order = PurchaseOrder.query.filter_by(id=po_id).with_for_update().first()
    if not order:
        return jsonify({'error': 'Purchase order not found'}), 404
    if order.status != 'SUBMITTED':
        return jsonify({'error': 'Only submitted purchase orders can be rejected'}), 409
    if order.created_by == request.current_user.id:
        return jsonify({'error': 'The purchase order creator cannot reject it'}), 403
    try:
        order.status = 'REJECTED'
        order.rejected_by = request.current_user.id
        order.rejected_at = db.func.current_timestamp()
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Purchase order rejection failed')
        return jsonify({'error': 'Unable to reject purchase order'}), 500
    return jsonify({'data': order.to_dict()})


@bp.route('/purchase-orders/<int:po_id>/submit', methods=['POST'])
def submit_purchase_order(po_id):
    order = PurchaseOrder.query.filter_by(id=po_id).with_for_update().first()
    if not order:
        return jsonify({'error': 'Purchase order not found'}), 404
    if order.status != 'DRAFT':
        return jsonify({'error': 'Only draft purchase orders can be submitted'}), 409
    try:
        order.status = 'SUBMITTED'
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Purchase order submission failed')
        return jsonify({'error': 'Unable to submit purchase order'}), 500
    return jsonify({
        'message': 'Purchase order submitted successfully',
        'data': order.to_dict()
    }), 200


@bp.route('/purchase-orders/<int:po_id>/cancel', methods=['POST'])
def cancel_purchase_order(po_id):
    order = PurchaseOrder.query.filter_by(id=po_id).with_for_update().first()
    if not order:
        return jsonify({'error': 'Purchase order not found'}), 404
    if order.status not in {'DRAFT', 'SUBMITTED', 'APPROVED'}:
        return jsonify({
            'error': f'Purchase order cannot be cancelled from {order.status} status'
        }), 409
    if any(receipt.status == 'POSTED' for receipt in order.goods_receipts):
        return jsonify({
            'error': 'Purchase order with a posted goods receipt cannot be cancelled'
        }), 409
    try:
        for receipt in order.goods_receipts:
            if receipt.status == 'DRAFT':
                receipt.status = 'CANCELLED'
        order.status = 'CANCELLED'
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Purchase order cancellation failed')
        return jsonify({'error': 'Unable to cancel purchase order'}), 500
    return jsonify({
        'message': 'Purchase order cancelled successfully',
        'data': order.to_dict()
    }), 200


@bp.route('/goods-receipts', methods=['GET'])
def get_goods_receipts():
    page = max(request.args.get('page', 1, type=int), 1)
    per_page = min(max(request.args.get('per_page', 10, type=int), 1), 100)
    query = GoodsReceipt.query
    status = request.args.get('status', type=str)
    purchase_order_id = request.args.get('purchase_order_id', type=int)
    warehouse_id = request.args.get('warehouse_id', type=int)
    if status:
        query = query.filter_by(status=status.upper())
    if purchase_order_id:
        query = query.filter_by(purchase_order_id=purchase_order_id)
    if warehouse_id is not None:
        query = query.join(PurchaseOrder).filter(
            PurchaseOrder.warehouse_id == warehouse_id
        )
    pagination = query.order_by(GoodsReceipt.id.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    return jsonify({
        'data': [receipt.to_dict() for receipt in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
    })


@bp.route('/goods-receipts', methods=['POST'])
def create_goods_receipt():
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({'error': 'A JSON object is required'}), 400
    purchase_order_id = data.get('purchase_order_id')
    items = data.get('items')
    if not isinstance(purchase_order_id, int) or isinstance(purchase_order_id, bool):
        return jsonify({'error': 'purchase_order_id is required'}), 400
    if not isinstance(items, list) or not items:
        return jsonify({'error': 'At least one item is required'}), 400

    order = PurchaseOrder.query.filter_by(
        id=purchase_order_id
    ).with_for_update().first()
    if not order:
        return jsonify({'error': 'Purchase order not found'}), 404
    if order.status not in {'APPROVED', 'PARTIALLY_RECEIVED'}:
        return jsonify({'error': 'Purchase order must be approved before receipt'}), 409

    order_items = {item.id: item for item in order.items}
    validated = []
    for item_data in items:
        if not isinstance(item_data, dict):
            return jsonify({'error': 'Each item must be a JSON object'}), 400
        item_id = item_data.get('purchase_order_item_id')
        quantity = item_data.get('quantity')
        if not isinstance(item_id, int) or isinstance(item_id, bool):
            return jsonify({'error': 'Each receipt item requires a purchase_order_item_id'}), 400
        if not _valid_number(quantity):
            return jsonify({'error': 'Receipt quantity must be positive'}), 400
        order_item = order_items.get(item_id)
        if not order_item:
            return jsonify({'error': f'Purchase order item {item_id} not found'}), 400
        already_requested = sum(
            existing_quantity
            for existing_id, existing_quantity in validated
            if existing_id == item_id
        )
        if quantity + already_requested > order_item.remaining_qty:
            return jsonify({
                'error': f'Receipt exceeds remaining quantity for item {item_id}'
            }), 400
        validated.append((item_id, quantity))

    try:
        received_date = _parse_order_date(data.get('received_date'))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    receipt = GoodsReceipt(
        code=f'GR-{uuid4().hex[:12].upper()}',
        purchase_order_id=order.id,
        received_date=received_date,
        notes=data.get('notes'),
        created_by=request.current_user.id,
        status='DRAFT'
    )
    try:
        db.session.add(receipt)
        db.session.flush()
        for item_id, quantity in validated:
            order_item = order_items[item_id]
            db.session.add(GoodsReceiptItem(
                goods_receipt_id=receipt.id,
                purchase_order_item_id=item_id,
                product_id=order_item.product_id,
                quantity=quantity,
                unit_cost=order_item.unit_cost
            ))
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Goods receipt creation failed')
        return jsonify({'error': 'Unable to create goods receipt'}), 500
    return jsonify({'data': receipt.to_dict()}), 201


@bp.route('/goods-receipts/<int:receipt_id>', methods=['GET'])
def get_goods_receipt(receipt_id):
    receipt = db.session.get(GoodsReceipt, receipt_id)
    if not receipt:
        return jsonify({'error': 'Goods receipt not found'}), 404
    return jsonify({'data': receipt.to_dict()})


@bp.route('/goods-receipts/<int:receipt_id>', methods=['PATCH'])
def update_goods_receipt(receipt_id):
    receipt = GoodsReceipt.query.filter_by(id=receipt_id).with_for_update().first()
    if not receipt:
        return jsonify({'error': 'Goods receipt not found'}), 404
    if receipt.status != 'DRAFT' or receipt.vendor_bill:
        return jsonify({'error': 'Only draft receipts without a vendor bill can be edited'}), 409
    data = request.get_json()
    items = data.get('items') if isinstance(data, dict) else None
    if not isinstance(items, list) or not items:
        return jsonify({'error': 'At least one receipt item is required'}), 400
    if data.get('purchase_order_id', receipt.purchase_order_id) != receipt.purchase_order_id:
        return jsonify({'error': 'A draft receipt cannot be moved to a different purchase order'}), 409

    order = PurchaseOrder.query.filter_by(
        id=receipt.purchase_order_id
    ).with_for_update().first()
    if not order or order.status not in {'APPROVED', 'PARTIALLY_RECEIVED'}:
        return jsonify({'error': 'The source purchase order is no longer eligible for receipt'}), 409
    order_items = {item.id: item for item in order.items}
    other_draft_quantities = {}
    for other_receipt in order.goods_receipts:
        if other_receipt.id == receipt.id or other_receipt.status != 'DRAFT':
            continue
        for other_item in other_receipt.items:
            other_draft_quantities[other_item.purchase_order_item_id] = (
                other_draft_quantities.get(other_item.purchase_order_item_id, 0)
                + other_item.quantity
            )

    requested_quantities = {}
    validated = []
    for item_data in items:
        if not isinstance(item_data, dict):
            return jsonify({'error': 'Each receipt item must be a JSON object'}), 400
        item_id = item_data.get('purchase_order_item_id')
        quantity = item_data.get('quantity')
        if not isinstance(item_id, int) or isinstance(item_id, bool) or not _valid_number(quantity):
            return jsonify({'error': 'Each receipt item requires a valid PO item and positive quantity'}), 400
        order_item = order_items.get(item_id)
        if not order_item:
            return jsonify({'error': f'Purchase order item {item_id} not found'}), 400
        requested_quantities[item_id] = requested_quantities.get(item_id, 0) + quantity
        if requested_quantities[item_id] + other_draft_quantities.get(item_id, 0) > order_item.remaining_qty:
            return jsonify({'error': f'Receipt exceeds remaining quantity for item {item_id}'}), 409
        validated.append((order_item, quantity))
    try:
        received_date = _parse_order_date(data.get('received_date', receipt.received_date.isoformat()))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    notes = data.get('notes', receipt.notes)
    if notes is not None and not isinstance(notes, str):
        return jsonify({'error': 'notes must be a string or null'}), 400

    try:
        receipt.received_date = received_date
        receipt.notes = notes
        receipt.items.clear()
        db.session.flush()
        for order_item, quantity in validated:
            receipt.items.append(GoodsReceiptItem(
                purchase_order_item_id=order_item.id,
                product_id=order_item.product_id,
                quantity=quantity,
                unit_cost=order_item.unit_cost
            ))
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Goods receipt draft update failed')
        return jsonify({'error': 'Unable to update goods receipt draft'}), 500
    return jsonify({'data': receipt.to_dict()})


@bp.route('/goods-receipts/<int:receipt_id>/post', methods=['POST'])
def post_goods_receipt(receipt_id):
    receipt = GoodsReceipt.query.filter_by(id=receipt_id).with_for_update().first()
    if not receipt:
        return jsonify({'error': 'Goods receipt not found'}), 404
    if receipt.status != 'DRAFT':
        return jsonify({'error': 'Only draft goods receipts can be posted'}), 409
    if receipt.vendor_bill:
        return jsonify({'error': 'A vendor bill already exists for this receipt'}), 409

    order = receipt.purchase_order
    locked_order_items = {
        item.id: item
        for item in PurchaseOrderItem.query.filter(
            PurchaseOrderItem.purchase_order_id == order.id
        ).order_by(PurchaseOrderItem.id).with_for_update().all()
    }
    for receipt_item in receipt.items:
        order_item = locked_order_items.get(receipt_item.purchase_order_item_id)
        if not order_item or receipt_item.quantity > order_item.remaining_qty:
            return jsonify({'error': 'Receipt exceeds remaining purchase order quantity'}), 409

    distinct_product_ids = sorted({item.product_id for item in receipt.items})
    balances = {
        product_id: InventoryBalance.get_or_create(
            product_id=product_id,
            warehouse_id=order.warehouse_id,
            for_update=True
        )
        for product_id in distinct_product_ids
    }

    try:
        receipt_total = decimal_value(0)
        for item in receipt.items:
            balance = balances[item.product_id]
            previous_quantity = decimal_value(balance.quantity_on_hand)
            received_quantity = decimal_value(item.quantity)
            new_quantity = previous_quantity + received_quantity
            previous_value = previous_quantity * decimal_value(balance.average_cost)
            incoming_value = received_quantity * decimal_value(item.unit_cost)
            balance.quantity_on_hand = new_quantity
            if new_quantity > 0:
                balance.average_cost = quantize_cost(
                    (previous_value + incoming_value) / new_quantity
                )
            balance.last_cost = item.unit_cost

            receipt_total += incoming_value
            db.session.add(StockMovement(
                product_id=item.product_id,
                warehouse_id=order.warehouse_id,
                movement_type='IN',
                quantity_delta=item.quantity,
                unit_cost=item.unit_cost,
                reference_type='GOODS_RECEIPT',
                reference_id=receipt.id,
                created_by=request.current_user.id
            ))

        receipt.status = 'POSTED'
        receipt.posted_by = request.current_user.id
        receipt.posted_at = db.func.current_timestamp()
        order.status = (
            'RECEIVED'
            if all(item.remaining_qty <= 1e-9 for item in locked_order_items.values())
            else 'PARTIALLY_RECEIVED'
        )
        bill = VendorBill(
            code=f'VB-{uuid4().hex[:12].upper()}',
            goods_receipt=receipt,
            supplier_id=order.supplier_id,
            total_amount=quantize_money(receipt_total),
            status='OPEN'
        )
        db.session.add(bill)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Goods receipt posting failed')
        return jsonify({'error': 'Unable to post goods receipt'}), 500

    return jsonify({
        'message': 'Goods receipt posted successfully',
        'data': receipt.to_dict(),
        'vendor_bill': bill.to_dict()
    }), 200


@bp.route('/goods-receipts/<int:receipt_id>/cancel', methods=['POST'])
def cancel_goods_receipt(receipt_id):
    receipt = GoodsReceipt.query.filter_by(id=receipt_id).with_for_update().first()
    if not receipt:
        return jsonify({'error': 'Goods receipt not found'}), 404
    if receipt.status != 'DRAFT':
        return jsonify({'error': 'Only draft goods receipts can be cancelled'}), 409
    if receipt.vendor_bill:
        return jsonify({'error': 'A receipt with a vendor bill cannot be cancelled'}), 409
    receipt.status = 'CANCELLED'
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Goods receipt cancellation failed')
        return jsonify({'error': 'Unable to cancel goods receipt'}), 500
    return jsonify({'data': receipt.to_dict()})


@bp.route('/vendor-bills', methods=['GET'])
def get_vendor_bills():
    page = max(request.args.get('page', 1, type=int), 1)
    per_page = min(max(request.args.get('per_page', 10, type=int), 1), 100)
    query = VendorBill.query
    status = request.args.get('status', type=str)
    supplier_id = request.args.get('supplier_id', type=int)
    warehouse_id = request.args.get('warehouse_id', type=int)
    if status:
        query = query.filter_by(status=status.upper())
    if supplier_id:
        query = query.filter_by(supplier_id=supplier_id)
    if warehouse_id is not None:
        query = query.join(VendorBill.goods_receipt).join(
            GoodsReceipt.purchase_order
        ).filter(PurchaseOrder.warehouse_id == warehouse_id)
    pagination = query.order_by(VendorBill.id.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    return jsonify({
        'data': [bill.to_dict() for bill in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
    })


@bp.route('/vendor-bills', methods=['POST'])
def create_vendor_bill():
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({'error': 'A JSON object is required'}), 400
    goods_receipt_id = data.get('goods_receipt_id')
    if not isinstance(goods_receipt_id, int) or isinstance(goods_receipt_id, bool):
        return jsonify({'error': 'goods_receipt_id is required'}), 400
    receipt = GoodsReceipt.query.filter_by(
        id=goods_receipt_id
    ).with_for_update().first()
    if not receipt:
        return jsonify({'error': 'Goods receipt not found'}), 404
    if receipt.status != 'POSTED':
        return jsonify({'error': 'Only posted goods receipts can be billed'}), 409
    if receipt.vendor_bill:
        return jsonify({'error': 'A vendor bill already exists for this receipt'}), 409
    total_amount = quantize_money(sum(
        (
            decimal_value(item.quantity) * decimal_value(item.unit_cost)
            for item in receipt.items
        ),
        decimal_value(0)
    ))
    bill = VendorBill(
        code=f'VB-{uuid4().hex[:12].upper()}',
        goods_receipt=receipt,
        supplier_id=receipt.purchase_order.supplier_id,
        total_amount=total_amount,
        status='OPEN'
    )
    try:
        db.session.add(bill)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Vendor bill creation failed')
        return jsonify({'error': 'Unable to create vendor bill'}), 500
    return jsonify({
        'message': 'Vendor bill created successfully',
        'data': bill.to_dict()
    }), 201


@bp.route('/vendor-bills/<int:bill_id>', methods=['GET'])
def get_vendor_bill(bill_id):
    bill = db.session.get(VendorBill, bill_id)
    if not bill:
        return jsonify({'error': 'Vendor bill not found'}), 404
    return jsonify({'data': bill.to_dict()})


@bp.route('/supplier-payments', methods=['GET'])
def get_supplier_payments():
    page = max(request.args.get('page', 1, type=int), 1)
    per_page = min(max(request.args.get('per_page', 10, type=int), 1), 100)
    query = SupplierPayment.query
    status = request.args.get('status', type=str)
    supplier_id = request.args.get('supplier_id', type=int)
    warehouse_id = request.args.get('warehouse_id', type=int)
    if status:
        query = query.filter_by(status=status.upper())
    if supplier_id:
        query = query.filter_by(supplier_id=supplier_id)
    if warehouse_id is not None:
        warehouse_payment_ids = (
            db.session.query(SupplierPaymentAllocation.payment_id)
            .join(SupplierPaymentAllocation.vendor_bill)
            .join(VendorBill.goods_receipt)
            .join(GoodsReceipt.purchase_order)
            .filter(PurchaseOrder.warehouse_id == warehouse_id)
        )
        query = query.filter(or_(
            SupplierPayment.id.in_(warehouse_payment_ids),
            SupplierPayment.source_vendor_bill_id.in_(
                db.session.query(VendorBill.id)
                .join(GoodsReceipt, GoodsReceipt.id == VendorBill.goods_receipt_id)
                .join(PurchaseOrder, PurchaseOrder.id == GoodsReceipt.purchase_order_id)
                .filter(PurchaseOrder.warehouse_id == warehouse_id)
            )
        ))
    pagination = query.order_by(SupplierPayment.id.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    rows = [payment.to_dict() for payment in pagination.items]
    if request.current_user.role == 'viewer':
        rows = [{
            'id': row['id'],
            'code': row['code'],
            'supplier_name': row['supplier_name'],
            'payment_date': row['payment_date'],
            'status': row['status'],
        } for row in rows]
    return jsonify({
        'data': rows,
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
    })


@bp.route('/supplier-payments', methods=['POST'])
def create_supplier_payment():
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({'error': 'A JSON object is required'}), 400
    supplier_id = data.get('supplier_id')
    source_vendor_bill_id = data.get('vendor_bill_id')
    amount = data.get('amount')
    payment_method = data.get('payment_method', 'BANK_TRANSFER')
    if not isinstance(supplier_id, int) or isinstance(supplier_id, bool):
        return jsonify({'error': 'supplier_id is required'}), 400
    if not _valid_number(amount):
        return jsonify({'error': 'amount must be a positive number'}), 400
    amount = quantize_money(amount)
    if amount <= 0:
        return jsonify({'error': 'amount must be at least 0.01'}), 400
    if (
        not isinstance(payment_method, str)
        or payment_method not in {'CASH', 'BANK_TRANSFER', 'CREDIT_CARD'}
    ):
        return jsonify({'error': 'Unsupported payment_method'}), 400

    supplier = db.session.get(Supplier, supplier_id)
    if not supplier:
        return jsonify({'error': 'Supplier not found'}), 404
    source_bill = None
    if source_vendor_bill_id is not None:
        if not isinstance(source_vendor_bill_id, int) or isinstance(source_vendor_bill_id, bool):
            return jsonify({'error': 'vendor_bill_id must be an integer'}), 400
        source_bill = db.session.get(VendorBill, source_vendor_bill_id)
        if not source_bill or source_bill.supplier_id != supplier.id:
            return jsonify({'error': 'Vendor bill not found for this supplier'}), 404
        if source_bill.status == 'PAID':
            return jsonify({'error': 'A paid vendor bill cannot be selected'}), 409
    payment = SupplierPayment(
        code=f'SP-{uuid4().hex[:16].upper()}',
        supplier_id=supplier.id,
        source_vendor_bill=source_bill,
        amount=amount,
        payment_method=payment_method,
        status='DRAFT'
    )
    try:
        db.session.add(payment)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Supplier payment creation failed')
        return jsonify({'error': 'Unable to create supplier payment'}), 500
    return jsonify({'data': payment.to_dict()}), 201


@bp.route('/supplier-payments/record-and-post', methods=['POST'])
def record_and_post_supplier_payment():
    required = ('supplier_payments.create', 'supplier_payments.allocate', 'supplier_payments.post')
    if any(not has_permission(request.current_user, code) for code in required):
        return jsonify({'error': 'Creating, allocating, and posting supplier payments are all required'}), 403
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({'error': 'A JSON object is required'}), 400
    bill_id = data.get('vendor_bill_id')
    amount = data.get('amount')
    method = data.get('payment_method', 'BANK_TRANSFER')
    if not isinstance(bill_id, int) or isinstance(bill_id, bool):
        return jsonify({'error': 'vendor_bill_id is required'}), 400
    if not _valid_number(amount):
        return jsonify({'error': 'amount must be a positive number'}), 400
    amount = quantize_money(amount)
    if amount <= 0:
        return jsonify({'error': 'amount must be at least 0.01'}), 400
    if not isinstance(method, str) or method not in {'CASH', 'BANK_TRANSFER', 'CREDIT_CARD'}:
        return jsonify({'error': 'Unsupported payment_method'}), 400

    bill = VendorBill.query.filter_by(id=bill_id).with_for_update().first()
    if not bill:
        return jsonify({'error': 'Vendor bill not found'}), 404
    draft_reserved = sum(
        (decimal_value(item.amount) for item in bill.allocations if item.payment.status == 'DRAFT'),
        decimal_value(0)
    )
    available = max(decimal_value(0), decimal_value(bill.balance_due) - draft_reserved)
    if amount > available:
        return jsonify({'error': 'Payment exceeds the vendor bill balance available to this transaction'}), 409

    payment = SupplierPayment(
        code=f'SP-{uuid4().hex[:16].upper()}',
        supplier_id=bill.supplier_id,
        source_vendor_bill=bill,
        amount=amount,
        payment_method=method,
        status='POSTED'
    )
    payment.allocations.append(SupplierPaymentAllocation(vendor_bill=bill, amount=amount))
    try:
        db.session.add(payment)
        db.session.flush()
        bill.status = 'PAID' if bill.balance_due <= decimal_value('0.005') else 'PARTIALLY_PAID'
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Atomic supplier payment failed')
        return jsonify({'error': 'Unable to record and post supplier payment'}), 500
    return jsonify({'data': payment.to_dict()}), 201


@bp.route('/supplier-payments/<int:payment_id>/allocations', methods=['POST'])
def allocate_supplier_payment(payment_id):
    data = request.get_json()
    if not isinstance(data, dict) or not isinstance(data.get('allocations'), list):
        return jsonify({'error': 'allocations must be a non-empty array'}), 400
    requested = data['allocations']
    if not requested:
        return jsonify({'error': 'allocations must be a non-empty array'}), 400

    payment = SupplierPayment.query.filter_by(
        id=payment_id
    ).with_for_update().first()
    if not payment:
        return jsonify({'error': 'Supplier payment not found'}), 404
    if payment.status != 'DRAFT':
        return jsonify({'error': 'Only draft supplier payments can be allocated'}), 409

    requested_by_bill = {}
    for allocation in requested:
        if not isinstance(allocation, dict):
            return jsonify({'error': 'Each allocation must be a JSON object'}), 400
        bill_id = allocation.get('vendor_bill_id')
        amount = allocation.get('amount')
        if not isinstance(bill_id, int) or isinstance(bill_id, bool):
            return jsonify({'error': 'Each allocation requires vendor_bill_id'}), 400
        if not _valid_number(amount):
            return jsonify({'error': 'Each allocation amount must be positive'}), 400
        rounded_amount = quantize_money(amount)
        if rounded_amount <= 0:
            return jsonify({'error': 'Allocation amount must be at least 0.01'}), 400
        if bill_id in requested_by_bill:
            return jsonify({
                'error': 'A vendor bill may appear only once per allocation request'
            }), 400
        requested_by_bill[bill_id] = rounded_amount

    existing_total = sum(
        (decimal_value(item.amount) for item in payment.allocations),
        decimal_value(0)
    )
    if quantize_money(
        existing_total + sum(requested_by_bill.values(), decimal_value(0))
    ) > quantize_money(payment.amount):
        return jsonify({'error': 'Allocations exceed payment amount'}), 400

    bills = (
        VendorBill.query
        .filter(VendorBill.id.in_(sorted(requested_by_bill)))
        .order_by(VendorBill.id)
        .with_for_update()
        .all()
    )
    bill_by_id = {bill.id: bill for bill in bills}
    missing_ids = set(requested_by_bill) - set(bill_by_id)
    if missing_ids:
        return jsonify({
            'error': 'Vendor bill not found for this supplier',
            'vendor_bill_ids': sorted(missing_ids)
        }), 404

    existing_by_bill = {}
    for allocation in payment.allocations:
        existing_by_bill[allocation.vendor_bill_id] = (
            existing_by_bill.get(allocation.vendor_bill_id, decimal_value(0))
            + decimal_value(allocation.amount)
        )
    for bill_id, amount in requested_by_bill.items():
        bill = bill_by_id[bill_id]
        if bill.supplier_id != payment.supplier_id:
            return jsonify({
                'error': 'All vendor bills must belong to the payment supplier'
            }), 400
        reserved_by_other_drafts = sum(
            (decimal_value(item.amount)
            for item in bill.allocations
            if item.payment.status == 'DRAFT' and item.payment_id != payment.id),
            decimal_value(0)
        )
        available_balance = decimal_value(bill.balance_due) - reserved_by_other_drafts
        if quantize_money(
            existing_by_bill.get(bill_id, decimal_value(0)) + amount
        ) > quantize_money(available_balance):
            return jsonify({
                'error': 'Allocation exceeds the outstanding vendor bill balance',
                'vendor_bill_id': bill_id
            }), 400

    try:
        for bill_id, amount in requested_by_bill.items():
            allocation = SupplierPaymentAllocation(
                vendor_bill_id=bill_id,
                amount=amount
            )
            allocation.vendor_bill = bill_by_id[bill_id]
            payment.allocations.append(allocation)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Supplier payment allocation failed')
        return jsonify({'error': 'Unable to allocate supplier payment'}), 500
    return jsonify({
        'message': 'Supplier payment allocations added successfully',
        'data': payment.to_dict()
    }), 200


@bp.route('/supplier-payments/<int:payment_id>/post', methods=['POST'])
def post_supplier_payment(payment_id):
    payment = SupplierPayment.query.filter_by(
        id=payment_id
    ).with_for_update().first()
    if not payment:
        return jsonify({'error': 'Supplier payment not found'}), 404
    if payment.status != 'DRAFT':
        return jsonify({'error': 'Only draft supplier payments can be posted'}), 409

    payload = request.get_json(silent=True)
    allocations = payload.get('allocations', []) if isinstance(payload, dict) else []
    if not isinstance(allocations, list):
        return jsonify({'error': 'allocations must be a list'}), 400

    if payment.allocations and allocations:
        return jsonify({
            'error': 'Draft allocations already exist; omit allocations when posting'
        }), 409

    validated = [
        (allocation.vendor_bill, allocation.amount)
        for allocation in payment.allocations
    ]
    allocated_total = decimal_value(0)
    requested_by_bill = {}
    for allocation in allocations if not payment.allocations else []:
        if not isinstance(allocation, dict):
            return jsonify({'error': 'Each allocation must be a JSON object'}), 400
        bill_id = allocation.get('vendor_bill_id')
        amount = allocation.get('amount')
        if not isinstance(bill_id, int) or isinstance(bill_id, bool):
            return jsonify({'error': 'Each allocation requires vendor_bill_id'}), 400
        if not _valid_number(amount):
            return jsonify({'error': 'Each allocation amount must be positive'}), 400
        bill = VendorBill.query.filter_by(id=bill_id).with_for_update().first()
        if not bill or bill.supplier_id != payment.supplier_id:
            return jsonify({'error': f'Vendor bill {bill_id} not found for this supplier'}), 404
        allocated_to_bill = sum(
            (decimal_value(item.amount) for item in bill.allocations
            if item.payment.status == 'POSTED'),
            decimal_value(0)
        )
        reserved_by_other_drafts = sum(
            (decimal_value(item.amount)
            for item in bill.allocations
            if item.payment.status == 'DRAFT' and item.payment_id != payment.id),
            decimal_value(0)
        )
        requested_by_bill[bill.id] = (
            requested_by_bill.get(bill.id, decimal_value(0))
            + quantize_money(amount)
        )
        if quantize_money(
            allocated_to_bill + reserved_by_other_drafts + requested_by_bill[bill.id],
        ) > quantize_money(bill.total_amount):
            return jsonify({'error': f'Allocation exceeds bill {bill_id} balance'}), 400
        validated.append((bill, quantize_money(amount)))
        allocated_total += quantize_money(amount)

    if payment.allocations:
        allocated_total = sum(
            (decimal_value(amount) for _, amount in validated),
            decimal_value(0)
        )
        allocated_by_bill = {}
        for bill, amount in validated:
            if bill is None:
                return jsonify({'error': 'An allocated vendor bill no longer exists'}), 404
            allocated_by_bill[bill.id] = (
                allocated_by_bill.get(bill.id, decimal_value(0))
                + decimal_value(amount)
            )
        locked_bills = (
            VendorBill.query
            .filter(VendorBill.id.in_(sorted(allocated_by_bill)))
            .order_by(VendorBill.id)
            .with_for_update()
            .all()
        )
        bill_by_id = {bill.id: bill for bill in locked_bills}
        if len(bill_by_id) != len(allocated_by_bill):
            return jsonify({'error': 'An allocated vendor bill no longer exists'}), 404
        for bill_id, amount in allocated_by_bill.items():
            bill = bill_by_id[bill_id]
            if bill.supplier_id != payment.supplier_id:
                return jsonify({
                    'error': 'All vendor bills must belong to the payment supplier'
                }), 409
            reserved_by_other_drafts = sum(
                (decimal_value(item.amount)
                for item in bill.allocations
                if item.payment.status == 'DRAFT' and item.payment_id != payment.id),
                decimal_value(0)
            )
            available_balance = decimal_value(bill.balance_due) - reserved_by_other_drafts
            if quantize_money(amount) > quantize_money(available_balance):
                return jsonify({
                    'error': 'Payment allocation exceeds the outstanding vendor bill balance',
                    'vendor_bill_id': bill_id
                }), 409
        validated = [
            (bill_by_id[bill_id], amount)
            for bill_id, amount in allocated_by_bill.items()
        ]
    if quantize_money(allocated_total) > quantize_money(payment.amount):
        return jsonify({'error': 'Allocations exceed payment amount'}), 400

    try:
        if not payment.allocations:
            for bill, amount in validated:
                bill.allocations.append(SupplierPaymentAllocation(
                    payment_id=payment.id,
                    vendor_bill_id=bill.id,
                    amount=amount
                ))
        payment.status = 'POSTED'
        db.session.flush()
        for bill, _ in validated:
            bill.status = (
                'PAID'
                if bill.balance_due <= decimal_value('0.005')
                else 'PARTIALLY_PAID'
            )
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Supplier payment posting failed')
        return jsonify({'error': 'Unable to post supplier payment'}), 500
    return jsonify({'data': payment.to_dict()})


@bp.route('/purchase-orders/<int:po_id>', methods=['GET'])
def get_purchase_order(po_id):
    order = db.session.get(PurchaseOrder, po_id)
    if not order:
        return jsonify({'error': 'Purchase order not found'}), 404
    return jsonify({'data': order.to_dict()})


@bp.route('/purchase-orders/<int:po_id>/post', methods=['POST'])
def post_purchase_order(po_id):
    order = PurchaseOrder.query.filter_by(id=po_id).with_for_update().first()
    if not order:
        return jsonify({'error': 'Purchase order not found'}), 404
    if order.status not in {'APPROVED', 'PARTIALLY_RECEIVED'}:
        return jsonify({'error': 'Purchase order must be approved before posting'}), 409
    if order.remaining_qty <= 0:
        return jsonify({'error': 'Purchase order has no remaining quantity'}), 409

    remaining_items = [
        item for item in order.items if item.remaining_qty > 0
    ]
    receipt = GoodsReceipt(
        code=f'GR-{uuid4().hex[:12].upper()}',
        purchase_order_id=order.id,
        received_date=date.today(),
        created_by=request.current_user.id,
        status='DRAFT',
        notes='Complete remaining purchase order quantity'
    )

    try:
        db.session.add(receipt)
        db.session.flush()
        for item in remaining_items:
            db.session.add(GoodsReceiptItem(
                goods_receipt_id=receipt.id,
                purchase_order_item_id=item.id,
                product_id=item.product_id,
                quantity=item.remaining_qty,
                unit_cost=item.unit_cost
            ))
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Final goods receipt creation failed')
        return jsonify({'error': 'Unable to create final goods receipt'}), 500

    return post_goods_receipt(receipt.id)
