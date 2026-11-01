from flask import jsonify, request

from app import db
from app.models import (
    AuditLog, GoodsReceipt, InventoryAdjuster, InventoryBalance, Invoice, Payment,
    InventoryQuarantine, InventoryQuarantineAction, Permission, PurchaseOrder,
    Role, RoleDefaultPermission, RolePermissionOverride, SalesOrder, Shipment,
    StockMovement, SalesReturn, StockTransfer,
    SupplierPayment, UserWarehouseAccess, VendorBill, Warehouse
)


PERMISSION_DEFINITIONS = {
    'users.manage': ('Manage users', 'users', 'manage', False),
    'profile.read': ('Read own profile', 'users', 'read', False),
    'roles.manage': ('Manage roles and permissions', 'roles', 'manage', False),
    'master_data.read': ('Read master data', 'master_data', 'read', False),
    'master_data.manage': ('Manage master data', 'master_data', 'manage', False),
    'warehouses.read': ('Read assigned warehouses', 'warehouses', 'read', True),
    'customers.read': ('Read customers', 'customers', 'read', False),
    'customers.manage': ('Manage customers', 'customers', 'manage', False),
    'suppliers.read': ('Read suppliers', 'suppliers', 'read', False),
    'suppliers.manage': ('Manage suppliers', 'suppliers', 'manage', False),
    'inventory.read': ('Read inventory', 'inventory', 'read', True),
    'inventory.adjust.read': ('Read inventory adjustments', 'inventory', 'read', True),
    'inventory.balance.create': ('Create opening balances', 'inventory', 'create', True),
    'inventory.adjust.create': ('Create adjustments', 'inventory', 'create', True),
    'inventory.adjust.approve': ('Review adjustments', 'inventory', 'approve', True),
    'inventory.adjust.post': ('Post adjustments', 'inventory', 'post', True),
    'inventory.transfer.create': ('Create transfers', 'inventory', 'create', True),
    'inventory.transfer.read': ('Read transfers', 'inventory', 'read', True),
    'inventory.transfer.approve': ('Approve transfers', 'inventory', 'approve', True),
    'inventory.transfer.post': ('Post transfers', 'inventory', 'post', True),
    'inventory.quarantine.read': ('Read quarantined stock', 'inventory', 'read', True),
    'inventory.quarantine.action.create': ('Request quarantine disposition', 'inventory', 'create', True),
    'inventory.quarantine.action.approve': ('Approve quarantine disposition', 'inventory', 'approve', True),
    'inventory.quarantine.action.post': ('Post quarantine disposition', 'inventory', 'post', True),
    'purchase_orders.read': ('Read purchase orders', 'purchasing', 'read', True),
    'purchase_orders.create': ('Create purchase orders', 'purchasing', 'create', True),
    'purchase_orders.submit': ('Submit purchase orders', 'purchasing', 'submit', True),
    'purchase_orders.approve': ('Approve purchase orders', 'purchasing', 'approve', True),
    'purchase_orders.cancel': ('Cancel purchase orders', 'purchasing', 'cancel', True),
    'goods_receipts.read': ('Read goods receipts', 'purchasing', 'read', True),
    'goods_receipts.create': ('Create goods receipts', 'purchasing', 'create', True),
    'goods_receipts.post': ('Post goods receipts', 'purchasing', 'post', True),
    'vendor_bills.read': ('Read vendor bills', 'finance', 'read', True),
    'vendor_bills.create': ('Create vendor bills', 'finance', 'create', True),
    'sales_orders.read': ('Read sales orders', 'sales', 'read', True),
    'sales_orders.create': ('Create sales orders', 'sales', 'create', True),
    'sales_orders.submit': ('Submit sales orders', 'sales', 'submit', True),
    'sales_orders.approve': ('Approve sales orders', 'sales', 'approve', True),
    'sales_orders.reserve': ('Reserve sales orders', 'sales', 'reserve', True),
    'sales_orders.cancel': ('Cancel sales orders', 'sales', 'cancel', True),
    'shipments.read': ('Read shipments', 'sales', 'read', True),
    'shipments.create': ('Create shipments', 'sales', 'create', True),
    'shipments.post': ('Post shipments', 'sales', 'post', True),
    'sales_returns.read': ('Read sales returns', 'sales', 'read', True),
    'sales_returns.create': ('Create sales returns', 'sales', 'create', True),
    'sales_returns.post': ('Post sales returns', 'sales', 'post', True),
    'sales_invoices.read': ('Read sales invoices', 'finance', 'read', True),
    'sales_invoices.create': ('Create sales invoices', 'finance', 'create', True),
    'customer_payments.read': ('Read customer payments', 'finance', 'read', True),
    'customer_payments.create': ('Create customer payments', 'finance', 'create', True),
    'customer_payments.post': ('Post customer payments', 'finance', 'post', True),
    'customer_payments.allocate': ('Allocate customer payments', 'finance', 'allocate', True),
    'supplier_payments.read': ('Read supplier payments', 'finance', 'read', True),
    'supplier_payments.create': ('Create supplier payments', 'finance', 'create', True),
    'supplier_payments.post': ('Post supplier payments', 'finance', 'post', True),
    'supplier_payments.allocate': ('Allocate supplier payments', 'finance', 'allocate', True),
    'finance.read': ('Read receivables and payables', 'finance', 'read', True),
    'finance.cash.read': ('Read cash summary', 'finance', 'read', True),
    'dashboard.read': ('Read operational dashboard', 'dashboard', 'read', True),
    'reports.read': ('Read reports and dashboard', 'reports', 'read', True),
    'audit_logs.read': ('Read audit log', 'audit_logs', 'read', False),
    'system.read': ('Read API metadata', 'system', 'read', False),
    'inventory.transfer.submit': ('Submit transfers', 'inventory', 'submit', True),
}


