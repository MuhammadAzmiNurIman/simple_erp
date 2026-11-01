from datetime import date, datetime, time

from flask import Blueprint, request, jsonify
from sqlalchemy.orm import joinedload, selectinload
from app import db
from app.money import cost_json, decimal_value, money_json
from ..finance import get_payables_response, get_receivables_response
from app.models import (
    GoodsReceipt,
    InventoryBalance,
    Invoice,
    Product,
    PurchaseOrder,
    SalesOrder,
    Shipment,
    StockMovement,
    ShipmentItem,
    VendorBill,
    Warehouse,
    Category,
    CustomerPaymentAllocation,
    SupplierPaymentAllocation,
)

bp = Blueprint('reports', __name__)


def _report_filters():
    try:
        from_date = date.fromisoformat(request.args['from_date']) if 'from_date' in request.args else None
        to_date = date.fromisoformat(request.args['to_date']) if 'to_date' in request.args else None
        warehouse_id = int(request.args['warehouse_id']) if 'warehouse_id' in request.args else None
    except ValueError:
        raise ValueError('Invalid date or warehouse filter') from None
    if from_date and to_date and from_date > to_date:
        raise ValueError('from_date cannot be later than to_date')
    if warehouse_id is not None and warehouse_id <= 0:
        raise ValueError('warehouse_id must be a positive integer')
    return from_date, to_date, warehouse_id


def _optional_positive_int(name):
    raw = request.args.get(name)
    if raw is None:
        return None
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f'{name} must be an integer') from None
    if value <= 0:
        raise ValueError(f'{name} must be a positive integer')
    return value


def _apply_date_filters(query, column, from_date, to_date):
    if from_date:
        query = query.filter(column >= datetime.combine(from_date, time.min))
    if to_date:
        query = query.filter(column <= datetime.combine(to_date, time.max))
    return query


def _paginate(query):
    page = max(request.args.get('page', 1, type=int), 1)
    per_page = min(max(request.args.get('per_page', 10, type=int), 1), 100)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return pagination


@bp.route('/inventory/low-stock', methods=['GET'])
@bp.route('/reports/low-stock', methods=['GET'])
def get_low_stock_report():
    """Laporan barang di bawah minimal stock (min_stock)"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    warehouse_id = request.args.get('warehouse_id', type=int)
    product_id = request.args.get('product_id', type=int)
    category_id = request.args.get('category_id', type=int)

    query = db.session.query(
        Product.id,
        Product.sku,
        Product.name,
        Product.min_stock,
        InventoryBalance.quantity_on_hand,
        InventoryBalance.quantity_reserved,
        Category.name.label('category_name'),
        Warehouse.name.label('warehouse_name'),
        Warehouse.code.label('warehouse_code'),
        (Product.min_stock - InventoryBalance.quantity_on_hand).label('stock_deficit')
    ).select_from(InventoryBalance)\
     .join(Product, InventoryBalance.product_id == Product.id)\
     .outerjoin(Category, Product.category_id == Category.id)\
     .join(Warehouse, InventoryBalance.warehouse_id == Warehouse.id)\
     .filter(InventoryBalance.quantity_on_hand < Product.min_stock)

    if warehouse_id:
        query = query.filter(InventoryBalance.warehouse_id == warehouse_id)
    if product_id is not None:
        query = query.filter(Product.id == product_id)
    if category_id is not None:
        query = query.filter(Product.category_id == category_id)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'data': [{
            'product_id': row.id,
            'sku': row.sku,
            'name': row.name,
            'category': row.category_name,
            'warehouse': row.warehouse_name,
            'warehouse_code': row.warehouse_code,
            'min_stock': row.min_stock,
            'quantity_on_hand': row.quantity_on_hand,
            'quantity_reserved': row.quantity_reserved,
            'stock_deficit': row.stock_deficit if row.stock_deficit else 0.0
        } for row in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
    })


@bp.route('/reports/turnover', methods=['GET'])
def get_turnover_report():
    """Laporan turnover barang berdasarkan stock movement"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    warehouse_id = request.args.get('warehouse_id', type=int)
    movement_type = request.args.get('type', type=str)  # IN, OUT, ADJUSTMENT

    from app.models import StockMovement

    query = db.session.query(
        StockMovement.product_id,
        Product.sku,
        Product.name,
        db.func.sum(db.func.abs(StockMovement.quantity_delta)).label('total_quantity'),
        StockMovement.movement_type,
        db.func.count(StockMovement.id).label('movement_count')
    ).select_from(StockMovement)\
     .join(Product, StockMovement.product_id == Product.id)\

    if warehouse_id:
        query = query.filter(StockMovement.warehouse_id == warehouse_id)

    if movement_type:
        query = query.filter(StockMovement.movement_type == movement_type)

    pagination = query    .group_by(StockMovement.product_id, StockMovement.movement_type)\
        .paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'data': [{
            'product_id': row.product_id,
            'sku': row.sku,
            'name': row.name,
            'total_quantity': float(row.total_quantity) if row.total_quantity else 0.0,
            'movement_count': row.movement_count,
            'movement_type': row.movement_type
        } for row in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
    })


