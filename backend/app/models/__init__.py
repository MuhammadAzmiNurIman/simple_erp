"""Public model exports, grouped internally by business domain."""

from .catalog import Category, Product, Unit, Warehouse
from .identity import (
    AuditLog, Permission, RevokedToken, Role, RoleDefaultPermission,
    RolePermissionOverride, User, UserWarehouseAccess,
    role_permissions,
)
from .inventory import (
    InventoryAdjuster, InventoryBalance, InventoryQuarantine,
    InventoryQuarantineAction, StockMovement, StockTransfer, StockTransferItem,
)
from .partners import Customer, Supplier
from .purchasing import (
    GoodsReceipt, GoodsReceiptItem, PurchaseOrder, PurchaseOrderItem,
    SupplierPayment, SupplierPaymentAllocation, VendorBill,
)
from .sales import (
    CustomerPaymentAllocation, Invoice, Payment, SalesOrder, SalesOrderItem,
    SalesReturn, SalesReturnItem, Shipment, ShipmentItem,
)
# Keep the domain models available through ``from app.models import ...``.
__all__ = [
    'Category', 'Unit', 'Product', 'Warehouse', 'InventoryBalance',
    'StockMovement', 'Customer', 'SalesOrder', 'SalesOrderItem',
    'InventoryAdjuster', 'InventoryQuarantine', 'InventoryQuarantineAction',
    'User', 'Supplier', 'PurchaseOrder',
    'PurchaseOrderItem', 'Invoice', 'Payment', 'GoodsReceipt',
    'GoodsReceiptItem', 'VendorBill', 'SupplierPayment',
    'SupplierPaymentAllocation', 'Shipment', 'ShipmentItem',
    'CustomerPaymentAllocation', 'SalesReturn', 'SalesReturnItem', 'Role', 'Permission',
    'UserWarehouseAccess', 'AuditLog', 'RevokedToken', 'role_permissions',
    'RolePermissionOverride', 'RoleDefaultPermission',
    'StockTransfer', 'StockTransferItem',
]