ALL_OPERATIONAL_PERMISSIONS = {
    code for code in PERMISSION_DEFINITIONS
    if code not in {'users.manage', 'roles.manage'}
}

MANAGER_READ_PERMISSIONS = {
    'profile.read', 'master_data.read', 'warehouses.read', 'inventory.read',
    'inventory.adjust.read', 'inventory.transfer.read',
    'inventory.quarantine.read',
    'customers.read', 'suppliers.read', 'dashboard.read',
    'purchase_orders.read', 'goods_receipts.read', 'vendor_bills.read',
    'sales_orders.read', 'shipments.read', 'sales_returns.read',
    'sales_invoices.read', 'customer_payments.read', 'supplier_payments.read',
    'finance.read', 'finance.cash.read', 'reports.read',
}

ROLE_DEFAULTS = {
    'admin': ALL_OPERATIONAL_PERMISSIONS | {'users.manage', 'roles.manage'},
    'operator': {
        'profile.read', 'master_data.read', 'warehouses.read', 'customers.read', 'suppliers.read',
        'dashboard.read', 'inventory.read',
        'purchase_orders.read', 'purchase_orders.create', 'purchase_orders.submit',
        'purchase_orders.cancel', 'goods_receipts.read', 'goods_receipts.create',
        'sales_orders.read', 'sales_orders.create', 'sales_orders.submit',
        'sales_orders.reserve', 'sales_orders.cancel', 'shipments.read',
        'shipments.create', 'sales_returns.read', 'sales_returns.create',
    },
    'viewer': {
        'master_data.read', 'warehouses.read', 'customers.read', 'suppliers.read', 'dashboard.read',
        'inventory.read', 'purchase_orders.read',
        'goods_receipts.read', 'sales_orders.read',
        'shipments.read', 'sales_invoices.read', 'customer_payments.read',
        'supplier_payments.read', 'sales_returns.read',
        'reports.read'
    },
    'purchasing': {
        'purchase_orders.read', 'purchase_orders.create', 'purchase_orders.submit',
        'purchase_orders.cancel', 'goods_receipts.read', 'goods_receipts.create',
        'suppliers.read', 'suppliers.manage', 'master_data.read', 'warehouses.read'
    },
    'warehouse': {
        'dashboard.read',
        'inventory.read', 'inventory.adjust.read', 'inventory.adjust.create',
        'inventory.adjust.approve', 'inventory.adjust.post',
        'inventory.transfer.read', 'inventory.transfer.create',
        'inventory.transfer.submit', 'inventory.transfer.post',
        'inventory.quarantine.read', 'inventory.quarantine.action.create',
        'inventory.quarantine.action.post',
        'goods_receipts.read', 'goods_receipts.create',
        'goods_receipts.post', 'shipments.read', 'shipments.create', 'shipments.post',
        'sales_returns.read', 'sales_returns.post',
        'purchase_orders.read', 'sales_orders.read', 'master_data.read', 'warehouses.read',
        'suppliers.read'
    },
    'sales': {
        'dashboard.read', 'inventory.read', 'customers.read', 'customers.manage',
        'sales_orders.read', 'sales_orders.create', 'sales_orders.submit',
        'sales_orders.reserve', 'sales_orders.cancel', 'shipments.read',
        'sales_returns.read', 'sales_returns.create',
        'sales_invoices.read', 'master_data.read', 'warehouses.read'
    },
    'finance': {
        'dashboard.read', 'reports.read',
        'vendor_bills.read', 'vendor_bills.create',
        'sales_invoices.read', 'sales_invoices.create', 'shipments.read',
        'customer_payments.read', 'customer_payments.create', 'customer_payments.post',
        'customer_payments.allocate', 'supplier_payments.read', 'warehouses.read',
        'supplier_payments.create', 'supplier_payments.post',
        'supplier_payments.allocate', 'finance.read', 'finance.cash.read'
    },
    'manager': MANAGER_READ_PERMISSIONS | {
        'inventory.adjust.approve', 'inventory.transfer.approve',
        'inventory.quarantine.action.approve',
        'purchase_orders.approve', 'sales_orders.approve',
    },
}
ROLE_DEFAULTS['admin'].add('profile.read')
ROLE_DEFAULTS['operator'].add('profile.read')
ROLE_DEFAULTS['viewer'].add('profile.read')
ROLE_DEFAULTS['purchasing'].add('profile.read')
ROLE_DEFAULTS['warehouse'].add('profile.read')
ROLE_DEFAULTS['sales'].add('profile.read')
ROLE_DEFAULTS['finance'].add('profile.read')
ROLE_DEFAULTS['manager'].add('profile.read')

