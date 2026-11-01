# app/routes/statistics.py
# Statistics & Dashboard Endpoints
from datetime import date, datetime, time

from flask import Blueprint, current_app, request, jsonify
from app import db
from app.authorization import has_permission
from app.money import decimal_value, money_json
from app.models import (
    Category,
    Customer,
    CustomerPaymentAllocation,
    GoodsReceipt,
    InventoryAdjuster,
    InventoryBalance,
    Invoice,
    Payment,
    Product,
    PurchaseOrder,
    SalesOrder,
    SalesOrderItem,
    Shipment,
    StockMovement,
    SupplierPayment,
    SupplierPaymentAllocation,
    Unit,
    VendorBill,
    Warehouse,
)


bp = Blueprint('statistics', __name__)


@bp.route('/statistics', methods=['GET'])
def get_statistics():
    """Statistik keseluruhan sistem DistribuFlow ERP"""
    try:
        warehouse_id = request.args.get('warehouse_id', type=int)
        # Total products
        total_products = Product.query.count()

        # Total warehouses
        total_warehouses = Warehouse.query.count()

        # Total customers
        total_customers = Customer.query.count()

        # Total sales orders
        sales_orders_query = SalesOrder.query
        if warehouse_id is not None:
            sales_orders_query = sales_orders_query.filter_by(warehouse_id=warehouse_id)
        total_sales_orders = sales_orders_query.count()

        # Total inventory balances
        inventory_query = InventoryBalance.query
        if warehouse_id is not None:
            inventory_query = inventory_query.filter_by(warehouse_id=warehouse_id)
        total_inventory_balances = inventory_query.count()

        # Total stock movements
        movement_query = StockMovement.query
        if warehouse_id is not None:
            movement_query = movement_query.filter_by(warehouse_id=warehouse_id)
        total_stock_movements = movement_query.count()

        # Total inventory adjusters
        adjuster_query = InventoryAdjuster.query
        if warehouse_id is not None:
            adjuster_query = adjuster_query.filter_by(warehouse_id=warehouse_id)
        total_adjusters = adjuster_query.count()

        # Total purchase orders
        purchase_order_query = PurchaseOrder.query
        if warehouse_id is not None:
            purchase_order_query = purchase_order_query.filter_by(warehouse_id=warehouse_id)
        total_purchase_orders = purchase_order_query.count()

        inventory_value_query = db.session.query(
            db.func.sum(
                InventoryBalance.average_cost * InventoryBalance.quantity_on_hand
            )
        )
        if warehouse_id is not None:
            inventory_value_query = inventory_value_query.filter(
                InventoryBalance.warehouse_id == warehouse_id
            )
        inventory_value_result = inventory_value_query.scalar()

        total_inventory_value = money_json(inventory_value_result)

        # Low stock count
        low_stock_query = db.session.query(Product).join(
            InventoryBalance, Product.id == InventoryBalance.product_id
        ).filter(
            InventoryBalance.quantity_on_hand < Product.min_stock
        )
        if warehouse_id is not None:
            low_stock_query = low_stock_query.filter(
                InventoryBalance.warehouse_id == warehouse_id
            )
        low_stock_count = low_stock_query.count()

        # Recent activity (last 5 sales orders)
        recent_sales_query = SalesOrder.query
        if warehouse_id is not None:
            recent_sales_query = recent_sales_query.filter_by(warehouse_id=warehouse_id)
        recent_sales = recent_sales_query.order_by(
            SalesOrder.created_at.desc()
        ).limit(5).all()

        recent_sales_data = []
        can_view_financial_metrics = has_permission(
            request.current_user,
            'finance.read'
        )
        for so in recent_sales:
            recent_sales_data.append({
                'id': so.id,
                'code': so.code,
                'status': so.status,
                'total_amount': (
                    money_json(so.total_amount)
                    if can_view_financial_metrics else None
                ),
                'created_at': so.created_at.isoformat() if so.created_at else None,
            })

        statistics_data = {
            'total_products': total_products,
            'total_warehouses': total_warehouses,
            'total_customers': total_customers,
            'total_sales_orders': total_sales_orders,
            'total_inventory_balances': total_inventory_balances,
            'total_stock_movements': total_stock_movements,
            'total_inventory_adjusters': total_adjusters,
            'total_purchase_orders': total_purchase_orders,
            'total_inventory_value': (
                total_inventory_value if can_view_financial_metrics else None
            ),
            'low_stock_count': low_stock_count,
            'recent_sales': recent_sales_data,
        }

        return jsonify({
            'data': statistics_data,
            'message': 'System statistics retrieved successfully'
        }), 200

    except Exception:
        db.session.rollback()
        current_app.logger.exception('Statistics query failed')
        return jsonify({'error': 'Unable to retrieve statistics'}), 500


