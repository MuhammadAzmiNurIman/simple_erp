import re

from app.authorization import required_permission


_PATH_PARAMETER = re.compile(r'<(?:(?P<converter>[^:<>]+):)?(?P<name>[^<>]+)>')
_BODY_SCHEMAS = {
    'auth.login': 'Login',
    'auth.refresh': 'RefreshToken',
    'auth.update_my_profile': 'UserProfilePatch',
    'product.create_product': 'ProductInput',
    'product.update_product': 'ProductPatch',
    'categories.create_category': 'CategoryInput',
    'categories.update_category': 'CategoryPatch',
    'units.create_unit': 'UnitInput',
    'units.update_unit': 'UnitPatch',
    'warehouse.create_warehouse': 'WarehouseInput',
    'warehouse.update_warehouse': 'WarehousePatch',
    'customers.create_customer': 'PartnerInput',
    'customers.patch_customer': 'PartnerPatch',
    'suppliers.create_supplier': 'PartnerInput',
    'suppliers.patch_supplier': 'PartnerPatch',
    'inventory.manage_inventory_balances': 'InventoryBalanceInput',
    'inventory_adjuster.create_inventory_adjuster': 'InventoryAdjustmentInput',
    'inventory_transfers.create_transfer': 'StockTransferCreate',
    'sales.create_sales_order': 'SalesOrderCreate',
    'sales.patch_sales_order': 'SalesOrderCreate',
    'sales.create_shipment_canonical': 'ShipmentCreate',
    'sales.create_shipment': 'ShipmentItemsCreate',
    'sales.update_shipment': 'ShipmentItemsCreate',
    'sales.create_sales_invoice': 'SalesInvoiceCreate',
    'sales_returns.create_sales_return': 'SalesReturnCreate',
    'purchasing.create_purchase_order': 'PurchaseOrderCreate',
    'purchasing.patch_purchase_order': 'PurchaseOrderPatch',
    'purchasing.create_goods_receipt': 'GoodsReceiptCreate',
    'purchasing.update_goods_receipt': 'GoodsReceiptCreate',
    'purchasing.create_vendor_bill': 'VendorBillCreate',
    'sales.record_payment': 'CustomerPaymentCreate',
    'sales.record_and_post_customer_payment': 'CustomerPaymentPostNow',
    'sales.allocate_customer_payment': 'CustomerPaymentAllocations',
    'purchasing.create_supplier_payment': 'SupplierPaymentCreate',
    'purchasing.record_and_post_supplier_payment': 'SupplierPaymentPostNow',
    'purchasing.allocate_supplier_payment': 'SupplierPaymentAllocations',
    'user_management.create_managed_user': 'ManagedUserCreate',
    'user_management.update_managed_user': 'ManagedUserPatch',
    'user_management.create_role': 'RoleCreate',
    'user_management.replace_role_permissions': 'RolePermissionsReplace',
}
_JSON_BODY_ENDPOINTS = {
    'auth.login', 'auth.register', 'auth.refresh',
    'product.create_product', 'product.update_product',
    'warehouse.create_warehouse', 'warehouse.update_warehouse',
    'categories.create_category', 'categories.update_category',
    'units.create_unit', 'units.update_unit',
    'customers.create_customer', 'customers.patch_customer',
    'suppliers.create_supplier', 'suppliers.patch_supplier',
    'inventory.manage_inventory_balances',
    'inventory_adjuster.create_inventory_adjuster',
    'inventory_transfers.create_transfer',
    'purchasing.create_purchase_order', 'purchasing.create_goods_receipt',
    'purchasing.create_supplier_payment', 'purchasing.allocate_supplier_payment',
    'purchasing.record_and_post_supplier_payment',
    'purchasing.create_vendor_bill',
    'sales.create_sales_order', 'sales.patch_sales_order', 'sales.create_shipment',
    'sales.create_shipment_canonical', 'sales.create_sales_invoice',
    'sales.record_payment', 'sales.allocate_customer_payment',
    'sales.record_and_post_customer_payment', 'sales.update_shipment',
    'sales_returns.create_sales_return',
    'user_management.create_managed_user', 'user_management.create_role',
    'user_management.update_managed_user',
    'user_management.replace_role_permissions',
    'auth.update_my_profile', 'purchasing.patch_purchase_order',
    'purchasing.update_goods_receipt',
}
_PUBLIC_ENDPOINTS = {
    'auth.login', 'auth.register', 'auth.refresh', 'api_info.health_check',
    'openapi.openapi_spec',
}
_HIDDEN_ENDPOINTS = {'auth.register'}
_DEPRECATED_PATHS = {
    '/inventory/adjusters': '/inventory/adjustments',
    '/inventory/adjusters/{adjuster_id}/approve': '/inventory/adjustments/{adjuster_id}/approve',
    '/inventory/adjusters/{adjuster_id}/reject': '/inventory/adjustments/{adjuster_id}/reject',
    '/inventory/adjusters/{adjuster_id}/post': '/inventory/adjustments/{adjuster_id}/post',
    '/movements': '/inventory/movements',
    '/movements/{movement_id}': '/inventory/movements/{movement_id}',
    '/reports/low-stock': '/inventory/low-stock',
    '/invoices': '/sales-invoices',
    '/invoices/{invoice_id}': '/sales-invoices/{invoice_id}',
    '/payments': '/customer-payments',
    '/payments/{payment_id}/post': '/customer-payments/{payment_id}/post',
}
_PAGINATED_ENDPOINTS = {
    'audit_logs.get_audit_logs',
    'categories.get_categories',
    'customers.get_customers',
    'finance.get_payables',
    'finance.get_receivables',
    'inventory.manage_inventory_balances',
    'inventory_adjuster.get_inventory_adjusters',
    'inventory_transfers.get_transfers',
    'product.get_products',
    'purchasing.get_goods_receipts',
    'purchasing.get_purchase_orders',
    'purchasing.get_supplier_payments',
    'purchasing.get_vendor_bills',
    'reports.get_inventory_report',
    'reports.get_low_stock_report',
    'reports.get_payables_report',
    'reports.get_purchases_report',
    'reports.get_receivables_report',
    'reports.get_replenishment_report',
    'reports.get_sales_report',
    'reports.get_stock_movement_report',
    'reports.get_turnover_report',
    'sales.get_invoices',
    'sales.get_payments',
    'sales.get_sales_orders',
    'sales.get_shipments',
    'sales_returns.get_sales_returns',
    'stock_movements.get_stock_movements',
    'suppliers.get_suppliers',
    'units.get_units',
    'user_management.get_users',
    'warehouse.get_warehouses',
}
_QUERY_FILTERS = {
    'api_info.get_api_info': {},
    'audit_logs.get_audit_logs': {
        'user_id': {'type': 'integer', 'minimum': 1},
        'endpoint': {'type': 'string'},
        'action': {'type': 'string'},
    },
    'categories.get_categories': {
        'active': {'type': 'string', 'enum': ['true', 'false']},
    },
    'customers.get_customers': {},
    'finance.get_cash_summary': {
        'from_date': {'type': 'string', 'format': 'date'},
        'to_date': {'type': 'string', 'format': 'date'},
    },
    'finance.get_payables': {
        'warehouse_id': {'type': 'integer', 'minimum': 1},
        'supplier_id': {'type': 'integer', 'minimum': 1},
        'from_date': {'type': 'string', 'format': 'date'},
        'to_date': {'type': 'string', 'format': 'date'},
        'status': {'type': 'string', 'enum': ['OPEN', 'PARTIALLY_PAID', 'PAID']},
    },
    'finance.get_receivables': {
        'warehouse_id': {'type': 'integer', 'minimum': 1},
        'customer_id': {'type': 'integer', 'minimum': 1},
        'as_of': {'type': 'string', 'format': 'date'},
        'from_date': {'type': 'string', 'format': 'date'},
        'to_date': {'type': 'string', 'format': 'date'},
        'status': {'type': 'string', 'enum': ['OPEN', 'PARTIALLY_PAID', 'PAID']},
    },
    'inventory.get_inventory_summary': {
        'warehouse_id': {'type': 'integer', 'minimum': 1},
    },
    'inventory.manage_inventory_balances': {
        'product_id': {'type': 'integer', 'minimum': 1},
        'warehouse_id': {'type': 'integer', 'minimum': 1},
        'active': {'type': 'string', 'enum': ['true', 'false']},
    },
    'inventory_adjuster.get_inventory_adjusters': {
        'type': {'type': 'string'},
        'status': {'type': 'string', 'enum': ['PENDING', 'APPROVED', 'REJECTED', 'POSTED']},
        'warehouse_id': {'type': 'integer', 'minimum': 1},
    },
    'inventory_transfers.get_transfers': {
        'status': {'type': 'string', 'enum': ['DRAFT', 'SUBMITTED', 'APPROVED', 'POSTED', 'CANCELLED']},
        'source_warehouse_id': {'type': 'integer', 'minimum': 1},
        'destination_warehouse_id': {'type': 'integer', 'minimum': 1},
        'warehouse_id': {'type': 'integer', 'minimum': 1, 'description': 'Filter transfers where this warehouse is the source or destination.'},
    },
    'product.get_products': {
        'name': {'type': 'string'},
        'category_id': {'type': 'integer', 'minimum': 1},
        'unit_id': {'type': 'integer', 'minimum': 1},
        'active': {'type': 'string', 'enum': ['true', 'false']},
    },
    'purchasing.get_goods_receipts': {
        'status': {'type': 'string'},
        'purchase_order_id': {'type': 'integer', 'minimum': 1},
        'warehouse_id': {'type': 'integer', 'minimum': 1},
    },
    'purchasing.get_purchase_orders': {
        'status': {'type': 'string'},
        'warehouse_id': {'type': 'integer', 'minimum': 1},
    },
    'purchasing.get_supplier_payments': {
        'status': {'type': 'string'},
        'supplier_id': {'type': 'integer', 'minimum': 1},
    },
    'purchasing.get_vendor_bills': {
        'status': {'type': 'string'},
        'supplier_id': {'type': 'integer', 'minimum': 1},
    },
    'reports.get_inventory_report': {
        'warehouse_id': {'type': 'integer', 'minimum': 1},
        'product_id': {'type': 'integer', 'minimum': 1},
        'category_id': {'type': 'integer', 'minimum': 1},
    },
    'reports.get_low_stock_report': {
        'warehouse_id': {'type': 'integer', 'minimum': 1},
        'product_id': {'type': 'integer', 'minimum': 1},
        'category_id': {'type': 'integer', 'minimum': 1},
    },
    'reports.get_payables_report': {
        'warehouse_id': {'type': 'integer', 'minimum': 1},
        'supplier_id': {'type': 'integer', 'minimum': 1},
        'from_date': {'type': 'string', 'format': 'date'},
        'to_date': {'type': 'string', 'format': 'date'},
        'status': {'type': 'string', 'enum': ['OPEN', 'PARTIALLY_PAID', 'PAID']},
    },
    'reports.get_purchases_report': {
        'from_date': {'type': 'string', 'format': 'date'},
        'to_date': {'type': 'string', 'format': 'date'},
        'warehouse_id': {'type': 'integer', 'minimum': 1},
        'supplier_id': {'type': 'integer', 'minimum': 1},
        'status': {'type': 'string', 'enum': ['OPEN', 'PARTIALLY_PAID', 'PAID']},
    },
    'reports.get_receivables_report': {
        'warehouse_id': {'type': 'integer', 'minimum': 1},
        'customer_id': {'type': 'integer', 'minimum': 1},
        'as_of': {'type': 'string', 'format': 'date'},
        'from_date': {'type': 'string', 'format': 'date'},
        'to_date': {'type': 'string', 'format': 'date'},
        'status': {'type': 'string', 'enum': ['OPEN', 'PARTIALLY_PAID', 'PAID']},
    },
    'reports.get_replenishment_report': {
        'warehouse_id': {'type': 'integer', 'minimum': 1},
    },
    'reports.get_sales_report': {
        'from_date': {'type': 'string', 'format': 'date'},
        'to_date': {'type': 'string', 'format': 'date'},
        'warehouse_id': {'type': 'integer', 'minimum': 1},
        'customer_id': {'type': 'integer', 'minimum': 1},
        'status': {'type': 'string', 'enum': ['OPEN', 'PARTIALLY_PAID', 'PAID']},
    },
    'reports.get_stock_movement_report': {
        'from_date': {'type': 'string', 'format': 'date'},
        'to_date': {'type': 'string', 'format': 'date'},
        'warehouse_id': {'type': 'integer', 'minimum': 1},
        'product_id': {'type': 'integer', 'minimum': 1},
        'category_id': {'type': 'integer', 'minimum': 1},
        'movement_type': {'type': 'string'},
    },
    'reports.get_turnover_report': {
        'warehouse_id': {'type': 'integer', 'minimum': 1},
        'type': {'type': 'string'},
    },
    'sales.get_invoices': {
        'status': {'type': 'string'},
    },
    'sales.get_payments': {
        'customer_id': {'type': 'integer', 'minimum': 1},
    },
    'sales.get_sales_orders': {
        'status': {'type': 'string'},
        'warehouse_id': {'type': 'integer', 'minimum': 1},
    },
    'sales.get_shipments': {
        'status': {'type': 'string'},
        'sales_order_id': {'type': 'integer', 'minimum': 1},
        'warehouse_id': {'type': 'integer', 'minimum': 1},
    },
    'sales_returns.get_sales_returns': {
        'status': {'type': 'string'},
        'warehouse_id': {'type': 'integer', 'minimum': 1},
        'shipment_id': {'type': 'integer', 'minimum': 1},
    },
    'statistics.get_dashboard': {
        'warehouse_id': {'type': 'integer', 'minimum': 1},
    },
    'statistics.get_dashboard_summary': {
        'from_date': {'type': 'string', 'format': 'date'},
        'to_date': {'type': 'string', 'format': 'date'},
        'warehouse_id': {'type': 'integer', 'minimum': 1},
    },
    'statistics.get_statistics': {
        'warehouse_id': {'type': 'integer', 'minimum': 1},
    },
    'stock_movements.get_stock_movements': {
        'product_id': {'type': 'integer', 'minimum': 1},
        'warehouse_id': {'type': 'integer', 'minimum': 1},
        'category_id': {'type': 'integer', 'minimum': 1},
        'movement_type': {'type': 'string'},
        'from_date': {'type': 'string', 'format': 'date'},
        'to_date': {'type': 'string', 'format': 'date'},
    },
    'suppliers.get_suppliers': {},
    'units.get_units': {
        'active': {'type': 'string', 'enum': ['true', 'false']},
    },
    'user_management.get_users': {
        'role': {'type': 'string'},
        'active': {'type': 'string', 'enum': ['true', 'false']},
        'search': {'type': 'string'},
    },
    'user_management.get_permissions': {
        'module': {'type': 'string'},
    },
    'warehouse.get_warehouses': {
        'active': {'type': 'string', 'enum': ['true', 'false']},
    },
}
_RESPONSE_SCHEMAS = {
    'api_info.get_api_info': 'ApiInfoResponse',
    'api_info.health_check': 'HealthResponse',
    'auth.login': 'AuthTokenResponse',
    'auth.logout': 'MessageResponse',
    'auth.me': 'AuthProfileResponse',
    'auth.update_my_profile': 'AuthProfileResponse',
    'auth.refresh': 'AuthTokenResponse',
    'categories.delete_category': 'MessageResponse',
    'customers.create_customer': 'PartnerResponse',
    'customers.get_customer': 'PartnerResponse',
    'customers.patch_customer': 'PartnerResponse',
    'inventory_adjuster.approve_inventory_adjuster': 'WorkflowResponse',
    'inventory_adjuster.reject_inventory_adjuster': 'WorkflowResponse',
    'inventory_adjuster.post_inventory_adjuster': 'WorkflowResponse',
    'inventory.manage_inventory_balances': 'InventoryBalanceListResponse',
    'inventory.get_inventory_balance': 'InventoryBalanceResponse',
    'inventory_quarantine.get_quarantines': 'QuarantineListResponse',
    'inventory_quarantine.request_quarantine_action': 'WorkflowResponse',
    'inventory_quarantine.approve_quarantine_action': 'WorkflowResponse',
    'inventory_quarantine.reject_quarantine_action': 'WorkflowResponse',
    'inventory_quarantine.post_quarantine_action': 'WorkflowResponse',
    'inventory_transfers.get_transfer': 'TransferResponse',
    'inventory_transfers.submit_transfer': 'WorkflowResponse',
    'inventory_transfers.approve_transfer': 'WorkflowResponse',
    'inventory_transfers.reject_transfer': 'WorkflowResponse',
    'inventory_transfers.post_transfer': 'WorkflowResponse',
    'product.create_product': 'ProductResponse',
    'product.get_product': 'ProductResponse',
    'product.update_product': 'ProductResponse',
    'product.delete_product': 'MessageResponse',
    'purchasing.create_purchase_order': 'PurchaseOrderResponse',
    'purchasing.patch_purchase_order': 'PurchaseOrderResponse',
    'purchasing.get_purchase_order': 'PurchaseOrderResponse',
    'purchasing.approve_purchase_order': 'WorkflowResponse',
    'purchasing.cancel_purchase_order': 'WorkflowResponse',
    'purchasing.post_purchase_order': 'WorkflowResponse',
    'purchasing.reject_purchase_order': 'WorkflowResponse',
    'purchasing.submit_purchase_order': 'WorkflowResponse',
    'purchasing.create_goods_receipt': 'GoodsReceiptResponse',
    'purchasing.get_goods_receipt': 'GoodsReceiptResponse',
    'purchasing.update_goods_receipt': 'GoodsReceiptResponse',
    'purchasing.post_goods_receipt': 'WorkflowResponse',
    'purchasing.create_vendor_bill': 'VendorBillResponse',
    'purchasing.get_vendor_bill': 'VendorBillResponse',
    'purchasing.create_supplier_payment': 'SupplierPaymentResponse',
    'purchasing.record_and_post_supplier_payment': 'SupplierPaymentResponse',
    'purchasing.allocate_supplier_payment': 'SupplierPaymentResponse',
    'purchasing.post_supplier_payment': 'WorkflowResponse',
    'roles.get_roles': 'RoleListResponse',
    'user_management.get_roles': 'RoleListResponse',
    'user_management.create_role': 'RoleResponse',
    'user_management.replace_role_permissions': 'RoleResponse',
    'user_management.get_permissions': 'PermissionListResponse',
    'user_management.get_users': 'UserListResponse',
    'user_management.create_managed_user': 'ManagedUserResponse',
    'user_management.update_managed_user': 'ManagedUserResponse',
    'sales.create_sales_order': 'SalesOrderResponse',
    'sales.get_sales_order': 'SalesOrderResponse',
    'sales.patch_sales_order': 'SalesOrderResponse',
    'sales.submit_sales_order': 'WorkflowResponse',
    'sales.approve_sales_order': 'WorkflowResponse',
    'sales.reject_sales_order': 'WorkflowResponse',
    'sales.reserve_sales_order': 'WorkflowResponse',
    'sales.cancel_sales_order': 'WorkflowResponse',
    'sales.shipment_sales_order': 'WorkflowResponse',
    'sales.create_shipment': 'ShipmentResponse',
    'sales.update_shipment': 'ShipmentResponse',
    'sales.create_shipment_canonical': 'ShipmentResponse',
    'sales.get_shipment': 'ShipmentResponse',
    'sales.post_shipment': 'WorkflowResponse',
    'sales.record_and_post_customer_payment': 'PaymentResponse',
    'sales.invoice_shipment': 'InvoiceResponse',
    'sales.invoice_sales_order': 'InvoiceResponse',
    'sales.create_sales_invoice': 'InvoiceResponse',
    'sales.get_invoice': 'InvoiceResponse',
    'sales.record_payment': 'PaymentResponse',
    'sales.allocate_customer_payment': 'PaymentResponse',
    'sales.post_payment': 'WorkflowResponse',
    'sales_returns.get_sales_return': 'SalesReturnResponse',
    'sales_returns.post_sales_return': 'WorkflowResponse',
    'suppliers.create_supplier': 'PartnerResponse',
    'suppliers.get_supplier': 'PartnerResponse',
    'suppliers.patch_supplier': 'PartnerResponse',
    'units.delete_unit': 'MessageResponse',
    'warehouse.delete_warehouse': 'MessageResponse',
    'vendor_bills.get_vendor_bill': 'VendorBillResponse',
    'auth.get_current_user': 'AuthProfileResponse',
    'audit_logs.get_audit_logs': 'AuditLogListResponse',
    'categories.get_categories': 'CategoryListResponse',
    'categories.create_category': 'CategoryResponse',
    'categories.get_category': 'CategoryResponse',
    'categories.update_category': 'CategoryResponse',
    'units.get_units': 'UnitListResponse',
    'units.create_unit': 'UnitResponse',
    'units.get_unit': 'UnitResponse',
    'units.update_unit': 'UnitResponse',
    'warehouse.get_warehouses': 'WarehouseListResponse',
    'warehouse.create_warehouse': 'WarehouseResponse',
    'warehouse.get_warehouse': 'WarehouseResponse',
    'warehouse.update_warehouse': 'WarehouseResponse',
    'statistics.get_statistics': 'StatisticsResponse',
    'statistics.get_dashboard': 'DashboardResponse',
    'statistics.get_dashboard_summary': 'DashboardSummaryResponse',
    'reports.get_low_stock_report': 'LowStockReportResponse',
    'reports.get_replenishment_report': 'LowStockReportResponse',
    'reports.get_turnover_report': 'TurnoverReportResponse',
    'inventory.get_inventory_summary': 'InventorySummaryResponse',
    'stock_movements.get_stock_movements': 'PagedObjectResponse',
    'stock_movements.get_stock_movement': 'StockMovementResponse',
    'finance.get_receivables': 'ReceivablesResponse',
    'finance.get_payables': 'PayablesResponse',
    'finance.get_cash_summary': 'CashSummaryResponse',
    'sales.get_sales_orders': 'SalesOrderListResponse',
    'sales.get_shipments': 'ShipmentListResponse',
    'sales.get_invoices': 'InvoiceListResponse',
    'sales.get_payments': 'PaymentListResponse',
    'purchasing.get_purchase_orders': 'PurchaseOrderListResponse',
    'purchasing.get_goods_receipts': 'GoodsReceiptListResponse',
    'purchasing.get_vendor_bills': 'VendorBillListResponse',
    'purchasing.get_supplier_payments': 'SupplierPaymentListResponse',
    'product.get_products': 'ProductListResponse',
    'customers.get_customers': 'PartnerListResponse',
    'suppliers.get_suppliers': 'PartnerListResponse',
    'reports.get_inventory_report': 'InventoryReportResponse',
    'reports.get_stock_movement_report': 'StockMovementReportResponse',
    'reports.get_sales_report': 'SalesReportResponse',
    'reports.get_purchases_report': 'PurchasesReportResponse',
    'reports.get_receivables_report': 'ReceivablesResponse',
    'reports.get_payables_report': 'PayablesResponse',
    'inventory_transfers.get_transfers': 'TransferListResponse',
    'inventory_transfers.create_transfer': 'TransferResponse',
    'inventory_adjuster.get_inventory_adjusters': 'AdjustmentListResponse',
    'inventory_adjuster.create_inventory_adjuster': 'AdjustmentResponse',
    'sales_returns.get_sales_returns': 'SalesReturnListResponse',
    'sales_returns.create_sales_return': 'SalesReturnResponse',
}