ROLE_NAMES = {
    'admin': ('Admin', 'Administrator sistem dengan akses seluruh modul, pengguna, role, permission, audit log, transaksi, dan semua gudang.'),
    'operator': ('Operator', 'Staf lintas modul untuk menyiapkan dan memantau transaksi operasional; tidak menyetujui, mem-posting, atau mengelola pergerakan dan penyesuaian stok.'),
    'viewer': ('Viewer', 'Akses baca saja untuk informasi operasional dan laporan yang diizinkan.'),
    'purchasing': ('Purchasing', 'Mengelola supplier, purchase order, dan penerimaan bila ditugaskan; tidak menyetujui PO sendiri atau mengelola pembayaran.'),
    'warehouse': ('Warehouse', 'Menangani pergerakan fisik stok, penerimaan, pengiriman, penyesuaian, dan transfer sesuai cakupan gudang serta izin posting.'),
    'sales': ('Sales', 'Mengelola pelanggan dan siklus pesanan pelanggan tanpa posting pengiriman atau pembayaran.'),
    'finance': ('Finance', 'Mengelola invoice, tagihan supplier, pembayaran, alokasi, piutang, utang, dan laporan keuangan.'),
    'manager': ('Manager', 'Pengawas read-only yang dapat menyetujui transaksi dalam cakupan gudangnya.'),
}