@bp.route('/dashboard', methods=['GET'])
def get_dashboard():
    """Dashboard utama - data komprehensif untuk UI"""
    try:
        warehouse_id = request.args.get('warehouse_id', type=int)
        # Sales data per warehouse
        sales_query = db.session.query(
            Warehouse.name.label('warehouse_name'),
            Warehouse.code.label('warehouse_code'),
            db.func.count(SalesOrder.id).label('total_orders'),
            db.func.sum(SalesOrder.total_amount).label('total_sales_amount')
        ).join(SalesOrder, SalesOrder.warehouse_id == Warehouse.id)\
         .group_by(Warehouse.id)
        if warehouse_id is not None:
            sales_query = sales_query.filter(SalesOrder.warehouse_id == warehouse_id)
        sales_per_warehouse = sales_query.all()

        sales_by_warehouse = []
        for row in sales_per_warehouse:
            sales_by_warehouse.append({
                'warehouse_name': row.warehouse_name,
                'warehouse_code': row.warehouse_code,
                'total_orders': row.total_orders,
                'total_sales_amount': money_json(row.total_sales_amount),
            })

        # Inventory summary per warehouse
        inventory_query = db.session.query(
            Warehouse.name.label('warehouse_name'),
            Warehouse.code.label('warehouse_code'),
            db.func.count(InventoryBalance.id).label('total_balances'),
            db.func.sum(InventoryBalance.quantity_on_hand).label('total_on_hand'),
            db.func.sum(InventoryBalance.quantity_reserved).label('total_reserved'),
        ).join(InventoryBalance, InventoryBalance.warehouse_id == Warehouse.id)\
         .group_by(Warehouse.id)
        if warehouse_id is not None:
            inventory_query = inventory_query.filter(
                InventoryBalance.warehouse_id == warehouse_id
            )
        inventory_per_warehouse = inventory_query.all()

        inventory_by_warehouse = []
        for row in inventory_per_warehouse:
            inventory_by_warehouse.append({
                'warehouse_name': row.warehouse_name,
                'warehouse_code': row.warehouse_code,
                'total_balances': row.total_balances,
                'total_on_hand': float(row.total_on_hand) if row.total_on_hand else 0.0,
                'total_reserved': float(row.total_reserved) if row.total_reserved else 0.0,
            })

        # Stock value per warehouse
        stock_value_query = db.session.query(
            Warehouse.name.label('warehouse_name'),
            Warehouse.code.label('warehouse_code'),
            db.func.sum(
                InventoryBalance.average_cost * InventoryBalance.quantity_on_hand
            ).label('total_value')
        ).join(InventoryBalance, InventoryBalance.warehouse_id == Warehouse.id)\
         .group_by(Warehouse.id)
        if warehouse_id is not None:
            stock_value_query = stock_value_query.filter(
                InventoryBalance.warehouse_id == warehouse_id
            )
        stock_value_per_warehouse = stock_value_query.all()

        stock_value_list = []
        for row in stock_value_per_warehouse:
            stock_value_list.append({
                'warehouse_name': row.warehouse_name,
                'warehouse_code': row.warehouse_code,
                'total_value': money_json(row.total_value),
            })

        # Low stock products
        low_stock_query = db.session.query(
            Product.id,
            Product.sku,
            Product.name,
            Product.min_stock,
            InventoryBalance.quantity_on_hand,
            Category.name.label('category_name')
        ).join(InventoryBalance, Product.id == InventoryBalance.product_id)\
         .join(Category, Product.category_id == Category.id)\
         .filter(InventoryBalance.quantity_on_hand < Product.min_stock)
        if warehouse_id is not None:
            low_stock_query = low_stock_query.filter(
                InventoryBalance.warehouse_id == warehouse_id
            )
        low_stock_products = low_stock_query.limit(10).all()

        low_stock_list = []
        for row in low_stock_products:
            low_stock_list.append({
                'product_id': row.id,
                'sku': row.sku,
                'name': row.name,
                'category': row.category_name,
                'min_stock': row.min_stock,
                'quantity_on_hand': row.quantity_on_hand,
                'stock_deficit': row.min_stock - row.quantity_on_hand,
            })

        dashboard_data = {
            'sales_by_warehouse': sales_by_warehouse,
            'inventory_by_warehouse': inventory_by_warehouse,
            'stock_value_by_warehouse': stock_value_list,
            'low_stock_products': low_stock_list,
            'total_metrics': {
                'total_products': Product.query.count(),
                'total_warehouses': Warehouse.query.count(),
                'total_customers': Customer.query.count(),
            }
        }

        return jsonify({
            'data': dashboard_data,
            'message': 'Dashboard data retrieved successfully'
        }), 200

    except Exception:
        db.session.rollback()
        current_app.logger.exception('Dashboard query failed')
        return jsonify({'error': 'Unable to retrieve dashboard data'}), 500