@bp.route('/reports/replenishment', methods=['GET'])
def get_replenishment_report():
    """Laporan barang yang perlu di-reorder (restock)"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    warehouse_id = request.args.get('warehouse_id', type=int)

    query = db.session.query(
        Product.id,
        Product.sku,
        Product.name,
        Product.min_stock,
        InventoryBalance.quantity_on_hand,
        Category.name.label('category_name'),
        Warehouse.name.label('warehouse_name'),
        Warehouse.code.label('warehouse_code'),
        ((Product.min_stock * 2) - InventoryBalance.quantity_on_hand).label('recommended_qty')
    ).select_from(InventoryBalance)\
     .join(Product, InventoryBalance.product_id == Product.id)\
     .outerjoin(Category, Product.category_id == Category.id)\
     .join(Warehouse, InventoryBalance.warehouse_id == Warehouse.id)\
     .filter(InventoryBalance.quantity_on_hand < Product.min_stock)

    if warehouse_id:
        query = query.filter(InventoryBalance.warehouse_id == warehouse_id)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'data': [{
            'product_id': row.id,
            'sku': row.sku,
            'name': row.name,
            'category': row.category_name,
            'warehouse': row.warehouse_name,
            'warehouse_code': row.warehouse_code,
            'min_stock': row.min_stock,
            'quantity_on_hand': row.quantity_on_hand,
            'stock_deficit': max(0, row.min_stock - row.quantity_on_hand),
            'recommended_qty': max(0, (row.min_stock * 2) - row.quantity_on_hand)
        } for row in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
    })


@bp.route('/reports/sales', methods=['GET'])
def get_sales_report():
    try:
        from_date, to_date, warehouse_id = _report_filters()
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    query = (
        Invoice.query
        .join(Shipment, Shipment.id == Invoice.shipment_id)
        .join(SalesOrder, SalesOrder.id == Shipment.sales_order_id)
    )
    query = _apply_date_filters(query, Invoice.created_at, from_date, to_date)
    try:
        customer_id = _optional_positive_int('customer_id')
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    if warehouse_id is not None:
        query = query.filter(SalesOrder.warehouse_id == warehouse_id)
    if customer_id is not None:
        query = query.filter(SalesOrder.customer_id == customer_id)
    status = request.args.get('status')
    if status:
        query = query.filter(Invoice.status == status.upper())
    total_sales_amount = query.with_entities(
        db.func.coalesce(db.func.sum(Invoice.total_amount), 0)
    ).scalar()
    pagination = _paginate(query.options(
        joinedload(Invoice.shipment).joinedload(Shipment.sales_order).joinedload(SalesOrder.customer),
        joinedload(Invoice.shipment).joinedload(Shipment.sales_order).joinedload(SalesOrder.warehouse),
        joinedload(Invoice.shipment).selectinload(Shipment.items).joinedload(ShipmentItem.product).joinedload(Product.unit),
        selectinload(Invoice.allocations).joinedload(CustomerPaymentAllocation.payment),
    ).order_by(Invoice.created_at.desc(), Invoice.id.desc()))
    data = []
    for invoice in pagination.items:
        order = invoice.shipment.sales_order
        data.append({
            **invoice.to_dict(),
            'customer_name': order.customer.name,
            'warehouse_name': order.warehouse.name,
        })
    return jsonify({
        'data': data,
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
        'period': {
            'from_date': from_date.isoformat() if from_date else None,
            'to_date': to_date.isoformat() if to_date else None,
        },
        'total_sales_amount': money_json(total_sales_amount),
    })


@bp.route('/reports/purchases', methods=['GET'])
def get_purchases_report():
    try:
        from_date, to_date, warehouse_id = _report_filters()
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    query = (
        VendorBill.query
        .join(GoodsReceipt, GoodsReceipt.id == VendorBill.goods_receipt_id)
        .join(PurchaseOrder, PurchaseOrder.id == GoodsReceipt.purchase_order_id)
    )
    query = _apply_date_filters(query, VendorBill.created_at, from_date, to_date)
    try:
        supplier_id = _optional_positive_int('supplier_id')
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    if warehouse_id is not None:
        query = query.filter(PurchaseOrder.warehouse_id == warehouse_id)
    if supplier_id is not None:
        query = query.filter(VendorBill.supplier_id == supplier_id)
    status = request.args.get('status')
    if status:
        query = query.filter(VendorBill.status == status.upper())
    total_purchase_amount = query.with_entities(
        db.func.coalesce(db.func.sum(VendorBill.total_amount), 0)
    ).scalar()
    pagination = _paginate(query.options(
        joinedload(VendorBill.supplier),
        joinedload(VendorBill.goods_receipt).joinedload(GoodsReceipt.purchase_order).joinedload(PurchaseOrder.warehouse),
        selectinload(VendorBill.allocations).joinedload(SupplierPaymentAllocation.payment),
    ).order_by(VendorBill.created_at.desc(), VendorBill.id.desc()))
    data = []
    for bill in pagination.items:
        purchase_order = bill.goods_receipt.purchase_order
        data.append({
            **bill.to_dict(),
            'supplier_name': bill.supplier.name,
            'warehouse_name': purchase_order.warehouse.name,
        })
    return jsonify({
        'data': data,
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
        'period': {
            'from_date': from_date.isoformat() if from_date else None,
            'to_date': to_date.isoformat() if to_date else None,
        },
        'total_purchase_amount': money_json(total_purchase_amount),
    })


@bp.route('/reports/inventory', methods=['GET'])
def get_inventory_report():
    try:
        _, _, warehouse_id = _report_filters()
        product_id = _optional_positive_int('product_id')
        category_id = _optional_positive_int('category_id')
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    query = db.session.query(
        Product.id.label('product_id'),
        Product.sku,
        Product.name,
        db.func.sum(InventoryBalance.quantity_on_hand).label('quantity_on_hand'),
        db.func.sum(InventoryBalance.quantity_reserved).label('quantity_reserved'),
        db.func.sum(
            InventoryBalance.quantity_on_hand * InventoryBalance.average_cost
        ).label('inventory_value'),
        db.func.sum(InventoryBalance.quantity_on_hand).label('valuation_quantity'),
        db.func.count(
            db.func.distinct(InventoryBalance.warehouse_id)
        ).label('warehouse_count'),
    ).join(InventoryBalance, InventoryBalance.product_id == Product.id)
    if warehouse_id is not None:
        query = query.filter(InventoryBalance.warehouse_id == warehouse_id)
    if product_id is not None:
        query = query.filter(Product.id == product_id)
    if category_id is not None:
        query = query.filter(Product.category_id == category_id)
    query = query.group_by(Product.id, Product.sku, Product.name)
    total_value_query = db.session.query(
        db.func.coalesce(db.func.sum(
            InventoryBalance.quantity_on_hand * InventoryBalance.average_cost
        ), 0)
    ).select_from(InventoryBalance)
    if warehouse_id is not None:
        total_value_query = total_value_query.filter(
            InventoryBalance.warehouse_id == warehouse_id
        )
    if product_id is not None:
        total_value_query = total_value_query.filter(
            InventoryBalance.product_id == product_id
        )
    if category_id is not None:
        total_value_query = total_value_query.join(Product).filter(
            Product.category_id == category_id
        )
    total_inventory_value = decimal_value(total_value_query.scalar() or 0)
    pagination = _paginate(query.order_by(Product.sku))
    data = []
    for row in pagination.items:
        on_hand = float(row.quantity_on_hand or 0)
        reserved = float(row.quantity_reserved or 0)
        value = decimal_value(row.inventory_value or 0)
        quantity = decimal_value(row.quantity_on_hand or 0)
        data.append({
            'product_id': row.product_id,
            'sku': row.sku,
            'name': row.name,
            'quantity_on_hand': on_hand,
            'quantity_reserved': reserved,
            'quantity_available': on_hand - reserved,
            'average_cost': cost_json(value / quantity) if quantity else 0,
            'inventory_value': money_json(value),
            'warehouse_count': row.warehouse_count,
        })
    return jsonify({
        'data': data,
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
        'warehouse_id': warehouse_id,
        'total_inventory_value': money_json(total_inventory_value),
    })


@bp.route('/reports/stock-movements', methods=['GET'])
def get_stock_movement_report():
    try:
        from_date, to_date, warehouse_id = _report_filters()
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    query = StockMovement.query.options(
        joinedload(StockMovement.product),
        joinedload(StockMovement.warehouse),
    )
    query = _apply_date_filters(query, StockMovement.created_at, from_date, to_date)
    try:
        product_id = _optional_positive_int('product_id')
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    if warehouse_id is not None:
        query = query.filter_by(warehouse_id=warehouse_id)
    if product_id is not None:
        query = query.filter_by(product_id=product_id)
    category_id = request.args.get('category_id', type=int)
    if category_id is not None:
        query = query.join(Product).filter(Product.category_id == category_id)
    movement_type = request.args.get('movement_type')
    if movement_type:
        query = query.filter(StockMovement.movement_type == movement_type.upper())
    pagination = _paginate(query.order_by(
        StockMovement.created_at.desc(),
        StockMovement.id.desc()
    ))
    data = [{
        'id': movement.id,
        'product_id': movement.product_id,
        'sku': movement.product.sku,
        'product_name': movement.product.name,
        'warehouse_id': movement.warehouse_id,
        'warehouse_name': movement.warehouse.name,
        'movement_type': movement.movement_type,
        'quantity_delta': movement.quantity_delta,
        'unit_cost': cost_json(movement.unit_cost),
        'reference_type': movement.reference_type,
        'reference_id': movement.reference_id,
        'created_at': movement.created_at.isoformat() if movement.created_at else None,
    } for movement in pagination.items]
    return jsonify({
        'data': data,
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
        'period': {
            'from_date': from_date.isoformat() if from_date else None,
            'to_date': to_date.isoformat() if to_date else None,
        },
    })


@bp.route('/reports/receivables', methods=['GET'])
def get_receivables_report():
    return get_receivables_response()


@bp.route('/reports/payables', methods=['GET'])
def get_payables_report():
    return get_payables_response()