ROUTE_PERMISSION_OVERRIDES = {
    'sales.update_shipment': 'shipments.create',
    'purchasing.update_goods_receipt': 'goods_receipts.create',
    'sales.record_and_post_customer_payment': 'customer_payments.create',
    'purchasing.record_and_post_supplier_payment': 'supplier_payments.create',
    'sales.cancel_shipment': 'shipments.create',
    'purchasing.cancel_goods_receipt': 'goods_receipts.create',
    'auth.me': 'profile.read',
    'auth.update_my_profile': 'profile.read',
    'auth.logout': 'profile.read',
    'warehouse.get_warehouses': 'warehouses.read',
    'warehouse.get_warehouse': 'warehouses.read',
    'sales.shipment_sales_order': 'shipments.post',
    'sales.patch_sales_order': 'sales_orders.create',
    'sales.create_shipment': 'shipments.create',
    'sales.create_shipment_canonical': 'shipments.create',
    'sales.post_shipment': 'shipments.post',
    'sales.create_sales_invoice': 'sales_invoices.create',
    'sales.record_payment': 'customer_payments.create',
    'sales.allocate_payment': 'customer_payments.allocate',
    'purchasing.create_supplier_payment': 'supplier_payments.create',
    'purchasing.allocate_supplier_payment': 'supplier_payments.allocate',
    'inventory_adjuster.get_inventory_adjusters': 'inventory.adjust.read',
    'inventory_adjuster.create_inventory_adjuster': 'inventory.adjust.create',
    'inventory_adjuster.approve_inventory_adjuster': 'inventory.adjust.approve',
    'inventory_adjuster.reject_inventory_adjuster': 'inventory.adjust.approve',
    'inventory_adjuster.post_inventory_adjuster': 'inventory.adjust.post',
    'api_info.get_api_info': 'system.read',
    'api_info.health_check': 'system.read',
    'purchasing.post_purchase_order': 'goods_receipts.post',
    'stock_movements.get_stock_movements': 'inventory.read',
    'reports.get_low_stock_report': 'inventory.read',
    'inventory_transfers.get_transfers': 'inventory.transfer.read',
    'inventory_transfers.get_transfer': 'inventory.transfer.read',
    'inventory_transfers.create_transfer': 'inventory.transfer.create',
    'inventory_transfers.submit_transfer': 'inventory.transfer.submit',
    'inventory_transfers.approve_transfer': 'inventory.transfer.approve',
    'inventory_transfers.reject_transfer': 'inventory.transfer.approve',
    'inventory_transfers.post_transfer': 'inventory.transfer.post',
    'inventory_quarantine.get_quarantines': 'inventory.quarantine.read',
    'inventory_quarantine.request_quarantine_action': 'inventory.quarantine.action.create',
    'inventory_quarantine.approve_quarantine_action': 'inventory.quarantine.action.approve',
    'inventory_quarantine.reject_quarantine_action': 'inventory.quarantine.action.approve',
    'inventory_quarantine.post_quarantine_action': 'inventory.quarantine.action.post',
    'customers.get_customers': 'customers.read',
    'customers.get_customer': 'customers.read',
    'customers.create_customer': 'customers.manage',
    'customers.patch_customer': 'customers.manage',
    'suppliers.get_suppliers': 'suppliers.read',
    'suppliers.get_supplier': 'suppliers.read',
    'suppliers.create_supplier': 'suppliers.manage',
    'suppliers.patch_supplier': 'suppliers.manage',
    'statistics.get_statistics': 'dashboard.read',
    'statistics.get_dashboard': 'finance.read',
    'statistics.get_dashboard_summary': 'finance.read',
}

WAREHOUSE_MODEL_BY_ENDPOINT = {
    'get_warehouse': Warehouse,
    'get_invoice': Invoice,
    'get_vendor_bill': VendorBill,
    'get_sales_order': SalesOrder,
    'patch_sales_order': SalesOrder,
    'get_supplier_payments': SupplierPayment,
    'get_payments': Payment,
    'allocate_customer_payment': Payment,
    'post_payment': Payment,
    'allocate_supplier_payment': SupplierPayment,
    'post_supplier_payment': SupplierPayment,
    'cancel_shipment': Shipment,
    'update_shipment': Shipment,
    'submit_sales_order': SalesOrder,
    'approve_sales_order': SalesOrder,
    'reject_sales_order': SalesOrder,
    'reserve_sales_order': SalesOrder,
    'cancel_sales_order': SalesOrder,
    'shipment_sales_order': SalesOrder,
    'create_shipment': SalesOrder,
    'approve_purchase_order': PurchaseOrder,
    'reject_purchase_order': PurchaseOrder,
    'submit_purchase_order': PurchaseOrder,
    'cancel_purchase_order': PurchaseOrder,
    'get_purchase_order': PurchaseOrder,
    'patch_purchase_order': PurchaseOrder,
    'post_purchase_order': PurchaseOrder,
    'create_goods_receipt': PurchaseOrder,
    'post_goods_receipt': GoodsReceipt,
    'cancel_goods_receipt': GoodsReceipt,
    'update_goods_receipt': GoodsReceipt,
    'get_goods_receipt': GoodsReceipt,
    'get_shipment': Shipment,
    'post_shipment': Shipment,
    'invoice_shipment': Shipment,
    'invoice_sales_order': SalesOrder,
    'get_inventory_balance': InventoryBalance,
    'get_stock_movement': StockMovement,
    'approve_inventory_adjuster': InventoryAdjuster,
    'reject_inventory_adjuster': InventoryAdjuster,
    'post_inventory_adjuster': InventoryAdjuster,
    'get_transfer': StockTransfer,
    'submit_transfer': StockTransfer,
    'approve_transfer': StockTransfer,
    'reject_transfer': StockTransfer,
    'post_transfer': StockTransfer,
    'request_quarantine_action': InventoryQuarantine,
    'approve_quarantine_action': InventoryQuarantineAction,
    'reject_quarantine_action': InventoryQuarantineAction,
    'post_quarantine_action': InventoryQuarantineAction,
    'get_sales_return': SalesReturn,
    'post_sales_return': SalesReturn,
}