@bp.route('/dashboard/summary', methods=['GET'])
def get_dashboard_summary():
    try:
        from_value = request.args.get('from_date')
        to_value = request.args.get('to_date')
        from_date = date.fromisoformat(from_value) if from_value else date.today().replace(day=1)
        to_date = date.fromisoformat(to_value) if to_value else date.today()
        if from_date > to_date:
            raise ValueError('from_date cannot be later than to_date')
        raw_warehouse_id = request.args.get('warehouse_id')
        warehouse_id = int(raw_warehouse_id) if raw_warehouse_id is not None else None
        if warehouse_id is not None and warehouse_id <= 0:
            raise ValueError('warehouse_id must be a positive integer')
    except ValueError:
        return jsonify({
            'error': 'Invalid date or warehouse filter'
        }), 400

    start = datetime.combine(from_date, time.min)
    end = datetime.combine(to_date, time.max)

    sales_query = db.session.query(
        db.func.coalesce(db.func.sum(Invoice.total_amount), 0)
    ).join(Shipment, Shipment.id == Invoice.shipment_id)\
     .join(SalesOrder, SalesOrder.id == Shipment.sales_order_id)\
     .filter(Invoice.created_at >= start, Invoice.created_at <= end)
    if warehouse_id is not None:
        sales_query = sales_query.filter(SalesOrder.warehouse_id == warehouse_id)
    total_sales = decimal_value(sales_query.scalar() or 0)

    purchases_query = db.session.query(
        db.func.coalesce(db.func.sum(VendorBill.total_amount), 0)
    ).join(GoodsReceipt, GoodsReceipt.id == VendorBill.goods_receipt_id)\
     .join(PurchaseOrder, PurchaseOrder.id == GoodsReceipt.purchase_order_id)\
     .filter(VendorBill.created_at >= start, VendorBill.created_at <= end)
    if warehouse_id is not None:
        purchases_query = purchases_query.filter(
            PurchaseOrder.warehouse_id == warehouse_id
        )
    total_purchases = decimal_value(purchases_query.scalar() or 0)

    inventory_value_query = db.session.query(
        db.func.coalesce(db.func.sum(
            InventoryBalance.quantity_on_hand * InventoryBalance.average_cost
        ), 0)
    )
    low_stock_query = db.session.query(InventoryBalance.id).join(
        Product,
        Product.id == InventoryBalance.product_id
    ).filter(InventoryBalance.quantity_on_hand < Product.min_stock)
    if warehouse_id is not None:
        inventory_value_query = inventory_value_query.filter(
            InventoryBalance.warehouse_id == warehouse_id
        )
        low_stock_query = low_stock_query.filter(
            InventoryBalance.warehouse_id == warehouse_id
        )
    inventory_value = decimal_value(inventory_value_query.scalar() or 0)
    low_stock_count = low_stock_query.count()

    posted_customer_allocations = db.session.query(
        CustomerPaymentAllocation.invoice_id.label('document_id'),
        db.func.sum(CustomerPaymentAllocation.amount).label('amount_paid')
    ).join(Payment, Payment.id == CustomerPaymentAllocation.payment_id)\
     .filter(Payment.status == 'POSTED')\
     .group_by(CustomerPaymentAllocation.invoice_id)\
     .subquery()
    receivable_balance = (
        Invoice.total_amount
        - db.func.coalesce(posted_customer_allocations.c.amount_paid, 0)
    )
    receivables_query = db.session.query(
        db.func.coalesce(db.func.sum(receivable_balance), 0)
    ).join(Shipment, Shipment.id == Invoice.shipment_id)\
     .join(SalesOrder, SalesOrder.id == Shipment.sales_order_id)\
     .outerjoin(
         posted_customer_allocations,
         posted_customer_allocations.c.document_id == Invoice.id
     ).filter(receivable_balance > 0.005)
    if warehouse_id is not None:
        receivables_query = receivables_query.filter(
            SalesOrder.warehouse_id == warehouse_id
        )
    total_receivables = decimal_value(receivables_query.scalar() or 0)

    posted_supplier_allocations = db.session.query(
        SupplierPaymentAllocation.vendor_bill_id.label('document_id'),
        db.func.sum(SupplierPaymentAllocation.amount).label('amount_paid')
    ).join(
        SupplierPayment,
        SupplierPayment.id == SupplierPaymentAllocation.payment_id
    ).filter(SupplierPayment.status == 'POSTED')\
     .group_by(SupplierPaymentAllocation.vendor_bill_id)\
     .subquery()
    payable_balance = (
        VendorBill.total_amount
        - db.func.coalesce(posted_supplier_allocations.c.amount_paid, 0)
    )
    payables_query = db.session.query(
        db.func.coalesce(db.func.sum(payable_balance), 0)
    ).join(
        GoodsReceipt,
        GoodsReceipt.id == VendorBill.goods_receipt_id
    ).join(
        PurchaseOrder,
        PurchaseOrder.id == GoodsReceipt.purchase_order_id
    ).outerjoin(
        posted_supplier_allocations,
        posted_supplier_allocations.c.document_id == VendorBill.id
    ).filter(payable_balance > 0.005)
    if warehouse_id is not None:
        payables_query = payables_query.filter(
            PurchaseOrder.warehouse_id == warehouse_id
        )
    total_payables = decimal_value(payables_query.scalar() or 0)

    cash_in_query = db.session.query(
        db.func.coalesce(db.func.sum(Payment.amount), 0)
    ).filter(
        Payment.status == 'POSTED',
        Payment.payment_date >= start,
        Payment.payment_date <= end
    )
    cash_out_query = db.session.query(
        db.func.coalesce(db.func.sum(SupplierPayment.amount), 0)
    ).filter(
        SupplierPayment.status == 'POSTED',
        SupplierPayment.payment_date >= start,
        SupplierPayment.payment_date <= end
    )
    if warehouse_id is not None:
        scoped_customer_allocations = db.session.query(
            CustomerPaymentAllocation.payment_id.label('payment_id'),
            db.func.sum(CustomerPaymentAllocation.amount).label('amount')
        ).join(Invoice, Invoice.id == CustomerPaymentAllocation.invoice_id).join(
            Shipment, Shipment.id == Invoice.shipment_id
        ).join(SalesOrder, SalesOrder.id == Shipment.sales_order_id).filter(
            SalesOrder.warehouse_id == warehouse_id
        ).group_by(CustomerPaymentAllocation.payment_id).subquery()
        legacy_customer_payments = db.session.query(
            db.func.coalesce(db.func.sum(Payment.amount), 0)
        ).join(Invoice, Invoice.id == Payment.invoice_id).join(
            Shipment, Shipment.id == Invoice.shipment_id
        ).join(SalesOrder, SalesOrder.id == Shipment.sales_order_id).filter(
            SalesOrder.warehouse_id == warehouse_id,
            ~db.session.query(CustomerPaymentAllocation.id).filter(
                CustomerPaymentAllocation.payment_id == Payment.id
            ).exists(),
            Payment.status == 'POSTED', Payment.payment_date >= start,
            Payment.payment_date <= end
        )
        scoped_supplier_allocations = db.session.query(
            SupplierPaymentAllocation.payment_id.label('payment_id'),
            db.func.sum(SupplierPaymentAllocation.amount).label('amount')
        ).join(VendorBill, VendorBill.id == SupplierPaymentAllocation.vendor_bill_id).join(
            GoodsReceipt, GoodsReceipt.id == VendorBill.goods_receipt_id
        ).join(PurchaseOrder, PurchaseOrder.id == GoodsReceipt.purchase_order_id).filter(
            PurchaseOrder.warehouse_id == warehouse_id
        ).group_by(SupplierPaymentAllocation.payment_id).subquery()
        cash_in_query = db.session.query(db.func.coalesce(
            db.func.sum(scoped_customer_allocations.c.amount), 0
        )).join(Payment, Payment.id == scoped_customer_allocations.c.payment_id).filter(
            Payment.status == 'POSTED', Payment.payment_date >= start,
            Payment.payment_date <= end
        )
        cash_out_query = db.session.query(db.func.coalesce(
            db.func.sum(scoped_supplier_allocations.c.amount), 0
        )).join(SupplierPayment, SupplierPayment.id == scoped_supplier_allocations.c.payment_id).filter(
            SupplierPayment.status == 'POSTED', SupplierPayment.payment_date >= start,
            SupplierPayment.payment_date <= end
        )
        cash_in = decimal_value(cash_in_query.scalar() or 0) + decimal_value(legacy_customer_payments.scalar() or 0)
    else:
        cash_in = decimal_value(cash_in_query.scalar() or 0)
        cash_out = decimal_value(cash_out_query.scalar() or 0)
    if warehouse_id is not None:
        cash_out = decimal_value(cash_out_query.scalar() or 0)

    distribution_query = db.session.query(
        Warehouse.id,
        Warehouse.name,
        Warehouse.code,
        db.func.coalesce(db.func.sum(
            InventoryBalance.quantity_on_hand
        ), 0).label('quantity_on_hand'),
        db.func.coalesce(db.func.sum(
            InventoryBalance.quantity_reserved
        ), 0).label('quantity_reserved'),
        db.func.coalesce(db.func.sum(
            InventoryBalance.quantity_on_hand * InventoryBalance.average_cost
        ), 0).label('inventory_value')
    ).outerjoin(
        InventoryBalance,
        InventoryBalance.warehouse_id == Warehouse.id
    ).group_by(Warehouse.id, Warehouse.name, Warehouse.code)
    if warehouse_id is not None:
        distribution_query = distribution_query.filter(Warehouse.id == warehouse_id)
    stock_distribution = [{
        'warehouse_id': row.id,
        'warehouse_name': row.name,
        'warehouse_code': row.code,
        'quantity_on_hand': float(row.quantity_on_hand),
        'quantity_reserved': float(row.quantity_reserved),
        'quantity_available': float(row.quantity_on_hand - row.quantity_reserved),
        'inventory_value': money_json(row.inventory_value),
    } for row in distribution_query.all()]

    return jsonify({
        'data': {
            'period': {
                'from_date': from_date.isoformat(),
                'to_date': to_date.isoformat(),
            },
            'warehouse_id': warehouse_id,
            'total_sales_amount': money_json(total_sales),
            'total_purchase_amount': money_json(total_purchases),
            'inventory_value': money_json(inventory_value),
            'low_stock_balance_count': low_stock_count,
            'receivables_outstanding': money_json(total_receivables),
            'payables_outstanding': money_json(total_payables),
            'cash_incoming': money_json(cash_in),
            'cash_outgoing': money_json(cash_out),
            'cash_net': money_json(cash_in - cash_out),
            'cash_scope': 'warehouse-attributed' if warehouse_id is not None else 'company-wide',
            'stock_distribution': stock_distribution,
        }
    })