def _path_details(rule):
    parameters = []

    def replace(match):
        converter = match.group('converter') or 'string'
        parameters.append({
            'name': match.group('name'),
            'in': 'path',
            'required': True,
            'schema': {'type': 'integer' if converter == 'int' else 'string'},
        })
        return '{' + match.group('name') + '}'

    return _PATH_PARAMETER.sub(replace, rule), parameters


def _operation_id(endpoint, method, path):
    path_suffix = re.sub(r'[^a-zA-Z0-9]+', '_', path).strip('_')
    return f'{endpoint.replace(".", "_")}_{method.lower()}_{path_suffix}'


def _body_schema(endpoint):
    schema_name = _BODY_SCHEMAS.get(endpoint)
    if schema_name:
        return {'$ref': f'#/components/schemas/{schema_name}'}
    return {'$ref': '#/components/schemas/JsonObject'}


def _query_parameters(endpoint):
    parameters = []
    if endpoint in _PAGINATED_ENDPOINTS:
        per_page_default = 25 if endpoint == 'audit_logs.get_audit_logs' else 10
        parameters.extend([
            {
                'name': 'page',
                'in': 'query',
                'required': False,
                'schema': {'type': 'integer', 'minimum': 1, 'default': 1},
            },
            {
                'name': 'per_page',
                'in': 'query',
                'required': False,
                'schema': {
                    'type': 'integer', 'minimum': 1, 'maximum': 100,
                    'default': per_page_default,
                },
            },
        ])
    for name, schema in _QUERY_FILTERS.get(endpoint, {}).items():
        parameters.append({
            'name': name,
            'in': 'query',
            'required': False,
            'schema': schema,
        })
    return parameters