def seed_authorization():
    """Insert default role and permission records without overwriting customizations."""
    new_permission_codes = set()
    for code, (name, module, action, warehouse_scoped) in PERMISSION_DEFINITIONS.items():
        permission = db.session.get(Permission, code)
        if permission is None:
            new_permission_codes.add(code)
            db.session.add(Permission(
                code=code,
                name=name,
                module=module,
                action=action,
                warehouse_scoped=warehouse_scoped
            ))
        elif permission.warehouse_scoped != warehouse_scoped:
            permission.warehouse_scoped = warehouse_scoped

    db.session.flush()
    for code, permission_codes in ROLE_DEFAULTS.items():
        role = db.session.get(Role, code)
        if role is None:
            name, description = ROLE_NAMES[code]
            role = Role(
                code=code,
                name=name,
                description=description,
                is_system=True
            )
            role.permissions = [
                db.session.get(Permission, permission_code)
                for permission_code in sorted(permission_codes)
            ]
            db.session.add(role)
        else:
            current_codes = {permission.code for permission in role.permissions}
            role.permissions.extend(
                db.session.get(Permission, permission_code)
                for permission_code in sorted(
                    (permission_codes & new_permission_codes) - current_codes
                )
            )
    db.session.commit()


def sync_system_role_permissions():
    """Apply code defaults while retaining explicitly recorded role overrides."""
    seed_authorization()
    for role_code, permission_codes in ROLE_DEFAULTS.items():
        role = db.session.get(Role, role_code)
        if role is None or not role.is_system:
            raise RuntimeError(
                f'Built-in role "{role_code}" is missing or not marked as a system role.'
            )
        previous_defaults = {
            row.permission_code
            for row in RoleDefaultPermission.query.filter_by(role_code=role_code).all()
        }
        overrides = RolePermissionOverride.query.filter_by(role_code=role_code).all()
        override_codes = {row.permission_code for row in overrides}
        current_codes = {permission.code for permission in role.permissions}

        # On the first adoption of tracked sync, preserve existing grants outside
        # the code defaults; their intent cannot be inferred safely.
        if not previous_defaults and role_code != 'admin':
            for custom_code in current_codes - set(permission_codes):
                if custom_code not in override_codes:
                    override = RolePermissionOverride(
                        role_code=role_code,
                        permission_code=custom_code,
                        is_granted=True
                    )
                    db.session.add(override)
                    overrides.append(override)
                    override_codes.add(custom_code)

        effective_codes = set(permission_codes)
        for override in overrides:
            if override.is_granted:
                effective_codes.add(override.permission_code)
            else:
                effective_codes.discard(override.permission_code)
        if role_code == 'admin':
            effective_codes = set(permission_codes)

        role.permissions = [
            db.session.get(Permission, permission_code)
            for permission_code in sorted(effective_codes)
        ]
        RoleDefaultPermission.query.filter_by(role_code=role_code).delete()
        db.session.add_all([
            RoleDefaultPermission(role_code=role_code, permission_code=permission_code)
            for permission_code in sorted(permission_codes)
        ])
    db.session.commit()


