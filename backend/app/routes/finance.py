from datetime import date, datetime, time

from flask import Blueprint, jsonify, request
from sqlalchemy import or_
from sqlalchemy.orm import joinedload, selectinload

from app import db
from app.money import decimal_value, money_json
from app.models import (
    CustomerPaymentAllocation,
    GoodsReceipt,
    Invoice,
    Payment,
    Product,
    PurchaseOrder,
    SalesOrder,
    Shipment,
    SupplierPayment,
    SupplierPaymentAllocation,
    ShipmentItem,
    VendorBill,
)


bp = Blueprint('finance', __name__)


def _date_filter(name):
    raw_value = request.args.get(name)
    if raw_value is None:
        return None
    try:
        return date.fromisoformat(raw_value)
    except ValueError:
        raise ValueError(f'{name} must use YYYY-MM-DD format') from None


def _positive_int_filter(name):
    raw_value = request.args.get(name)
    if raw_value is None:
        return None
    try:
        value = int(raw_value)
    except ValueError:
        raise ValueError(f'{name} must be an integer') from None
    if value <= 0:
        raise ValueError(f'{name} must be a positive integer')
    return value


def _pagination():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    return max(page, 1), min(max(per_page, 1), 100)


def _payment_allocation_totals(allocation_model, payment_model, foreign_key):
    return (
        db.session.query(
            getattr(allocation_model, foreign_key).label('document_id'),
            db.func.sum(allocation_model.amount).label('amount_paid')
        )
        .join(payment_model, payment_model.id == allocation_model.payment_id)
        .filter(payment_model.status == 'POSTED')
        .group_by(getattr(allocation_model, foreign_key))
        .subquery()
    )


@bp.route('/finance/receivables', methods=['GET'])
def get_receivables():
    return get_receivables_response()


def get_receivables_response():
    try:
        warehouse_id = _positive_int_filter('warehouse_id')
        customer_id = _positive_int_filter('customer_id')
        from_date = _date_filter('from_date')
        to_date = _date_filter('to_date')
        as_of_date = _date_filter('as_of') or date.today()
        if from_date and to_date and from_date > to_date:
            raise ValueError('from_date cannot be later than to_date')
        page, per_page = _pagination()
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    paid_totals = _payment_allocation_totals(
        CustomerPaymentAllocation,
        Payment,
        'invoice_id'
    )
    balance = Invoice.total_amount - db.func.coalesce(paid_totals.c.amount_paid, 0)
    query = (
        db.session.query(Invoice, balance.label('balance_due'))
        .join(Shipment, Shipment.id == Invoice.shipment_id)
        .join(SalesOrder, SalesOrder.id == Shipment.sales_order_id)
        .outerjoin(paid_totals, paid_totals.c.document_id == Invoice.id)
        .filter(balance > 0.005)
        .options(
            joinedload(Invoice.shipment).joinedload(Shipment.sales_order).joinedload(SalesOrder.customer),
            joinedload(Invoice.shipment).joinedload(Shipment.sales_order).joinedload(SalesOrder.warehouse),
            joinedload(Invoice.shipment).selectinload(Shipment.items).joinedload(ShipmentItem.product).joinedload(Product.unit),
            selectinload(Invoice.allocations).joinedload(CustomerPaymentAllocation.payment),
        )
    )
    if warehouse_id is not None:
        query = query.filter(SalesOrder.warehouse_id == warehouse_id)
    if customer_id is not None:
        query = query.filter(SalesOrder.customer_id == customer_id)
    if from_date is not None:
        query = query.filter(Invoice.created_at >= datetime.combine(from_date, time.min))
    if to_date is not None:
        query = query.filter(Invoice.created_at <= datetime.combine(to_date, time.max))
    status = request.args.get('status')
    if status:
        query = query.filter(Invoice.status == status.upper())

    summary_query = db.session.query(
        db.func.count(Invoice.id),
        db.func.coalesce(db.func.sum(balance), 0),
        db.func.coalesce(db.func.sum(
            db.case((Invoice.due_date < as_of_date, balance), else_=0)
        ), 0)
    ).select_from(Invoice)\
     .join(Shipment, Shipment.id == Invoice.shipment_id)\
     .join(SalesOrder, SalesOrder.id == Shipment.sales_order_id)\
     .outerjoin(paid_totals, paid_totals.c.document_id == Invoice.id)\
     .filter(balance > 0.005)
    if warehouse_id is not None:
        summary_query = summary_query.filter(SalesOrder.warehouse_id == warehouse_id)
    if customer_id is not None:
        summary_query = summary_query.filter(SalesOrder.customer_id == customer_id)
    if from_date is not None:
        summary_query = summary_query.filter(Invoice.created_at >= datetime.combine(from_date, time.min))
    if to_date is not None:
        summary_query = summary_query.filter(Invoice.created_at <= datetime.combine(to_date, time.max))
    if status:
        summary_query = summary_query.filter(Invoice.status == status.upper())
    count, total_outstanding, overdue_amount = summary_query.one()

    rows = query.order_by(Invoice.due_date, Invoice.id)\
        .offset((page - 1) * per_page)\
        .limit(per_page)\
        .all()
    data = []
    for invoice, balance_due in rows:
        order = invoice.shipment.sales_order
        data.append({
            **invoice.to_dict(),
            'balance_due': money_json(balance_due),
            'customer_name': order.customer.name,
            'warehouse_id': order.warehouse_id,
            'warehouse_name': order.warehouse.name,
            'overdue_days': max((as_of_date - invoice.due_date).days, 0),
        })
    return jsonify({
        'data': data,
        'total': count,
        'page': page,
        'pages': (count + per_page - 1) // per_page,
        'as_of_date': as_of_date.isoformat(),
        'summary': {
            'outstanding_amount': money_json(total_outstanding),
            'overdue_amount': money_json(overdue_amount),
        }
    })