def create_openapi_spec(app):
    paths = {}
    tags = set()

    for rule in sorted(app.url_map.iter_rules(), key=lambda item: item.rule):
        if not rule.rule.startswith('/api/v1/'):
            continue

        path, path_parameters = _path_details(rule.rule[len('/api/v1'):])
        endpoint = rule.endpoint
        if endpoint in _HIDDEN_ENDPOINTS:
            continue
        module, _, view_name = endpoint.partition('.')
        tags.add(module)

        for method in sorted(rule.methods - {'HEAD', 'OPTIONS'}):
            permission = required_permission(endpoint, method)
            creates_resource = method == 'POST' and (
                view_name.startswith('create_')
                or view_name.startswith('record_')
            )
            responses = {
                '400': {'$ref': '#/components/responses/BadRequest'},
                '401': {'$ref': '#/components/responses/Unauthorized'},
                '403': {'$ref': '#/components/responses/Forbidden'},
                '404': {'$ref': '#/components/responses/NotFound'},
                '409': {'$ref': '#/components/responses/Conflict'},
                '500': {'$ref': '#/components/responses/ServerError'},
            }
            if endpoint != 'auth.register':
                responses['201' if creates_resource else '200'] = {
                    'description': (
                        'Resource created successfully.'
                        if creates_resource else 'Request completed successfully.'
                    ),
                    'content': {
                        'application/json': {
                            'schema': {
                                '$ref': (
                                    '#/components/schemas/OpenAPIDocument'
                                    if endpoint == 'openapi.openapi_spec'
                                    else f"#/components/schemas/{_RESPONSE_SCHEMAS.get(endpoint, 'JsonObject')}"
                                )
                            }
                        }
                    },
                }
            operation = {
                'operationId': _operation_id(endpoint, method, path),
                'tags': [module],
                'summary': view_name.replace('_', ' ').capitalize(),
                'description': (
                    f'API operation `{endpoint}`. Required permission: `{permission}`.'
                    if permission else f'API operation `{endpoint}`.'
                ),
                'parameters': list(path_parameters),
                'responses': responses,
                'x-required-permission': permission,
            }
            if endpoint not in _PUBLIC_ENDPOINTS:
                operation['security'] = [{'BearerAuth': []}]

            if path in _DEPRECATED_PATHS:
                operation['deprecated'] = True
                operation['x-canonical-path'] = _DEPRECATED_PATHS[path]

            if method in {'POST', 'PUT', 'PATCH'} and endpoint in _JSON_BODY_ENDPOINTS:
                operation['requestBody'] = {
                    'required': True,
                    'content': {
                        'application/json': {'schema': _body_schema(endpoint)}
                    },
                }

            if method == 'GET':
                operation['parameters'].extend(_query_parameters(endpoint))

            paths.setdefault(path, {})[method.lower()] = operation

    return {
        'openapi': '3.1.0',
        'info': {
            'title': app.config['API_TITLE'],
            'version': app.config['API_VERSION'],
            'description': app.config['API_DESCRIPTION'],
        },
        'servers': [{'url': '/api/v1'}],
        'tags': [{'name': tag} for tag in sorted(tags)],
        'paths': paths,
        'components': {
            'securitySchemes': {
                'BearerAuth': {
                    'type': 'http',
                    'scheme': 'bearer',
                    'bearerFormat': 'JWT',
                }
            },
            'schemas': {
                'OpenAPIDocument': {
                    'type': 'object',
                    'required': ['openapi', 'info', 'paths'],
                    'properties': {
                        'openapi': {'type': 'string', 'const': '3.1.0'},
                        'info': {'type': 'object'},
                        'paths': {'type': 'object'},
                        'components': {'type': 'object'},
                    },
                    'additionalProperties': True,
                },
            'AuditLogRecord': {
                'type': 'object', 'required': ['id', 'action', 'endpoint', 'status_code', 'created_at'],
                'properties': {
                    'id': {'type': 'integer'}, 'user_id': {'type': ['integer', 'null']},
                    'username': {'type': ['string', 'null']}, 'action': {'type': 'string', 'enum': ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']},
                    'endpoint': {'type': 'string'}, 'resource_id': {'type': ['string', 'null']},
                    'status_code': {'type': 'integer'}, 'ip_address': {'type': ['string', 'null']},
                    'created_at': {'type': ['string', 'null'], 'format': 'date-time'},
                },
            },
            'AuditLogListResponse': {
                'type': 'object', 'required': ['data', 'total', 'page', 'pages'],
                'properties': {'data': {'type': 'array', 'items': {'$ref': '#/components/schemas/AuditLogRecord'}}, 'total': {'type': 'integer'}, 'page': {'type': 'integer'}, 'pages': {'type': 'integer'}},
            },
            'CategoryRecord': {
                'type': 'object', 'required': ['id', 'name'],
                'properties': {'id': {'type': 'integer'}, 'name': {'type': 'string'}, 'description': {'type': ['string', 'null']}, 'is_active': {'type': 'boolean'}},
            },
            'UnitRecord': {
                'type': 'object', 'required': ['id', 'name'],
                'properties': {'id': {'type': 'integer'}, 'name': {'type': 'string'}, 'symbol': {'type': ['string', 'null']}, 'is_active': {'type': 'boolean'}},
            },
            'WarehouseRecord': {
                'type': 'object', 'required': ['id', 'code', 'name'],
                'properties': {'id': {'type': 'integer'}, 'code': {'type': 'string'}, 'name': {'type': 'string'}, 'address': {'type': ['string', 'null']}, 'is_active': {'type': 'boolean'}},
            },
            'CategoryListResponse': {'type': 'object', 'required': ['data', 'total', 'page', 'pages'], 'properties': {'data': {'type': 'array', 'items': {'$ref': '#/components/schemas/CategoryRecord'}}, 'total': {'type': 'integer'}, 'page': {'type': 'integer'}, 'pages': {'type': 'integer'}}},
            'CategoryResponse': {'type': 'object', 'required': ['data'], 'properties': {'data': {'$ref': '#/components/schemas/CategoryRecord'}, 'message': {'type': 'string'}}},
            'UnitListResponse': {'type': 'object', 'required': ['data', 'total', 'page', 'pages'], 'properties': {'data': {'type': 'array', 'items': {'$ref': '#/components/schemas/UnitRecord'}}, 'total': {'type': 'integer'}, 'page': {'type': 'integer'}, 'pages': {'type': 'integer'}}},
            'UnitResponse': {'type': 'object', 'required': ['data'], 'properties': {'data': {'$ref': '#/components/schemas/UnitRecord'}, 'message': {'type': 'string'}}},
            'WarehouseListResponse': {'type': 'object', 'required': ['data', 'total', 'page', 'pages'], 'properties': {'data': {'type': 'array', 'items': {'$ref': '#/components/schemas/WarehouseRecord'}}, 'total': {'type': 'integer'}, 'page': {'type': 'integer'}, 'pages': {'type': 'integer'}}},
            'WarehouseResponse': {'type': 'object', 'required': ['data'], 'properties': {'data': {'$ref': '#/components/schemas/WarehouseRecord'}, 'message': {'type': 'string'}}},
            'PartnerRecord': {'type': 'object', 'required': ['id', 'code', 'name'], 'properties': {'id': {'type': 'integer'}, 'code': {'type': 'string'}, 'name': {'type': 'string'}, 'email': {'type': ['string', 'null']}, 'phone': {'type': ['string', 'null']}, 'address': {'type': ['string', 'null']}, 'is_active': {'type': 'boolean'}}},
            'PartnerListResponse': {'type': 'object', 'required': ['data', 'total', 'page', 'pages'], 'properties': {'data': {'type': 'array', 'items': {'$ref': '#/components/schemas/PartnerRecord'}}, 'total': {'type': 'integer'}, 'page': {'type': 'integer'}, 'pages': {'type': 'integer'}}},
            'ProductRecord': {'type': 'object', 'required': ['id', 'sku', 'name'], 'properties': {'id': {'type': 'integer'}, 'sku': {'type': 'string'}, 'name': {'type': 'string'}, 'category_id': {'type': ['integer', 'null']}, 'unit_id': {'type': ['integer', 'null']}, 'sales_price': {'type': ['number', 'null']}, 'min_stock': {'type': 'number'}, 'is_active': {'type': 'boolean'}}},
            'ProductListResponse': {'type': 'object', 'required': ['data', 'total', 'page', 'pages'], 'properties': {'data': {'type': 'array', 'items': {'$ref': '#/components/schemas/ProductRecord'}}, 'total': {'type': 'integer'}, 'page': {'type': 'integer'}, 'pages': {'type': 'integer'}}},
            'StatisticsResponse': {'type': 'object', 'required': ['data'], 'properties': {'data': {'type': 'object', 'properties': {'total_products': {'type': 'integer'}, 'total_warehouses': {'type': 'integer'}, 'total_customers': {'type': 'integer'}, 'total_sales_orders': {'type': 'integer'}, 'total_inventory_value': {'type': ['number', 'null']}, 'low_stock_count': {'type': 'integer'}, 'recent_sales': {'type': 'array', 'items': {'type': 'object', 'properties': {'id': {'type': 'integer'}, 'code': {'type': 'string'}, 'status': {'type': 'string'}, 'total_amount': {'type': ['number', 'null']}, 'created_at': {'type': ['string', 'null'], 'format': 'date-time'}}}}}}, 'message': {'type': 'string'}}},
            'DashboardResponse': {'type': 'object', 'required': ['data'], 'properties': {'data': {'type': 'object', 'properties': {'sales_by_warehouse': {'type': 'array', 'items': {'type': 'object', 'properties': {'warehouse_code': {'type': 'string'}, 'warehouse_name': {'type': 'string'}, 'total_orders': {'type': 'integer'}, 'total_sales_amount': {'type': 'number'}}}}, 'inventory_by_warehouse': {'type': 'array', 'items': {'type': 'object', 'properties': {'warehouse_code': {'type': 'string'}, 'warehouse_name': {'type': 'string'}, 'total_on_hand': {'type': 'number'}, 'total_reserved': {'type': 'number'}}}}, 'stock_value_by_warehouse': {'type': 'array', 'items': {'type': 'object', 'properties': {'warehouse_code': {'type': 'string'}, 'warehouse_name': {'type': 'string'}, 'total_value': {'type': 'number'}}}}, 'low_stock_products': {'type': 'array', 'items': {'type': 'object', 'properties': {'product_id': {'type': 'integer'}, 'sku': {'type': 'string'}, 'name': {'type': 'string'}, 'min_stock': {'type': 'number'}, 'quantity_on_hand': {'type': 'number'}, 'stock_deficit': {'type': 'number'}}}}}}, 'message': {'type': 'string'}}},
            'DashboardSummaryResponse': {'type': 'object', 'required': ['data'], 'properties': {'data': {'type': 'object', 'required': ['period', 'total_sales_amount', 'total_purchase_amount', 'inventory_value', 'receivables_outstanding', 'payables_outstanding', 'cash_incoming', 'cash_outgoing', 'cash_net', 'stock_distribution'], 'properties': {'period': {'$ref': '#/components/schemas/ReportPeriod'}, 'warehouse_id': {'type': ['integer', 'null']}, 'total_sales_amount': {'type': 'number'}, 'total_purchase_amount': {'type': 'number'}, 'inventory_value': {'type': 'number'}, 'low_stock_balance_count': {'type': 'integer'}, 'receivables_outstanding': {'type': 'number'}, 'payables_outstanding': {'type': 'number'}, 'cash_incoming': {'type': 'number'}, 'cash_outgoing': {'type': 'number'}, 'cash_net': {'type': 'number'}, 'cash_scope': {'type': 'string', 'enum': ['company-wide', 'warehouse-attributed']}, 'stock_distribution': {'type': 'array', 'items': {'type': 'object', 'properties': {'warehouse_id': {'type': 'integer'}, 'warehouse_code': {'type': 'string'}, 'warehouse_name': {'type': 'string'}, 'quantity_on_hand': {'type': 'number'}, 'quantity_reserved': {'type': 'number'}, 'quantity_available': {'type': 'number'}, 'inventory_value': {'type': 'number'}}}}}}}},
            'CashSummaryResponse': {'type': 'object', 'required': ['data'], 'properties': {'data': {'type': 'object', 'properties': {'from_date': {'type': ['string', 'null'], 'format': 'date'}, 'to_date': {'type': ['string', 'null'], 'format': 'date'}, 'incoming_amount': {'type': 'number'}, 'outgoing_amount': {'type': 'number'}, 'net_amount': {'type': 'number'}, 'incoming_payment_count': {'type': 'integer'}, 'outgoing_payment_count': {'type': 'integer'}}}}},
            'LowStockReportResponse': {'type': 'object', 'required': ['data', 'total', 'page', 'pages'], 'properties': {'data': {'type': 'array', 'items': {'type': 'object', 'properties': {'product_id': {'type': 'integer'}, 'sku': {'type': 'string'}, 'name': {'type': 'string'}, 'category': {'type': ['string', 'null']}, 'warehouse': {'type': 'string'}, 'warehouse_code': {'type': 'string'}, 'min_stock': {'type': 'number'}, 'quantity_on_hand': {'type': 'number'}, 'quantity_reserved': {'type': 'number'}, 'stock_deficit': {'type': 'number'}, 'recommended_qty': {'type': 'number'}}}}, 'total': {'type': 'integer'}, 'page': {'type': 'integer'}, 'pages': {'type': 'integer'}}},
            'TurnoverReportResponse': {'type': 'object', 'required': ['data', 'total', 'page', 'pages'], 'properties': {'data': {'type': 'array', 'items': {'type': 'object', 'properties': {'product_id': {'type': 'integer'}, 'sku': {'type': 'string'}, 'name': {'type': 'string'}, 'total_quantity': {'type': 'number'}, 'movement_count': {'type': 'integer'}, 'movement_type': {'type': 'string'}}}}, 'total': {'type': 'integer'}, 'page': {'type': 'integer'}, 'pages': {'type': 'integer'}}},
            'InventorySummaryResponse': {'type': 'object', 'required': ['data'], 'properties': {'data': {'type': 'array', 'items': {'type': 'object', 'required': ['warehouse_code', 'product_name', 'on_hand', 'reserved', 'available', 'average_cost', 'total_value'], 'properties': {'warehouse_code': {'type': 'string'}, 'product_name': {'type': 'string'}, 'on_hand': {'type': 'number'}, 'reserved': {'type': 'number'}, 'available': {'type': 'number'}, 'average_cost': {'type': 'number'}, 'total_value': {'type': 'number'}}}}}},
            'PagedObjectResponse': {'type': 'object', 'required': ['data', 'total', 'page', 'pages'], 'properties': {'data': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': True}}, 'total': {'type': 'integer'}, 'page': {'type': 'integer'}, 'pages': {'type': 'integer'}}},
            'ApiInfoResponse': {'type': 'object', 'required': ['name', 'version', 'description', 'total_endpoints', 'total_modules'], 'properties': {'name': {'type': 'string'}, 'version': {'type': 'string'}, 'description': {'type': 'string'}, 'total_endpoints': {'type': 'integer'}, 'total_modules': {'type': 'integer'}}},
            'HealthResponse': {'type': 'object', 'required': ['status', 'database'], 'properties': {'status': {'type': 'string'}, 'database': {'type': 'string'}}},
            'MessageResponse': {'type': 'object', 'properties': {'message': {'type': 'string'}}},
            'WorkflowResponse': {'type': 'object', 'properties': {'message': {'type': 'string'}, 'data': {'type': 'object', 'additionalProperties': True}, 'shipment': {'type': 'object', 'additionalProperties': True}}},
            'AuthTokenResponse': {'type': 'object', 'properties': {'message': {'type': 'string'}, 'data': {'type': 'object', 'properties': {'id': {'type': 'integer'}, 'username': {'type': 'string'}, 'email': {'type': 'string'}, 'role': {'type': 'string'}, 'permissions': {'type': 'array', 'items': {'type': 'string'}}, 'all_warehouses': {'type': 'boolean'}, 'warehouse_ids': {'type': 'array', 'items': {'type': 'integer'}}, 'token': {'type': 'string'}, 'token_type': {'type': 'string'}, 'expires_in': {'type': 'integer'}, 'refresh_token': {'type': 'string'}, 'refresh_expires_in': {'type': 'integer'}}}}},
            'AuthProfileResponse': {'type': 'object', 'properties': {'data': {'type': 'object', 'properties': {'id': {'type': 'integer'}, 'username': {'type': 'string'}, 'email': {'type': 'string'}, 'role': {'type': 'string'}, 'permissions': {'type': 'array', 'items': {'type': 'string'}}, 'all_warehouses': {'type': 'boolean'}, 'warehouse_ids': {'type': 'array', 'items': {'type': 'integer'}}, 'is_active': {'type': 'boolean'}, 'created_at': {'type': ['string', 'null'], 'format': 'date-time'}}}, 'message': {'type': 'string'}}},
            'PartnerResponse': {'type': 'object', 'properties': {'data': {'$ref': '#/components/schemas/PartnerRecord'}, 'message': {'type': 'string'}}},
            'ProductResponse': {'type': 'object', 'properties': {'data': {'$ref': '#/components/schemas/ProductRecord'}, 'message': {'type': 'string'}}},
            'RoleListResponse': {'type': 'object', 'properties': {'data': {'type': 'array', 'items': {'type': 'object', 'properties': {'code': {'type': 'string'}, 'name': {'type': 'string'}, 'description': {'type': ['string', 'null']}, 'is_system': {'type': 'boolean'}, 'permissions': {'type': 'array', 'items': {'type': 'string'}}}}}}},
            'RoleResponse': {'type': 'object', 'properties': {'data': {'type': 'object', 'properties': {'code': {'type': 'string'}, 'name': {'type': 'string'}, 'description': {'type': ['string', 'null']}, 'is_system': {'type': 'boolean'}, 'permissions': {'type': 'array', 'items': {'type': 'string'}}}}, 'message': {'type': 'string'}}},
            'PermissionListResponse': {'type': 'object', 'properties': {'data': {'type': 'array', 'items': {'type': 'object', 'properties': {'code': {'type': 'string'}, 'name': {'type': 'string'}, 'module': {'type': 'string'}, 'action': {'type': 'string'}, 'warehouse_scoped': {'type': 'boolean'}}}}}},
            'UserListResponse': {'$ref': '#/components/schemas/PagedObjectResponse'},
            'ManagedUserResponse': {'type': 'object', 'properties': {'data': {'type': 'object', 'properties': {'id': {'type': 'integer'}, 'username': {'type': 'string'}, 'email': {'type': 'string'}, 'role': {'type': 'string'}, 'is_active': {'type': 'boolean'}, 'all_warehouses': {'type': 'boolean'}, 'warehouse_ids': {'type': 'array', 'items': {'type': 'integer'}}}}, 'message': {'type': 'string'}}},
            'SalesOrderResponse': {'type': 'object', 'properties': {'data': {'type': 'object', 'properties': {'id': {'type': 'integer'}, 'code': {'type': 'string'}, 'customer_id': {'type': 'integer'}, 'warehouse_id': {'type': 'integer'}, 'status': {'type': 'string'}, 'due_date': {'type': ['string', 'null'], 'format': 'date'}, 'total_amount': {'type': 'number'}, 'total_qty': {'type': 'number'}, 'remaining_qty': {'type': 'number'}, 'items': {'type': 'array', 'items': {'type': 'object', 'properties': {'id': {'type': 'integer'}, 'product_id': {'type': 'integer'}, 'quantity': {'type': 'number'}, 'unit_price': {'type': 'number'}, 'total_price': {'type': 'number'}}}}}}, 'message': {'type': 'string'}}},
            'ShipmentResponse': {'type': 'object', 'properties': {'data': {'type': 'object', 'properties': {'id': {'type': 'integer'}, 'code': {'type': 'string'}, 'sales_order_id': {'type': 'integer'}, 'status': {'type': 'string'}, 'shipped_at': {'type': ['string', 'null'], 'format': 'date-time'}, 'invoice_id': {'type': ['integer', 'null']}, 'items': {'type': 'array', 'items': {'type': 'object', 'properties': {'sales_order_item_id': {'type': 'integer'}, 'product_id': {'type': 'integer'}, 'product_name': {'type': 'string'}, 'quantity': {'type': 'number'}, 'unit_price': {'type': 'number'}}}}}}, 'message': {'type': 'string'}}},
            'InvoiceResponse': {'type': 'object', 'properties': {'data': {'type': 'object', 'properties': {'id': {'type': 'integer'}, 'code': {'type': 'string'}, 'shipment_id': {'type': 'integer'}, 'customer_id': {'type': 'integer'}, 'warehouse_id': {'type': 'integer'}, 'total_amount': {'type': 'number'}, 'amount_paid': {'type': 'number'}, 'balance_due': {'type': 'number'}, 'status': {'type': 'string'}, 'due_date': {'type': 'string', 'format': 'date'}}}, 'message': {'type': 'string'}}},
            'PaymentResponse': {'type': 'object', 'properties': {'data': {'type': 'object', 'properties': {'id': {'type': 'integer'}, 'customer_id': {'type': 'integer'}, 'amount': {'type': 'number'}, 'payment_method': {'type': 'string'}, 'payment_date': {'type': ['string', 'null'], 'format': 'date-time'}, 'status': {'type': 'string'}, 'allocations': {'type': 'array', 'items': {'type': 'object', 'properties': {'invoice_id': {'type': 'integer'}, 'amount': {'type': 'number'}}}}}}, 'message': {'type': 'string'}}},
            'PurchaseOrderResponse': {'type': 'object', 'properties': {'data': {'type': 'object', 'properties': {'id': {'type': 'integer'}, 'code': {'type': 'string'}, 'supplier_id': {'type': 'integer'}, 'warehouse_id': {'type': 'integer'}, 'status': {'type': 'string'}, 'order_date': {'type': 'string', 'format': 'date'}, 'total_amount': {'type': 'number'}, 'items': {'type': 'array', 'items': {'type': 'object', 'properties': {'product_id': {'type': 'integer'}, 'quantity': {'type': 'number'}, 'unit_cost': {'type': 'number'}}}}}}, 'message': {'type': 'string'}}},
            'GoodsReceiptResponse': {'type': 'object', 'properties': {'data': {'type': 'object', 'properties': {'id': {'type': 'integer'}, 'code': {'type': 'string'}, 'purchase_order_id': {'type': 'integer'}, 'status': {'type': 'string'}, 'received_date': {'type': 'string', 'format': 'date'}, 'items': {'type': 'array', 'items': {'type': 'object', 'properties': {'product_id': {'type': 'integer'}, 'quantity': {'type': 'number'}, 'unit_cost': {'type': 'number'}}}}}}, 'message': {'type': 'string'}}},
            'VendorBillResponse': {'type': 'object', 'properties': {'data': {'type': 'object', 'properties': {'id': {'type': 'integer'}, 'code': {'type': 'string'}, 'goods_receipt_id': {'type': 'integer'}, 'supplier_id': {'type': 'integer'}, 'total_amount': {'type': 'number'}, 'amount_paid': {'type': 'number'}, 'balance_due': {'type': 'number'}, 'status': {'type': 'string'}}}, 'message': {'type': 'string'}}},
            'SupplierPaymentResponse': {'type': 'object', 'properties': {'data': {'type': 'object', 'properties': {'id': {'type': 'integer'}, 'code': {'type': 'string'}, 'supplier_id': {'type': 'integer'}, 'source_vendor_bill_id': {'type': ['integer', 'null']}, 'amount': {'type': 'number'}, 'allocated_amount': {'type': 'number'}, 'unallocated_amount': {'type': 'number'}, 'payment_method': {'type': 'string'}, 'status': {'type': 'string'}}}, 'message': {'type': 'string'}}},
            'InventoryBalanceListResponse': {'$ref': '#/components/schemas/PagedObjectResponse'},
            'InventoryBalanceResponse': {'type': 'object', 'properties': {'data': {'type': 'object', 'properties': {'id': {'type': 'integer'}, 'product_id': {'type': 'integer'}, 'warehouse_id': {'type': 'integer'}, 'quantity_on_hand': {'type': 'number'}, 'quantity_reserved': {'type': 'number'}, 'average_cost': {'type': 'number'}}}, 'message': {'type': 'string'}}},
            'StockMovementResponse': {'type': 'object', 'required': ['data'], 'properties': {'data': {'type': 'object', 'properties': {'id': {'type': 'integer'}, 'product_id': {'type': 'integer'}, 'warehouse_id': {'type': 'integer'}, 'movement_type': {'type': 'string'}, 'quantity_delta': {'type': 'number'}, 'unit_cost': {'type': ['number', 'null']}, 'reference_type': {'type': ['string', 'null']}, 'reference_id': {'type': ['integer', 'null']}, 'created_at': {'type': ['string', 'null'], 'format': 'date-time'}}}}},
            'QuarantineListResponse': {'$ref': '#/components/schemas/PagedObjectResponse'},
            'UserProfilePatch': {'type': 'object', 'properties': {'username': {'type': 'string', 'minLength': 1, 'maxLength': 50}, 'email': {'type': 'string', 'format': 'email'}, 'current_password': {'type': 'string', 'format': 'password'}, 'new_password': {'type': 'string', 'minLength': 12, 'format': 'password'}, 'refresh_token': {'type': 'string'}}, 'additionalProperties': False},
            'PurchaseOrderPatch': {'type': 'object', 'properties': {'supplier_id': {'type': 'integer', 'minimum': 1}, 'warehouse_id': {'type': 'integer', 'minimum': 1}, 'order_date': {'type': 'string', 'format': 'date'}, 'notes': {'type': ['string', 'null']}, 'items': {'type': 'array', 'minItems': 1, 'items': {'type': 'object', 'required': ['product_id', 'quantity', 'unit_cost'], 'properties': {'product_id': {'type': 'integer', 'minimum': 1}, 'quantity': {'type': 'number', 'exclusiveMinimum': 0}, 'unit_cost': {'type': 'number', 'minimum': 0}}}}}},
            'SalesOrderListResponse': {'$ref': '#/components/schemas/PagedObjectResponse'},
            'ShipmentListResponse': {'$ref': '#/components/schemas/PagedObjectResponse'},
            'InvoiceListResponse': {'$ref': '#/components/schemas/PagedObjectResponse'},
            'PaymentListResponse': {'$ref': '#/components/schemas/PagedObjectResponse'},
            'PurchaseOrderListResponse': {'$ref': '#/components/schemas/PagedObjectResponse'},
            'GoodsReceiptListResponse': {'$ref': '#/components/schemas/PagedObjectResponse'},
            'VendorBillListResponse': {'$ref': '#/components/schemas/PagedObjectResponse'},
            'SupplierPaymentListResponse': {'$ref': '#/components/schemas/PagedObjectResponse'},
            'Login': {
                'type': 'object',
                'required': ['username', 'password'],
                'properties': {
                    'username': {'type': 'string'},
                    'password': {'type': 'string', 'format': 'password'},
                },
            },
            'RefreshToken': {
                'type': 'object',
                'required': ['refresh_token'],
                'properties': {
                    'refresh_token': {'type': 'string'},
                },
            },
            'JsonObject': {
                    'type': 'object',
                    'description': 'JSON object; see the operation and PRD for fields.',
                    'additionalProperties': True,
                },
            'ReportRow': {
                'type': 'object',
                'description': 'A report row. Fields vary by report and are listed in the endpoint response examples.',
                'additionalProperties': True,
            },
            'InventoryReportRow': {
                'type': 'object', 'required': ['product_id', 'sku', 'name', 'quantity_on_hand', 'quantity_reserved', 'quantity_available', 'inventory_value'],
                'properties': {
                    'product_id': {'type': 'integer'}, 'sku': {'type': 'string'}, 'name': {'type': 'string'},
                    'quantity_on_hand': {'type': 'number'}, 'quantity_reserved': {'type': 'number'},
                    'quantity_available': {'type': 'number'}, 'average_cost': {'type': 'number'},
                    'inventory_value': {'type': 'number'}, 'warehouse_count': {'type': 'integer'},
                }, 'additionalProperties': True,
            },
            'StockMovementReportRow': {
                'type': 'object', 'required': ['id', 'product_id', 'sku', 'product_name', 'warehouse_id', 'movement_type', 'quantity_delta', 'created_at'],
                'properties': {
                    'id': {'type': 'integer'}, 'product_id': {'type': 'integer'}, 'sku': {'type': 'string'},
                    'product_name': {'type': 'string'}, 'warehouse_id': {'type': 'integer'},
                    'warehouse_name': {'type': 'string'}, 'movement_type': {'type': 'string'},
                    'quantity_delta': {'type': 'number'}, 'unit_cost': {'type': 'number'},
                    'reference_type': {'type': ['string', 'null']}, 'reference_id': {'type': ['integer', 'null']},
                    'created_at': {'type': ['string', 'null'], 'format': 'date-time'},
                },
            },
            'SalesReportRow': {
                'type': 'object', 'required': ['id', 'code', 'customer_id', 'total_amount', 'balance_due', 'status', 'created_at'],
                'properties': {
                    'id': {'type': 'integer'}, 'code': {'type': 'string'}, 'customer_id': {'type': 'integer'},
                    'customer_name': {'type': 'string'}, 'warehouse_id': {'type': 'integer'},
                    'warehouse_name': {'type': 'string'}, 'total_amount': {'type': 'number'},
                    'amount_paid': {'type': 'number'}, 'balance_due': {'type': 'number'},
                    'status': {'type': 'string'}, 'due_date': {'type': 'string', 'format': 'date'},
                    'created_at': {'type': ['string', 'null'], 'format': 'date-time'},
                    'items': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': True}},
                }, 'additionalProperties': True,
            },
            'PurchasesReportRow': {
                'type': 'object', 'required': ['id', 'code', 'supplier_id', 'total_amount', 'balance_due', 'status', 'created_at'],
                'properties': {
                    'id': {'type': 'integer'}, 'code': {'type': 'string'}, 'supplier_id': {'type': 'integer'},
                    'supplier_name': {'type': 'string'}, 'warehouse_name': {'type': 'string'},
                    'total_amount': {'type': 'number'}, 'amount_paid': {'type': 'number'},
                    'balance_due': {'type': 'number'}, 'status': {'type': 'string'},
                    'created_at': {'type': ['string', 'null'], 'format': 'date-time'},
                }, 'additionalProperties': True,
            },
            'ReceivableRow': {
                'allOf': [
                    {'$ref': '#/components/schemas/SalesReportRow'},
                    {'type': 'object', 'required': ['overdue_days'], 'properties': {'overdue_days': {'type': 'integer'}}},
                ],
            },
            'PayableRow': {'$ref': '#/components/schemas/PurchasesReportRow'},
            'ReportPeriod': {
                'type': 'object',
                'properties': {
                    'from_date': {'type': ['string', 'null'], 'format': 'date'},
                    'to_date': {'type': ['string', 'null'], 'format': 'date'},
                },
            },
            'InventoryReportResponse': {
                'type': 'object', 'required': ['data', 'total', 'page', 'pages', 'total_inventory_value'],
                'properties': {
                    'data': {'type': 'array', 'items': {'$ref': '#/components/schemas/InventoryReportRow'}},
                    'total': {'type': 'integer'}, 'page': {'type': 'integer'}, 'pages': {'type': 'integer'},
                    'warehouse_id': {'type': ['integer', 'null']}, 'total_inventory_value': {'type': 'number'},
                },
            },
            'StockMovementReportResponse': {
                'type': 'object', 'required': ['data', 'total', 'page', 'pages', 'period'],
                'properties': {
                    'data': {'type': 'array', 'items': {'$ref': '#/components/schemas/StockMovementReportRow'}},
                    'total': {'type': 'integer'}, 'page': {'type': 'integer'}, 'pages': {'type': 'integer'},
                    'period': {'$ref': '#/components/schemas/ReportPeriod'},
                },
            },
            'SalesReportResponse': {
                'type': 'object', 'required': ['data', 'total', 'page', 'pages', 'period', 'total_sales_amount'],
                'properties': {
                    'data': {'type': 'array', 'items': {'$ref': '#/components/schemas/SalesReportRow'}},
                    'total': {'type': 'integer'}, 'page': {'type': 'integer'}, 'pages': {'type': 'integer'},
                    'period': {'$ref': '#/components/schemas/ReportPeriod'}, 'total_sales_amount': {'type': 'number'},
                },
            },
            'PurchasesReportResponse': {
                'type': 'object', 'required': ['data', 'total', 'page', 'pages', 'period', 'total_purchase_amount'],
                'properties': {
                    'data': {'type': 'array', 'items': {'$ref': '#/components/schemas/PurchasesReportRow'}},
                    'total': {'type': 'integer'}, 'page': {'type': 'integer'}, 'pages': {'type': 'integer'},
                    'period': {'$ref': '#/components/schemas/ReportPeriod'}, 'total_purchase_amount': {'type': 'number'},
                },
            },
            'ReceivablesResponse': {
                'type': 'object', 'required': ['data', 'total', 'page', 'pages', 'summary'],
                'properties': {
                    'data': {'type': 'array', 'items': {'$ref': '#/components/schemas/ReceivableRow'}},
                    'total': {'type': 'integer'}, 'page': {'type': 'integer'}, 'pages': {'type': 'integer'},
                    'as_of_date': {'type': 'string', 'format': 'date'}, 'summary': {'type': 'object'},
                },
            },
            'PayablesResponse': {
                'type': 'object', 'required': ['data', 'total', 'page', 'pages', 'summary'],
                'properties': {
                    'data': {'type': 'array', 'items': {'$ref': '#/components/schemas/PayableRow'}},
                    'total': {'type': 'integer'}, 'page': {'type': 'integer'}, 'pages': {'type': 'integer'},
                    'summary': {'type': 'object', 'properties': {'outstanding_amount': {'type': 'number'}}},
                },
            },
            'TransferResponse': {'type': 'object', 'properties': {'data': {'type': 'object', 'additionalProperties': True}, 'message': {'type': 'string'}}},
            'TransferListResponse': {'type': 'object', 'properties': {'data': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': True}}, 'total': {'type': 'integer'}, 'page': {'type': 'integer'}, 'pages': {'type': 'integer'}}},
            'AdjustmentResponse': {'type': 'object', 'properties': {'data': {'type': 'object', 'additionalProperties': True}, 'message': {'type': 'string'}}},
            'AdjustmentListResponse': {'type': 'object', 'properties': {'data': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': True}}, 'total': {'type': 'integer'}, 'page': {'type': 'integer'}, 'pages': {'type': 'integer'}}},
            'SalesReturnResponse': {'type': 'object', 'properties': {'data': {'type': 'object', 'additionalProperties': True}, 'message': {'type': 'string'}}},
            'SalesReturnListResponse': {'type': 'object', 'properties': {'data': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': True}}, 'total': {'type': 'integer'}, 'page': {'type': 'integer'}, 'pages': {'type': 'integer'}}},
            'ProductInput': {
                'type': 'object',
                'required': ['sku', 'name'],
                'properties': {
                    'sku': {'type': 'string', 'maxLength': 50},
                    'name': {'type': 'string', 'maxLength': 100},
                    'category_id': {'type': ['integer', 'null']},
                    'unit_id': {'type': ['integer', 'null']},
                    'sales_price': {'type': ['number', 'null'], 'minimum': 0},
                    'min_stock': {'type': 'number', 'minimum': 0},
                },
            },
            'ProductPatch': {
                'type': 'object',
                'properties': {
                    'sku': {'type': 'string', 'maxLength': 50},
                    'name': {'type': 'string', 'maxLength': 100},
                    'category_id': {'type': ['integer', 'null']},
                    'unit_id': {'type': ['integer', 'null']},
                    'sales_price': {'type': ['number', 'null'], 'minimum': 0},
                    'min_stock': {'type': 'number', 'minimum': 0},
                },
            },
            'CategoryInput': {
                'type': 'object',
                'required': ['name'],
                'properties': {
                    'name': {'type': 'string'},
                    'description': {'type': 'string'},
                },
            },
            'CategoryPatch': {
                'type': 'object',
                'properties': {
                    'name': {'type': 'string'},
                    'description': {'type': 'string'},
                },
            },
            'UnitInput': {
                'type': 'object',
                'required': ['name'],
                'properties': {
                    'name': {'type': 'string'},
                    'symbol': {'type': 'string'},
                },
            },
            'UnitPatch': {
                'type': 'object',
                'properties': {
                    'name': {'type': 'string'},
                    'symbol': {'type': 'string'},
                },
            },
            'WarehouseInput': {
                'type': 'object',
                'required': ['code', 'name'],
                'properties': {
                    'code': {'type': 'string', 'maxLength': 10},
                    'name': {'type': 'string', 'maxLength': 50},
                    'address': {'type': 'string'},
                },
            },
            'WarehousePatch': {
                'type': 'object',
                'properties': {
                    'code': {'type': 'string', 'maxLength': 10},
                    'name': {'type': 'string', 'maxLength': 50},
                    'address': {'type': 'string'},
                },
            },
            'PartnerInput': {
                'type': 'object',
                'required': ['name'],
                'properties': {
                    'name': {'type': 'string'},
                    'email': {'type': 'string', 'format': 'email'},
                    'phone': {'type': 'string'},
                    'address': {'type': 'string'},
                },
            },
            'PartnerPatch': {
                'type': 'object',
                'properties': {
                    'name': {'type': 'string'},
                    'email': {'type': 'string', 'format': 'email'},
                    'phone': {'type': 'string'},
                    'address': {'type': 'string'},
                },
            },
            'InventoryBalanceInput': {
                'type': 'object',
                'required': ['product_id', 'warehouse_id'],
                'properties': {
                    'product_id': {'type': 'integer'},
                    'warehouse_id': {'type': 'integer'},
                    'quantity_on_hand': {'type': 'number', 'minimum': 0},
                    'average_cost': {'type': 'number', 'minimum': 0},
                },
            },
            'InventoryAdjustmentInput': {
                'type': 'object',
                'required': ['inventory_balance_id', 'adjustment_type', 'quantity'],
                'properties': {
                    'inventory_balance_id': {'type': 'integer'},
                    'adjustment_type': {'type': 'string', 'enum': ['ADD', 'REDUCE']},
                    'quantity': {'type': 'number', 'exclusiveMinimum': 0},
                    'description': {'type': 'string'},
                },
            },
            'StockTransferCreate': {
                'type': 'object',
                'required': [
                    'source_warehouse_id', 'destination_warehouse_id',
                    'reason', 'items',
                ],
                'properties': {
                    'source_warehouse_id': {'type': 'integer'},
                    'destination_warehouse_id': {'type': 'integer'},
                    'reason': {'type': 'string', 'minLength': 1},
                    'items': {
                        'type': 'array',
                        'minItems': 1,
                        'items': {
                            'type': 'object',
                            'required': ['product_id', 'quantity'],
                            'properties': {
                                'product_id': {'type': 'integer'},
                                'quantity': {'type': 'number', 'exclusiveMinimum': 0},
                            },
                        },
                    },
                },
            },
                'Error': {
                    'type': 'object',
                    'required': ['error'],
                    'properties': {'error': {'type': 'string'}},
                },
                'SalesOrderItemInput': {
                    'type': 'object',
                    'required': ['product_id', 'quantity'],
                    'properties': {
                        'product_id': {'type': 'integer'},
                        'quantity': {'type': 'number', 'exclusiveMinimum': 0},
                        'unit_price': {
                            'type': 'number',
                            'minimum': 0,
                            'description': 'Selling price per unit. When omitted, the product catalog price is used; older products without a catalog price fall back to average inventory cost.',
                        },
                    },
                },
                'SalesOrderCreate': {
                    'type': 'object',
                    'required': ['customer_id', 'warehouse_id', 'due_date', 'items'],
                    'properties': {
                        'customer_id': {'type': 'integer'},
                        'warehouse_id': {'type': 'integer'},
                        'due_date': {'type': 'string', 'format': 'date'},
                        'notes': {'type': 'string'},
                        'items': {
                            'type': 'array',
                            'items': {'$ref': '#/components/schemas/SalesOrderItemInput'},
                        },
                    },
                },
                'ShipmentCreate': {
                    'type': 'object',
                    'required': ['sales_order_id', 'items'],
                    'properties': {
                        'sales_order_id': {'type': 'integer'},
                        'items': {
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'required': ['sales_order_item_id', 'quantity'],
                                'properties': {
                                    'sales_order_item_id': {'type': 'integer'},
                                    'quantity': {'type': 'number', 'exclusiveMinimum': 0},
                                },
                            },
                        },
                    },
                },
                'ShipmentItemsCreate': {
                    'type': 'object',
                    'required': ['items'],
                    'properties': {
                        'items': {
                            'type': 'array',
                            'minItems': 1,
                            'items': {
                                'type': 'object',
                                'required': ['sales_order_item_id', 'quantity'],
                                'properties': {
                                    'sales_order_item_id': {'type': 'integer'},
                                    'quantity': {'type': 'number', 'exclusiveMinimum': 0},
                                },
                            },
                        },
                    },
                },
                'SalesInvoiceCreate': {
                    'type': 'object',
                    'required': ['shipment_id'],
                    'properties': {'shipment_id': {'type': 'integer'}},
                },
                'SalesReturnCreate': {
                    'type': 'object',
                    'required': ['shipment_id', 'reason', 'items'],
                    'properties': {
                        'shipment_id': {'type': 'integer'},
                        'reason': {'type': 'string', 'minLength': 1},
                        'items': {
                            'type': 'array',
                            'minItems': 1,
                            'items': {
                                'type': 'object',
                                'required': ['shipment_item_id', 'quantity', 'condition'],
                                'properties': {
                                    'shipment_item_id': {'type': 'integer'},
                                    'quantity': {'type': 'number', 'exclusiveMinimum': 0},
                                    'condition': {
                                        'type': 'string',
                                        'enum': ['RESTOCK', 'DAMAGED'],
                                    },
                                },
                            },
                        },
                    },
                },
                'PurchaseOrderCreate': {
                    'type': 'object',
                    'required': ['supplier_id', 'warehouse_id', 'items'],
                    'properties': {
                        'supplier_id': {'type': 'integer'},
                        'warehouse_id': {'type': 'integer'},
                        'order_date': {'type': 'string', 'format': 'date'},
                        'notes': {'type': 'string'},
                        'items': {
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'required': ['product_id', 'quantity', 'unit_cost'],
                                'properties': {
                                    'product_id': {'type': 'integer'},
                                    'quantity': {'type': 'number', 'exclusiveMinimum': 0},
                                    'unit_cost': {'type': 'number', 'minimum': 0},
                                },
                            },
                        },
                    },
                },
                'GoodsReceiptCreate': {
                    'type': 'object',
                    'required': ['purchase_order_id', 'items'],
                    'properties': {
                        'purchase_order_id': {'type': 'integer'},
                        'received_date': {'type': 'string', 'format': 'date'},
                        'notes': {'type': 'string'},
                        'items': {
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'required': ['purchase_order_item_id', 'quantity'],
                                'properties': {
                                    'purchase_order_item_id': {'type': 'integer'},
                                    'quantity': {'type': 'number', 'exclusiveMinimum': 0},
                                },
                            },
                        },
                    },
                },
                'CustomerPaymentPostNow': {
                    'type': 'object',
                    'required': ['invoice_id', 'amount'],
                    'properties': {
                        'invoice_id': {'type': 'integer'},
                        'amount': {'type': 'number', 'exclusiveMinimum': 0},
                        'payment_method': {'type': 'string', 'enum': ['CASH', 'BANK_TRANSFER', 'CREDIT_CARD']},
                        'warehouse_id': {'type': 'integer'},
                    },
                },
                'SupplierPaymentPostNow': {
                    'type': 'object',
                    'required': ['vendor_bill_id', 'amount'],
                    'properties': {
                        'vendor_bill_id': {'type': 'integer'},
                        'amount': {'type': 'number', 'exclusiveMinimum': 0},
                        'payment_method': {'type': 'string', 'enum': ['CASH', 'BANK_TRANSFER', 'CREDIT_CARD']},
                        'warehouse_id': {'type': 'integer'},
                    },
                },
                'VendorBillCreate': {
                    'type': 'object',
                    'required': ['goods_receipt_id'],
                    'properties': {'goods_receipt_id': {'type': 'integer'}},
                },
                'CustomerPaymentCreate': {
                    'type': 'object',
                    'required': ['amount', 'payment_method'],
                    'anyOf': [
                        {'required': ['customer_id']},
                        {'required': ['invoice_id']},
                    ],
                    'properties': {
                        'customer_id': {'type': 'integer'},
                        'invoice_id': {'type': 'integer', 'description': 'Optional source invoice; its warehouse scope is enforced.'},
                        'warehouse_id': {'type': 'integer', 'description': 'Warehouse scope for a draft payment before invoice allocation.'},
                        'amount': {'type': 'number', 'exclusiveMinimum': 0},
                        'payment_method': {'type': 'string'},
                        'payment_date': {'type': 'string', 'format': 'date-time'},
                    },
                },
                'SupplierPaymentCreate': {
                    'type': 'object',
                    'required': ['supplier_id', 'amount', 'payment_method'],
                    'properties': {
                        'supplier_id': {'type': 'integer'},
                        'vendor_bill_id': {'type': 'integer', 'description': 'Optional source bill used to retain warehouse scope for a draft payment.'},
                        'warehouse_id': {'type': 'integer', 'description': 'Warehouse scope for a draft payment before vendor-bill allocation.'},
                        'amount': {'type': 'number', 'exclusiveMinimum': 0},
                        'payment_method': {'type': 'string'},
                        'payment_date': {'type': 'string', 'format': 'date-time'},
                    },
                },
                'CustomerPaymentAllocations': {
                    'type': 'object',
                    'required': ['allocations'],
                    'properties': {
                        'allocations': {
                            'type': 'array',
                            'minItems': 1,
                            'items': {
                                'type': 'object',
                                'required': ['invoice_id', 'amount'],
                                'properties': {
                                    'invoice_id': {'type': 'integer'},
                                    'amount': {'type': 'number', 'exclusiveMinimum': 0},
                                },
                            },
                        },
                    },
                },
                'SupplierPaymentAllocations': {
                    'type': 'object',
                    'required': ['allocations'],
                    'properties': {
                        'allocations': {
                            'type': 'array',
                            'minItems': 1,
                            'items': {
                                'type': 'object',
                                'required': ['vendor_bill_id', 'amount'],
                                'properties': {
                                    'vendor_bill_id': {'type': 'integer'},
                                    'amount': {'type': 'number', 'exclusiveMinimum': 0},
                                },
                            },
                        },
                    },
                },
                'ManagedUserCreate': {
                    'type': 'object',
                    'required': ['username', 'email', 'password', 'role'],
                    'properties': {
                        'username': {'type': 'string', 'maxLength': 50},
                        'email': {'type': 'string', 'format': 'email', 'maxLength': 100},
                        'password': {
                            'type': 'string', 'format': 'password', 'minLength': 12,
                        },
                        'role': {'type': 'string'},
                        'all_warehouses': {'type': 'boolean', 'default': False},
                        'warehouse_ids': {
                            'type': 'array',
                            'items': {'type': 'integer'},
                        },
                    },
                },
                'ManagedUserPatch': {
                    'type': 'object',
                    'properties': {
                        'role': {'type': 'string'},
                        'is_active': {'type': 'boolean'},
                        'password': {'type': 'string', 'format': 'password', 'minLength': 12},
                        'all_warehouses': {'type': 'boolean'},
                        'warehouse_ids': {
                            'type': 'array',
                            'items': {'type': 'integer'},
                        },
                    },
                },
                'RoleCreate': {
                    'type': 'object',
                    'required': ['code', 'name'],
                    'properties': {
                        'code': {'type': 'string', 'pattern': '^[a-z][a-z0-9_-]{1,19}$'},
                        'name': {'type': 'string', 'maxLength': 80},
                        'description': {'type': 'string', 'maxLength': 255},
                    },
                },
                'RolePermissionsReplace': {
                    'type': 'object',
                    'required': ['permissions'],
                    'properties': {
                        'permissions': {
                            'type': 'array',
                            'items': {'type': 'string'},
                        },
                    },
                },
            },
            'responses': {
                'BadRequest': {
                    'description': 'Invalid request data.',
                    'content': {'application/json': {'schema': {'$ref': '#/components/schemas/Error'}}},
                },
                'Unauthorized': {
                    'description': 'Authentication is required or the token is invalid.',
                    'content': {'application/json': {'schema': {'$ref': '#/components/schemas/Error'}}},
                },
                'Forbidden': {
                    'description': 'The caller lacks permission or warehouse scope.',
                    'content': {'application/json': {'schema': {'$ref': '#/components/schemas/Error'}}},
                },
                'NotFound': {
                    'description': 'The requested resource was not found.',
                    'content': {'application/json': {'schema': {'$ref': '#/components/schemas/Error'}}},
                },
                'Conflict': {
                    'description': 'The operation conflicts with the current resource state.',
                    'content': {'application/json': {'schema': {'$ref': '#/components/schemas/Error'}}},
                },
                'ServerError': {
                    'description': 'The server could not complete the operation.',
                    'content': {'application/json': {'schema': {'$ref': '#/components/schemas/Error'}}},
                },
            },
        },
    }