def plan_system_role_permission_reconciliation():
    """Build a read-only report of drift from the canonical role matrix."""
    report = {
        'permission_catalog': {
            'known': sorted(PERMISSION_DEFINITIONS),
            'unknown_database_permissions': [
                {
                    'code': permission.code,
                    'assigned_roles': sorted(role.code for role in permission.roles),
                }
                for permission in Permission.query.all()
                if permission.code not in PERMISSION_DEFINITIONS
            ],
        },
        'roles': [],
    }

    for role_code, default_codes in ROLE_DEFAULTS.items():
        role = db.session.get(Role, role_code)
        if role is None or not role.is_system:
            raise RuntimeError(
                f'Built-in role "{role_code}" is missing or not marked as a system role.'
            )

        defaults = set(default_codes)
        overrides = {
            row.permission_code: row.is_granted
            for row in RolePermissionOverride.query.filter_by(role_code=role_code).all()
        }
        current = {permission.code for permission in role.permissions}
        explicit_grants = {
            code for code, granted in overrides.items()
            if granted and code in PERMISSION_DEFINITIONS
        }
        explicit_denials = {
            code for code, granted in overrides.items()
            if not granted and code in PERMISSION_DEFINITIONS
        }
        effective = (defaults | explicit_grants) - explicit_denials
        if role_code == 'admin':
            # Admin gets the complete current catalog, without stale grants.
            effective = set(PERMISSION_DEFINITIONS)

        report['roles'].append({
            'code': role_code,
            'missing_effective_grants': sorted(effective - current),
            'untracked_grants_to_remove': sorted(
                code for code in current - effective
                if code not in overrides
            ),
            'explicit_grants_to_keep': sorted(explicit_grants),
            'explicit_denials_to_keep': sorted(explicit_denials),
            'denied_grants_to_remove': sorted(explicit_denials & current),
            'unknown_grants_to_remove': sorted(
                code for code in current
                if code not in PERMISSION_DEFINITIONS
            ),
            'unknown_overrides_to_remove': sorted(
                code for code in overrides
                if code not in PERMISSION_DEFINITIONS
            ),
            'stale_default_snapshot': sorted(
                row.permission_code
                for row in RoleDefaultPermission.query.filter_by(role_code=role_code).all()
                if row.permission_code not in defaults
            ),
            'effective_permissions': sorted(effective),
        })
    return report


def apply_system_role_permission_reconciliation():
    """Align built-in roles exactly to defaults plus recorded overrides."""
    # Validate all roles before making any mutations.
    report = plan_system_role_permission_reconciliation()
    try:
        for role_report in report['roles']:
            role_code = role_report['code']
            role = db.session.get(Role, role_code)
            effective = set(role_report['effective_permissions'])
            role.permissions = [
                db.session.get(Permission, code)
                for code in sorted(effective)
            ]

            RoleDefaultPermission.query.filter_by(role_code=role_code).delete()
            db.session.add_all([
                RoleDefaultPermission(role_code=role_code, permission_code=code)
                for code in sorted(ROLE_DEFAULTS[role_code])
            ])

            known_overrides = RolePermissionOverride.query.filter_by(
                role_code=role_code
            ).all()
            for override in known_overrides:
                if override.permission_code not in PERMISSION_DEFINITIONS:
                    db.session.delete(override)
            db.session.add(AuditLog(
                user_id=None,
                action='UPDATE',
                endpoint='cli.reconcile-role-permissions',
                resource_id=role_code,
                status_code=200,
                ip_address=None,
            ))
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return plan_system_role_permission_reconciliation()


def required_permission(endpoint, method):
    if endpoint in ROUTE_PERMISSION_OVERRIDES:
        return ROUTE_PERMISSION_OVERRIDES[endpoint]
    if not endpoint:
        return None

    module, _, view = endpoint.partition('.')
    if module in {'product', 'categories', 'units', 'warehouse'}:
        return 'master_data.read' if method in {'GET', 'HEAD'} else 'master_data.manage'
    if module == 'inventory':
        return 'inventory.read' if method in {'GET', 'HEAD'} else 'inventory.balance.create'
    if module == 'stock_movements':
        return 'inventory.read'
    if module in {'reports', 'statistics'}:
        return 'reports.read'
    if module == 'finance':
        return 'finance.cash.read' if 'cash_summary' in view else 'finance.read'
    if module == 'sales_returns':
        action = _action(view, method)
        return f'sales_returns.{action}'
    if module == 'purchasing':
        resource = _purchasing_resource(view)
        action = _action(view, method)
        return f'{resource}.{action}' if resource else None
    if module == 'sales':
        resource = _sales_resource(view)
        action = _action(view, method)
        return f'{resource}.{action}' if resource else None
    if module == 'user_management':
        if view.startswith('get_role') or view.startswith('list_role'):
            return 'roles.manage'
        return 'users.manage' if 'user' in view else 'roles.manage'
    if module == 'audit_logs':
        return 'audit_logs.read'
    return None