@bp.route('/finance/payables', methods=['GET'])
def get_payables():
    return get_payables_response()


def get_payables_response():
    try:
        warehouse_id = _positive_int_filter('warehouse_id')
        supplier_id = _positive_int_filter('supplier_id')
        from_date = _date_filter('from_date')
        to_date = _date_filter('to_date')
        if from_date and to_date and from_date > to_date:
            raise ValueError('from_date cannot be later than to_date')
        page, per_page = _pagination()
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    paid_totals = _payment_allocation_totals(
        SupplierPaymentAllocation,
        SupplierPayment,
        'vendor_bill_id'
    )
    balance = VendorBill.total_amount - db.func.coalesce(paid_totals.c.amount_paid, 0)
    query = (
        db.session.query(VendorBill, balance.label('balance_due'))
        .join(GoodsReceipt, GoodsReceipt.id == VendorBill.goods_receipt_id)
        .join(PurchaseOrder, PurchaseOrder.id == GoodsReceipt.purchase_order_id)
        .outerjoin(paid_totals, paid_totals.c.document_id == VendorBill.id)
        .filter(balance > 0.005)
        .options(
            joinedload(VendorBill.supplier),
            joinedload(VendorBill.goods_receipt).joinedload(GoodsReceipt.purchase_order).joinedload(PurchaseOrder.warehouse),
            selectinload(VendorBill.allocations).joinedload(SupplierPaymentAllocation.payment),
        )
    )
    if warehouse_id is not None:
        query = query.filter(PurchaseOrder.warehouse_id == warehouse_id)
    if supplier_id is not None:
        query = query.filter(VendorBill.supplier_id == supplier_id)
    if from_date is not None:
        query = query.filter(VendorBill.created_at >= datetime.combine(from_date, time.min))
    if to_date is not None:
        query = query.filter(VendorBill.created_at <= datetime.combine(to_date, time.max))
    status = request.args.get('status')
    if status:
        query = query.filter(VendorBill.status == status.upper())

    summary_query = db.session.query(
        db.func.count(VendorBill.id),
        db.func.coalesce(db.func.sum(balance), 0)
    ).select_from(VendorBill)\
     .join(GoodsReceipt, GoodsReceipt.id == VendorBill.goods_receipt_id)\
     .join(PurchaseOrder, PurchaseOrder.id == GoodsReceipt.purchase_order_id)\
     .outerjoin(paid_totals, paid_totals.c.document_id == VendorBill.id)\
     .filter(balance > 0.005)
    if warehouse_id is not None:
        summary_query = summary_query.filter(PurchaseOrder.warehouse_id == warehouse_id)
    if supplier_id is not None:
        summary_query = summary_query.filter(VendorBill.supplier_id == supplier_id)
    if from_date is not None:
        summary_query = summary_query.filter(VendorBill.created_at >= datetime.combine(from_date, time.min))
    if to_date is not None:
        summary_query = summary_query.filter(VendorBill.created_at <= datetime.combine(to_date, time.max))
    if status:
        summary_query = summary_query.filter(VendorBill.status == status.upper())
    count, total_outstanding = summary_query.one()

    rows = query.order_by(VendorBill.created_at, VendorBill.id)\
        .offset((page - 1) * per_page)\
        .limit(per_page)\
        .all()
    data = []
    for bill, balance_due in rows:
        purchase_order = bill.goods_receipt.purchase_order
        data.append({
            **bill.to_dict(),
            'balance_due': money_json(balance_due),
            'supplier_name': bill.supplier.name,
            'warehouse_id': purchase_order.warehouse_id,
            'warehouse_name': purchase_order.warehouse.name,
        })
    return jsonify({
        'data': data,
        'total': count,
        'page': page,
        'pages': (count + per_page - 1) // per_page,
        'summary': {
            'outstanding_amount': money_json(total_outstanding),
        }
    })


