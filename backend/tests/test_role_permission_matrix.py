"""Comprehensive Role & Permission Matrix tests (RBAC & Warehouse Scoping)."""
import pytest
from app import db
from app.models import (
    Customer,
    GoodsReceipt,
    GoodsReceiptItem,
    InventoryAdjuster,
    InventoryBalance,
    Product,
    PurchaseOrder,
    PurchaseOrderItem,
    Role,
    SalesOrder,
    SalesOrderItem,
    Shipment,
    StockTransfer,
    StockTransferItem,
    Supplier,
    User,
    UserWarehouseAccess,
    Warehouse,
)
from app.routes.identity.auth import generate_token


def make_user(app, username, role, warehouse_ids=None, all_warehouses=True):
    """Helper to create and authenticate a user with specific role and warehouse access."""
    with app.app_context():
        user = User(
            username=username,
            email=f"{username}@testcorp.com",
            role=role,
            all_warehouses=all_warehouses,
            is_active=True,
        )
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

        if warehouse_ids:
            for wid in warehouse_ids:
                db.session.add(UserWarehouseAccess(user_id=user.id, warehouse_id=wid))
            db.session.commit()

        token = generate_token(user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def base_data(client, app):
    """Seed foundational master data for permission testing."""
    with app.app_context():
        wh1 = Warehouse(code="WH-ALPHA", name="Alpha Warehouse", is_active=True)
        wh2 = Warehouse(code="WH-BETA", name="Beta Warehouse", is_active=True)
        cust = Customer(name="Global Customer", email="cust@test.com", is_active=True)
        sup = Supplier(code="SUP-001", name="Global Supplier", email="sup@test.com", is_active=True)
        p1 = Product(sku="SKU-ITEM-1", name="Product Alpha", is_active=True)
        p2 = Product(sku="SKU-ITEM-2", name="Product Beta", is_active=True)
        db.session.add_all([wh1, wh2, cust, sup, p1, p2])
        db.session.commit()

        b1 = InventoryBalance(product_id=p1.id, warehouse_id=wh1.id, quantity_on_hand=100, average_cost=10.0)
        b2 = InventoryBalance(product_id=p2.id, warehouse_id=wh2.id, quantity_on_hand=50, average_cost=20.0)
        db.session.add_all([b1, b2])
        db.session.commit()

        return {
            "wh1_id": wh1.id,
            "wh2_id": wh2.id,
            "cust_id": cust.id,
            "sup_id": sup.id,
            "p1_id": p1.id,
            "p2_id": p2.id,
            "b1_id": b1.id,
            "b2_id": b2.id,
        }


def test_admin_has_full_module_access_and_can_manage_users(client, app, base_data):
    """Admin can manage access and operate across all ERP modules."""
    admin_hdr = make_user(app, "admin_user", "admin", all_warehouses=True)

    # Admin CAN manage users
    res_user = client.post(
        "/api/v1/users",
        headers=admin_hdr,
        json={
            "username": "sub_operator",
            "email": "sub_op@testcorp.com",
            "password": "Password123!",
            "role": "warehouse",
            "warehouse_ids": [base_data["wh1_id"], base_data["wh2_id"]],
        },
    )
    assert res_user.status_code == 201

    # Admin CAN read audit logs
    res_audit = client.get("/api/v1/audit-logs", headers=admin_hdr)
    assert res_audit.status_code == 200

    # Admin CAN create sales orders and purchase orders.
    res_so = client.post(
        "/api/v1/sales-orders",
        headers=admin_hdr,
        json={
            "customer_id": base_data["cust_id"],
            "warehouse_id": base_data["wh1_id"],
            "due_date": "2026-12-31",
            "items": [{"product_id": base_data["p1_id"], "quantity": 1}],
        },
    )
    assert res_so.status_code == 201

    res_po = client.post(
        "/api/v1/purchase-orders",
        headers=admin_hdr,
        json={
            "supplier_id": base_data["sup_id"],
            "warehouse_id": base_data["wh1_id"],
            "items": [{"product_id": base_data["p1_id"], "quantity": 1, "unit_cost": 10.0}],
        },
    )
    assert res_po.status_code == 201

    assert client.get("/api/v1/inventory/balances", headers=admin_hdr).status_code == 200
    assert client.get("/api/v1/finance/cash-summary", headers=admin_hdr).status_code == 200


def test_scoped_sales_order_list_defaults_to_assigned_warehouses(client, app, base_data):
    first = client.post('/api/v1/sales-orders', json={
        'customer_id': base_data['cust_id'],
        'warehouse_id': base_data['wh1_id'],
        'due_date': '2026-12-31',
        'items': [{'product_id': base_data['p1_id'], 'quantity': 1}],
    })
    second = client.post('/api/v1/sales-orders', json={
        'customer_id': base_data['cust_id'],
        'warehouse_id': base_data['wh2_id'],
        'due_date': '2026-12-31',
        'items': [{'product_id': base_data['p2_id'], 'quantity': 1}],
    })
    assert first.status_code == second.status_code == 201

    sales_headers = make_user(
        app,
        'scoped-sales-list',
        'sales',
        warehouse_ids=[base_data['wh1_id']],
        all_warehouses=False,
    )
    response = client.get('/api/v1/sales-orders', headers=sales_headers)
    assert response.status_code == 200
    assert response.get_json()['total'] == 1
    assert response.get_json()['data'][0]['warehouse_id'] == base_data['wh1_id']
    assert client.get(
        f"/api/v1/sales-orders?warehouse_id={base_data['wh2_id']}",
        headers=sales_headers,
    ).status_code == 403


def test_purchasing_role_boundaries(client, app, base_data):
    """Purchasing role can create/submit POs, but cannot approve POs or post stock."""
    purch_hdr = make_user(app, "purch_user", "purchasing", all_warehouses=True)

    # Purchasing CAN create PO
    res_po = client.post(
        "/api/v1/purchase-orders",
        headers=purch_hdr,
        json={
            "supplier_id": base_data["sup_id"],
            "warehouse_id": base_data["wh1_id"],
            "items": [{"product_id": base_data["p1_id"], "quantity": 10, "unit_cost": 12.0}],
        },
    )
    assert res_po.status_code == 201
    po_id = res_po.get_json()["data"]["id"]

    # Purchasing CAN submit PO
    assert client.post(f"/api/v1/purchase-orders/{po_id}/submit", headers=purch_hdr).status_code == 200

    # Purchasing CANNOT approve PO (requires manager)
    assert client.post(f"/api/v1/purchase-orders/{po_id}/approve", headers=purch_hdr).status_code == 403

    # Purchasing CANNOT create sales orders
    assert client.post(
        "/api/v1/sales-orders",
        headers=purch_hdr,
        json={
            "customer_id": base_data["cust_id"],
            "warehouse_id": base_data["wh1_id"],
            "due_date": "2026-12-31",
            "items": [{"product_id": base_data["p1_id"], "quantity": 1}],
        },
    ).status_code == 403

    # Purchasing CANNOT manage users
    assert client.post("/api/v1/users", headers=purch_hdr, json={"username": "hacker"}).status_code == 403


def test_warehouse_role_boundaries(client, app, base_data):
    """Warehouse role handles inventory receiving & shipping, but cannot create POs or SOs."""
    wh_hdr = make_user(app, "wh_user", "warehouse", all_warehouses=True)

    # Warehouse CAN create stock transfers
    res_tr = client.post(
        "/api/v1/inventory/transfers",
        headers=wh_hdr,
        json={
            "source_warehouse_id": base_data["wh1_id"],
            "destination_warehouse_id": base_data["wh2_id"],
            "reason": "Replenish WH2",
            "items": [{"product_id": base_data["p1_id"], "quantity": 5}],
        },
    )
    assert res_tr.status_code == 201

    # Warehouse CANNOT create POs
    assert client.post(
        "/api/v1/purchase-orders",
        headers=wh_hdr,
        json={
            "supplier_id": base_data["sup_id"],
            "warehouse_id": base_data["wh1_id"],
            "items": [{"product_id": base_data["p1_id"], "quantity": 1, "unit_cost": 10.0}],
        },
    ).status_code == 403

    # Warehouse CANNOT create SOs
    assert client.post(
        "/api/v1/sales-orders",
        headers=wh_hdr,
        json={
            "customer_id": base_data["cust_id"],
            "warehouse_id": base_data["wh1_id"],
            "due_date": "2026-12-31",
            "items": [{"product_id": base_data["p1_id"], "quantity": 1}],
        },
    ).status_code == 403

    # Warehouse CANNOT create customer payments
    assert client.post(
        "/api/v1/customer-payments",
        headers=wh_hdr,
        json={"customer_id": base_data["cust_id"], "amount": 100.0, "payment_method": "BANK_TRANSFER"},
    ).status_code == 403


def test_sales_role_boundaries(client, app, base_data):
    """Sales role manages sales orders, but cannot ship products or issue invoices."""
    sales_hdr = make_user(app, "sales_user", "sales", all_warehouses=True)

    # Sales CAN create sales orders
    res_so = client.post(
        "/api/v1/sales-orders",
        headers=sales_hdr,
        json={
            "customer_id": base_data["cust_id"],
            "warehouse_id": base_data["wh1_id"],
            "due_date": "2026-12-31",
            "items": [{"product_id": base_data["p1_id"], "quantity": 2}],
        },
    )
    assert res_so.status_code == 201
    so_id = res_so.get_json()["data"]["id"]

    # Sales CAN cancel sales orders
    assert client.post(f"/api/v1/sales-orders/{so_id}/cancel", headers=sales_hdr).status_code == 200

    # Sales CANNOT post shipments
    assert client.post(f"/api/v1/sales-orders/{so_id}/shipment", headers=sales_hdr).status_code == 403
    assert client.post("/api/v1/shipments/1/post", headers=sales_hdr).status_code == 403

    # Sales CANNOT create invoices
    assert client.post(f"/api/v1/sales-orders/{so_id}/invoice", headers=sales_hdr).status_code == 403

    # Sales CANNOT create POs
    assert client.post(
        "/api/v1/purchase-orders",
        headers=sales_hdr,
        json={"supplier_id": base_data["sup_id"], "warehouse_id": base_data["wh1_id"], "items": []},
    ).status_code == 403


def test_finance_role_boundaries(client, app, base_data):
    """Finance role manages invoices, payments, and financial reports, but cannot mutate inventory."""
    fin_hdr = make_user(app, "fin_user", "finance", all_warehouses=True)

    # Finance CAN create customer payment drafts
    res_pay = client.post(
        "/api/v1/customer-payments",
        headers=fin_hdr,
        json={
            "customer_id": base_data["cust_id"],
            "amount": 250.0,
            "payment_method": "BANK_TRANSFER",
            "payment_date": "2026-10-26",
        },
    )
    assert res_pay.status_code == 201

    # Finance CAN read finance cash summary
    assert client.get("/api/v1/finance/cash-summary", headers=fin_hdr).status_code == 200
    assert client.get("/api/v1/finance/receivables", headers=fin_hdr).status_code == 200

    # Finance CANNOT create sales orders
    assert client.post(
        "/api/v1/sales-orders",
        headers=fin_hdr,
        json={"customer_id": base_data["cust_id"], "warehouse_id": base_data["wh1_id"], "items": []},
    ).status_code == 403

    # Finance CANNOT create purchase orders
    assert client.post(
        "/api/v1/purchase-orders",
        headers=fin_hdr,
        json={"supplier_id": base_data["sup_id"], "warehouse_id": base_data["wh1_id"], "items": []},
    ).status_code == 403

    # Finance CANNOT post shipments
    assert client.post("/api/v1/shipments/1/post", headers=fin_hdr).status_code == 403


def test_manager_role_boundaries(client, app, base_data):
    """Manager approves orders and views reports, but cannot create basic orders or post stock."""
    mgr_hdr = make_user(app, "mgr_user", "manager", all_warehouses=True)

    # Manager CAN read reports and cash summary
    assert client.get("/api/v1/reports/sales", headers=mgr_hdr).status_code == 200
    assert client.get("/api/v1/reports/inventory", headers=mgr_hdr).status_code == 200
    assert client.get("/api/v1/finance/cash-summary", headers=mgr_hdr).status_code == 200
    assert client.get("/api/v1/purchase-orders", headers=mgr_hdr).status_code == 200
    assert client.get("/api/v1/goods-receipts", headers=mgr_hdr).status_code == 200

    # Manager CANNOT create purchase orders
    assert client.post(
        "/api/v1/purchase-orders",
        headers=mgr_hdr,
        json={"supplier_id": base_data["sup_id"], "warehouse_id": base_data["wh1_id"], "items": []},
    ).status_code == 403

    # Manager CANNOT create sales orders
    assert client.post(
        "/api/v1/sales-orders",
        headers=mgr_hdr,
        json={"customer_id": base_data["cust_id"], "warehouse_id": base_data["wh1_id"], "items": []},
    ).status_code == 403

    # Manager CANNOT post shipments
    assert client.post("/api/v1/shipments/1/post", headers=mgr_hdr).status_code == 403

    # Manager CANNOT manage users
    assert client.post("/api/v1/users", headers=mgr_hdr, json={"username": "new_guy"}).status_code == 403


def test_viewer_role_is_strictly_read_only(client, app, base_data):
    """Viewer can read data across modules but is strictly prohibited from any state changes."""
    view_hdr = make_user(app, "viewer_user", "viewer", all_warehouses=True)

    # Viewer CAN read
    assert client.get("/api/v1/products", headers=view_hdr).status_code == 200
    assert client.get("/api/v1/sales-orders", headers=view_hdr).status_code == 200
    assert client.get("/api/v1/purchase-orders", headers=view_hdr).status_code == 200
    assert client.get("/api/v1/inventory/balances", headers=view_hdr).status_code == 200
    assert client.get("/api/v1/reports/inventory", headers=view_hdr).status_code == 200

    # Viewer CANNOT mutate
    assert client.post("/api/v1/products", headers=view_hdr, json={"sku": "NEW", "name": "NEW"}).status_code == 403
    assert client.post(
        "/api/v1/sales-orders",
        headers=view_hdr,
        json={"customer_id": base_data["cust_id"], "warehouse_id": base_data["wh1_id"], "items": []},
    ).status_code == 403
    assert client.post(
        "/api/v1/purchase-orders",
        headers=view_hdr,
        json={"supplier_id": base_data["sup_id"], "warehouse_id": base_data["wh1_id"], "items": []},
    ).status_code == 403
    assert client.post("/api/v1/customer-payments", headers=view_hdr, json={"amount": 50}).status_code == 403


def test_warehouse_scoping_prevents_unauthorized_cross_warehouse_access(client, app, base_data):
    """Users with single-warehouse access are strictly denied access to other warehouses."""
    # User only has access to WH1 (Alpha)
    wh1_user_hdr = make_user(
        app,
        "operator_wh1",
        "operator",
        warehouse_ids=[base_data["wh1_id"]],
        all_warehouses=False,
    )

    # Accessing WH1 balance is permitted
    res_wh1 = client.get(
        f"/api/v1/inventory/balances?warehouse_id={base_data['wh1_id']}",
        headers=wh1_user_hdr,
    )
    assert res_wh1.status_code == 200

    # Accessing WH2 balance is DENIED (403)
    res_wh2 = client.get(
        f"/api/v1/inventory/balances?warehouse_id={base_data['wh2_id']}",
        headers=wh1_user_hdr,
    )
    assert res_wh2.status_code == 403

    # Creating Sales Order for WH2 is DENIED (403)
    res_so_wh2 = client.post(
        "/api/v1/sales-orders",
        headers=wh1_user_hdr,
        json={
            "customer_id": base_data["cust_id"],
            "warehouse_id": base_data["wh2_id"],
            "due_date": "2026-12-31",
            "items": [{"product_id": base_data["p2_id"], "quantity": 1}],
        },
    )
    assert res_so_wh2.status_code == 403

    # Creating Transfer involving unauthorized destination (WH2) is DENIED (403)
    res_tr = client.post(
        "/api/v1/inventory/transfers",
        headers=wh1_user_hdr,
        json={
            "source_warehouse_id": base_data["wh1_id"],
            "destination_warehouse_id": base_data["wh2_id"],
            "reason": "Illicit Transfer",
            "items": [{"product_id": base_data["p1_id"], "quantity": 1}],
        },
    )
    assert res_tr.status_code == 403

    # Spoofing check: Sending target resource from WH2 while passing allowed WH1 in query is DENIED
    res_spoof = client.get(
        f"/api/v1/inventory/balances/{base_data['b2_id']}?warehouse_id={base_data['wh1_id']}",
        headers=wh1_user_hdr,
    )
    assert res_spoof.status_code == 403


def test_maker_checker_segregation_of_duties(client, app, base_data):
    """Creator of a transfer or adjustment cannot approve or review their own transaction."""
    # Admin has the create/review permissions needed to isolate maker-checker
    # behavior from each operational role's narrower permission grants.
    creator_hdr = make_user(app, "creator_user", "admin", all_warehouses=True)
    checker_hdr = make_user(app, "checker_user", "admin", all_warehouses=True)

    # 1. Stock Transfer Maker-Checker
    tr_res = client.post(
        "/api/v1/inventory/transfers",
        headers=creator_hdr,
        json={
            "source_warehouse_id": base_data["wh1_id"],
            "destination_warehouse_id": base_data["wh2_id"],
            "reason": "Maker Checker Test",
            "items": [{"product_id": base_data["p1_id"], "quantity": 2}],
        },
    )
    assert tr_res.status_code == 201
    tr_id = tr_res.get_json()["data"]["id"]

    assert client.post(f"/api/v1/inventory/transfers/{tr_id}/submit", headers=creator_hdr).status_code == 200

    # Creator self-approval is REJECTED with 403
    res_self_appr = client.post(f"/api/v1/inventory/transfers/{tr_id}/approve", headers=creator_hdr)
    assert res_self_appr.status_code == 403
    assert "creator cannot approve" in res_self_appr.get_json()["error"]

    # Checker approval SUCCEEDS
    assert client.post(f"/api/v1/inventory/transfers/{tr_id}/approve", headers=checker_hdr).status_code == 200

    # 2. Inventory Adjustment Maker-Checker
    adj_res = client.post(
        "/api/v1/inventory/adjusters",
        headers=creator_hdr,
        json={
            "inventory_balance_id": base_data["b1_id"],
            "adjustment_type": "ADD",
            "quantity": 5,
            "description": "Stock adjustment test",
        },
    )
    assert adj_res.status_code == 201
    adj_id = adj_res.get_json()["data"]["id"]

    # Creator self-review is REJECTED with 403
    res_adj_self = client.post(f"/api/v1/inventory/adjusters/{adj_id}/approve", headers=creator_hdr)
    assert res_adj_self.status_code == 403
    assert "creator cannot review" in res_adj_self.get_json()["error"]

    # Checker review SUCCEEDS
    assert client.post(f"/api/v1/inventory/adjusters/{adj_id}/approve", headers=checker_hdr).status_code == 200