def _action(view, method):
    if method in {'GET', 'HEAD'}:
        return 'read'
    for action in ('approve', 'reject', 'post', 'reserve', 'cancel', 'submit', 'allocate'):
        if action in view:
            return 'approve' if action == 'reject' else action
    return 'create'


def _purchasing_resource(view):
    if 'purchase_order' in view:
        return 'purchase_orders'
    if 'goods_receipt' in view:
        return 'goods_receipts'
    if 'vendor_bill' in view:
        return 'vendor_bills'
    if 'supplier_payment' in view:
        return 'supplier_payments'
    return None


def _sales_resource(view):
    if 'sales_return' in view:
        return 'sales_returns'
    if 'invoice' in view:
        return 'sales_invoices'
    if 'sales_order' in view:
        return 'sales_orders'
    if 'shipment' in view:
        return 'shipments'
    if 'payment' in view:
        return 'customer_payments'
    return None


def has_permission(user, permission_code):
    if user.role == 'admin':
        return permission_code in PERMISSION_DEFINITIONS
    permission = db.session.get(Permission, permission_code)
    if permission is None:
        return False
    role = db.session.get(Role, user.role)
    return bool(role and permission in role.permissions)


def check_warehouse_scope(user, endpoint, view_args=None):
    view_args = view_args or {}
    if user.all_warehouses or user.role == 'admin':
        return None

    allowed_ids = {
        access.warehouse_id
        for access in UserWarehouseAccess.query.filter_by(user_id=user.id).all()
    }
    request.allowed_warehouse_ids = allowed_ids
    values = []
    for key in ('warehouse_id', 'source_warehouse_id', 'destination_warehouse_id'):
        raw = request.args.get(key) if request.method in {'GET', 'HEAD'} else None
        payload = request.get_json(silent=True)
        if raw is None and isinstance(payload, dict):
            raw = payload.get(key)
        if raw is not None:
            try:
                values.append(int(raw))
            except (TypeError, ValueError):
                return jsonify({'error': f'{key} must be an integer'}), 400
    if isinstance(payload, dict):
        balance_id = payload.get('inventory_balance_id')
        if isinstance(balance_id, int) and not isinstance(balance_id, bool):
            balance = db.session.get(InventoryBalance, balance_id)
            if balance:
                values.append(balance.warehouse_id)
        purchase_order_id = payload.get('purchase_order_id')
        if isinstance(purchase_order_id, int) and not isinstance(purchase_order_id, bool):
            purchase_order = db.session.get(PurchaseOrder, purchase_order_id)
            if purchase_order:
                values.append(purchase_order.warehouse_id)
        shipment_id = payload.get('shipment_id')
        if isinstance(shipment_id, int) and not isinstance(shipment_id, bool):
            shipment = db.session.get(Shipment, shipment_id)
            if shipment:
                values.append(shipment.sales_order.warehouse_id)
        sales_order_id = payload.get('sales_order_id')
        if isinstance(sales_order_id, int) and not isinstance(sales_order_id, bool):
            sales_order = db.session.get(SalesOrder, sales_order_id)
            if sales_order:
                values.append(sales_order.warehouse_id)
        goods_receipt_id = payload.get('goods_receipt_id')
        if isinstance(goods_receipt_id, int) and not isinstance(goods_receipt_id, bool):
            goods_receipt = db.session.get(GoodsReceipt, goods_receipt_id)
            if goods_receipt:
                values.append(goods_receipt.purchase_order.warehouse_id)
        invoice_id = payload.get('invoice_id')
        if isinstance(invoice_id, int) and not isinstance(invoice_id, bool):
            invoice = db.session.get(Invoice, invoice_id)
            if invoice:
                values.append(invoice.shipment.sales_order.warehouse_id)
        vendor_bill_id = payload.get('vendor_bill_id')
        if isinstance(vendor_bill_id, int) and not isinstance(vendor_bill_id, bool):
            vendor_bill = db.session.get(VendorBill, vendor_bill_id)
            if vendor_bill:
                values.append(vendor_bill.goods_receipt.purchase_order.warehouse_id)

        # Finance allocations may target several source documents. Validate the
        # real warehouse of every target instead of trusting a client-supplied
        # warehouse_id on the payment request.
        allocations = payload.get('allocations')
        if isinstance(allocations, list):
            for allocation in allocations:
                if not isinstance(allocation, dict):
                    continue
                allocation_invoice_id = allocation.get('invoice_id')
                if (
                    isinstance(allocation_invoice_id, int)
                    and not isinstance(allocation_invoice_id, bool)
                ):
                    invoice = db.session.get(Invoice, allocation_invoice_id)
                    if invoice:
                        values.append(invoice.shipment.sales_order.warehouse_id)
                allocation_bill_id = allocation.get('vendor_bill_id')
                if (
                    isinstance(allocation_bill_id, int)
                    and not isinstance(allocation_bill_id, bool)
                ):
                    vendor_bill = db.session.get(VendorBill, allocation_bill_id)
                    if vendor_bill:
                        values.append(
                            vendor_bill.goods_receipt.purchase_order.warehouse_id
                        )

    if endpoint:
        if endpoint == 'inventory_transfers.get_transfers' and not values:
            return None
        view_name = endpoint.partition('.')[2]
        model = WAREHOUSE_MODEL_BY_ENDPOINT.get(view_name)
        record_id = next(
            (value for key, value in view_args.items() if key.endswith('_id') or key == 'id'),
            None
        )
        if model is not None and isinstance(record_id, int):
            record = db.session.get(model, record_id)
            if record is not None:
                if isinstance(record, PurchaseOrder):
                    values.append(record.warehouse_id)
                elif isinstance(record, GoodsReceipt):
                    values.append(record.purchase_order.warehouse_id)
                elif isinstance(record, SalesOrder):
                    values.append(record.warehouse_id)
                elif isinstance(record, Warehouse):
                    values.append(record.id)
                elif isinstance(record, Invoice):
                    values.append(record.shipment.sales_order.warehouse_id)
                elif isinstance(record, Payment):
                    if record.invoice is not None:
                        values.append(record.invoice.shipment.sales_order.warehouse_id)
                    values.extend(
                        allocation.invoice.shipment.sales_order.warehouse_id
                        for allocation in record.allocations
                    )
                elif isinstance(record, VendorBill):
                    values.append(record.goods_receipt.purchase_order.warehouse_id)
                elif isinstance(record, SupplierPayment):
                    if record.source_vendor_bill is not None:
                        values.append(
                            record.source_vendor_bill.goods_receipt.purchase_order.warehouse_id
                        )
                    values.extend(
                        allocation.vendor_bill.goods_receipt.purchase_order.warehouse_id
                        for allocation in record.allocations
                    )
                elif isinstance(record, Shipment):
                    values.append(record.sales_order.warehouse_id)
                elif isinstance(record, InventoryBalance):
                    values.append(record.warehouse_id)
                elif isinstance(record, StockMovement):
                    values.append(record.warehouse_id)
                elif isinstance(record, InventoryAdjuster):
                    values.append(record.warehouse_id)
                elif isinstance(record, StockTransfer):
                    values.extend((
                        record.source_warehouse_id,
                        record.destination_warehouse_id
                    ))
                elif isinstance(record, InventoryQuarantine):
                    values.append(record.warehouse_id)
                elif isinstance(record, InventoryQuarantineAction):
                    values.append(record.quarantine.warehouse_id)
                elif isinstance(record, SalesReturn):
                    values.append(record.shipment.sales_order.warehouse_id)

    if endpoint in {'sales.get_sales_orders', 'warehouse.get_warehouses'} and not values:
        return None
    if not values:
        return jsonify({'error': 'A permitted warehouse scope is required'}), 403
    if any(warehouse_id not in allowed_ids for warehouse_id in values):
        return jsonify({'error': 'Access to one or more warehouses is denied'}), 403
    return None