@bp.route('/finance/cash-summary', methods=['GET'])
def get_cash_summary():
    try:
        warehouse_id = _positive_int_filter('warehouse_id')
        from_date = _date_filter('from_date')
        to_date = _date_filter('to_date')
        if from_date and to_date and from_date > to_date:
            raise ValueError('from_date cannot be later than to_date')
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    incoming_query = db.session.query(
        db.func.count(Payment.id),
        db.func.coalesce(db.func.sum(Payment.amount), 0)
    ).filter(Payment.status == 'POSTED')
    outgoing_query = db.session.query(
        db.func.count(SupplierPayment.id),
        db.func.coalesce(db.func.sum(SupplierPayment.amount), 0)
    ).filter(SupplierPayment.status == 'POSTED')
    if warehouse_id is not None:
        customer_scoped = db.session.query(
            CustomerPaymentAllocation.payment_id.label('payment_id'),
            db.func.sum(CustomerPaymentAllocation.amount).label('amount')
        ).join(Invoice, Invoice.id == CustomerPaymentAllocation.invoice_id).join(
            Shipment, Shipment.id == Invoice.shipment_id
        ).join(SalesOrder, SalesOrder.id == Shipment.sales_order_id).filter(
            SalesOrder.warehouse_id == warehouse_id
        ).group_by(CustomerPaymentAllocation.payment_id).subquery()
        customer_count_query = db.session.query(db.func.count(db.distinct(
            customer_scoped.c.payment_id
        ))).join(Payment, Payment.id == customer_scoped.c.payment_id).filter(
            Payment.status == 'POSTED'
        )
        incoming_amount_query = db.session.query(db.func.coalesce(
            db.func.sum(customer_scoped.c.amount), 0
        )).join(Payment, Payment.id == customer_scoped.c.payment_id).filter(
            Payment.status == 'POSTED'
        )
        customer_invoice_ids = db.session.query(Invoice.id).join(
            Shipment, Shipment.id == Invoice.shipment_id
        ).join(SalesOrder, SalesOrder.id == Shipment.sales_order_id).filter(
            SalesOrder.warehouse_id == warehouse_id
        )
        legacy_customer = db.session.query(
            db.func.count(Payment.id), db.func.coalesce(db.func.sum(Payment.amount), 0)
        ).filter(
            Payment.status == 'POSTED', Payment.invoice_id.in_(customer_invoice_ids),
            ~db.session.query(CustomerPaymentAllocation.id).filter(
                CustomerPaymentAllocation.payment_id == Payment.id
            ).exists()
        )
        supplier_scoped = db.session.query(
            SupplierPaymentAllocation.payment_id.label('payment_id'),
            db.func.sum(SupplierPaymentAllocation.amount).label('amount')
        ).join(VendorBill, VendorBill.id == SupplierPaymentAllocation.vendor_bill_id).join(
            GoodsReceipt, GoodsReceipt.id == VendorBill.goods_receipt_id
        ).join(PurchaseOrder, PurchaseOrder.id == GoodsReceipt.purchase_order_id).filter(
            PurchaseOrder.warehouse_id == warehouse_id
        ).group_by(SupplierPaymentAllocation.payment_id).subquery()
        supplier_count_query = db.session.query(db.func.count(db.distinct(
            supplier_scoped.c.payment_id
        ))).join(SupplierPayment, SupplierPayment.id == supplier_scoped.c.payment_id).filter(
            SupplierPayment.status == 'POSTED'
        )
        outgoing_amount_query = db.session.query(db.func.coalesce(
            db.func.sum(supplier_scoped.c.amount), 0
        )).join(SupplierPayment, SupplierPayment.id == supplier_scoped.c.payment_id).filter(
            SupplierPayment.status == 'POSTED'
        )
        if from_date is not None:
            start = datetime.combine(from_date, time.min)
            customer_count_query = customer_count_query.filter(Payment.payment_date >= start)
            incoming_amount_query = incoming_amount_query.filter(Payment.payment_date >= start)
            legacy_customer = legacy_customer.filter(Payment.payment_date >= start)
            supplier_count_query = supplier_count_query.filter(SupplierPayment.payment_date >= start)
            outgoing_amount_query = outgoing_amount_query.filter(SupplierPayment.payment_date >= start)
        if to_date is not None:
            end = datetime.combine(to_date, time.max)
            customer_count_query = customer_count_query.filter(Payment.payment_date <= end)
            incoming_amount_query = incoming_amount_query.filter(Payment.payment_date <= end)
            legacy_customer = legacy_customer.filter(Payment.payment_date <= end)
            supplier_count_query = supplier_count_query.filter(SupplierPayment.payment_date <= end)
            outgoing_amount_query = outgoing_amount_query.filter(SupplierPayment.payment_date <= end)
        customer_count, customer_amount = legacy_customer.one()
        incoming_count = customer_count_query.scalar() + customer_count
        incoming_amount = decimal_value(incoming_amount_query.scalar() or 0) + decimal_value(customer_amount or 0)
        outgoing_count = supplier_count_query.scalar()
        outgoing_amount = outgoing_amount_query.scalar()
    if warehouse_id is None:
        if from_date is not None:
            start = datetime.combine(from_date, time.min)
            incoming_query = incoming_query.filter(Payment.payment_date >= start)
            outgoing_query = outgoing_query.filter(SupplierPayment.payment_date >= start)
        if to_date is not None:
            end = datetime.combine(to_date, time.max)
            incoming_query = incoming_query.filter(Payment.payment_date <= end)
            outgoing_query = outgoing_query.filter(SupplierPayment.payment_date <= end)
        incoming_count, incoming_amount = incoming_query.one()
        outgoing_count, outgoing_amount = outgoing_query.one()
    incoming_amount = decimal_value(incoming_amount)
    outgoing_amount = decimal_value(outgoing_amount)
    return jsonify({
        'data': {
            'from_date': from_date.isoformat() if from_date else None,
            'to_date': to_date.isoformat() if to_date else None,
            'incoming_amount': money_json(incoming_amount),
            'outgoing_amount': money_json(outgoing_amount),
            'net_amount': money_json(incoming_amount - outgoing_amount),
            'incoming_payment_count': incoming_count,
            'outgoing_payment_count': outgoing_count,
        }
    })
