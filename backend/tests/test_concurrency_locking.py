"""Tests for concurrency control and deterministic deadlock-safe row locking."""
from app import db
from app.models import InventoryBalance, User
from app.routes.identity.auth import generate_token


def create_approver_headers(client, username="concurrency-approver"):
    with client.application.app_context():
        user = User(
            username=username,
            email=f"{username}@example.com",
            role="manager",
            all_warehouses=True,
        )
        user.set_password("test-password")
        db.session.add(user)
        db.session.commit()
        token = generate_token(user.id)
    return {"Authorization": f"Bearer {token}"}


def test_inventory_balance_get_or_create_existing(client, app):
    """get_or_create returns existing balance row without duplicating."""
    wh = client.post("/api/v1/warehouses", json={
        "code": "WH-CONC-1",
        "name": "Warehouse Conc 1",
    }).get_json()["data"]

    prod = client.post("/api/v1/products", json={
        "sku": "SKU-CONC-1",
        "name": "Product Conc 1",
        "min_stock": 0,
    }).get_json()["data"]

    with app.app_context():
        # First call creates the balance atomically with 0 stock
        b1 = InventoryBalance.get_or_create(prod["id"], wh["id"], for_update=True)
        assert b1 is not None
        assert b1.product_id == prod["id"]
        assert b1.warehouse_id == wh["id"]
        assert float(b1.quantity_on_hand) == 0.0

        b1.quantity_on_hand = 45.0
        db.session.commit()

        # Second call retrieves the existing row
        b2 = InventoryBalance.get_or_create(prod["id"], wh["id"], for_update=True)
        assert b2.id == b1.id
        assert float(b2.quantity_on_hand) == 45.0


def test_multi_item_sales_order_inverted_order(client):
    """SO creation and reservation with inverted item order executes deterministically."""
    wh = client.post("/api/v1/warehouses", json={
        "code": "WH-SO-CONC",
        "name": "SO Conc Warehouse",
    }).get_json()["data"]

    cust = client.post("/api/v1/customers", json={
        "name": "Conc Customer",
    }).get_json()["data"]

    p1 = client.post("/api/v1/products", json={
        "sku": "SKU-SO-ALPHA",
        "name": "Alpha Item",
        "min_stock": 0,
    }).get_json()["data"]

    p2 = client.post("/api/v1/products", json={
        "sku": "SKU-SO-BETA",
        "name": "Beta Item",
        "min_stock": 0,
    }).get_json()["data"]

    # Seed stock
    client.post("/api/v1/inventory/balances", json={
        "product_id": p1["id"],
        "warehouse_id": wh["id"],
        "quantity_on_hand": 50,
        "average_cost": 10.0,
    })
    client.post("/api/v1/inventory/balances", json={
        "product_id": p2["id"],
        "warehouse_id": wh["id"],
        "quantity_on_hand": 50,
        "average_cost": 20.0,
    })

    # Create SO with inverted item sequence [P2, P1]
    res = client.post(
        "/api/v1/sales-orders",
        json={
            "customer_id": cust["id"],
            "warehouse_id": wh["id"],
            "due_date": "2026-12-25",
            "items": [
                {"product_id": p2["id"], "quantity": 5},
                {"product_id": p1["id"], "quantity": 10},
            ],
        },
    )
    assert res.status_code == 201
    so = res.get_json()["data"]
    so_id = so["id"]
    assert so["status"] == "RESERVED"

    assert client.post(f"/api/v1/sales-orders/{so_id}/submit").status_code == 200
    approver = create_approver_headers(client, username="so-approver")
    assert client.post(
        f"/api/v1/sales-orders/{so_id}/approve", headers=approver
    ).status_code == 200

    # Create and post shipment (locks balances in sorted order and decrements)
    ship_res = client.post(f"/api/v1/sales-orders/{so_id}/shipment")
    assert ship_res.status_code == 200
    assert ship_res.get_json()["shipment"]["status"] == "POSTED"

    # Verify balances after shipment
    b1_data = client.get(f"/api/v1/inventory/balances?product_id={p1['id']}&warehouse_id={wh['id']}").get_json()["data"][0]
    b2_data = client.get(f"/api/v1/inventory/balances?product_id={p2['id']}&warehouse_id={wh['id']}").get_json()["data"][0]
    assert float(b1_data["quantity_on_hand"]) == 40.0  # 50 - 10
    assert float(b1_data["quantity_reserved"]) == 0.0
    assert float(b2_data["quantity_on_hand"]) == 45.0  # 50 - 5
    assert float(b2_data["quantity_reserved"]) == 0.0


def test_post_goods_receipt_with_uninitialized_balances(client):
    """Posting goods receipt for products without prior balances initializes them atomically."""
    wh = client.post("/api/v1/warehouses", json={
        "code": "WH-GR-CONC",
        "name": "GR Conc Warehouse",
    }).get_json()["data"]

    sup = client.post("/api/v1/suppliers", json={
        "name": "GR Conc Supplier",
    }).get_json()["data"]

    p1 = client.post("/api/v1/products", json={
        "sku": "SKU-GR-1",
        "name": "GR Product 1",
        "min_stock": 0,
    }).get_json()["data"]

    p2 = client.post("/api/v1/products", json={
        "sku": "SKU-GR-2",
        "name": "GR Product 2",
        "min_stock": 0,
    }).get_json()["data"]

    # Create PO with items (unit_cost)
    po_res = client.post("/api/v1/purchase-orders", json={
        "supplier_id": sup["id"],
        "warehouse_id": wh["id"],
        "items": [
            {"product_id": p1["id"], "quantity": 20, "unit_cost": 15.0},
            {"product_id": p2["id"], "quantity": 30, "unit_cost": 25.0},
        ],
    })
    assert po_res.status_code == 201
    po = po_res.get_json()["data"]
    po_items = po["items"]

    poi_map = {item["product_id"]: item["id"] for item in po_items}

    # Submit and approve PO
    assert client.post(f"/api/v1/purchase-orders/{po['id']}/submit").status_code == 200
    approver = create_approver_headers(client, username="po-approver")
    assert client.post(f"/api/v1/purchase-orders/{po['id']}/approve", headers=approver).status_code == 200

    # Create Goods Receipt with inverted items [P2, P1] via POST /api/v1/goods-receipts
    gr_res = client.post("/api/v1/goods-receipts", json={
        "purchase_order_id": po["id"],
        "items": [
            {"purchase_order_item_id": poi_map[p2["id"]], "quantity": 30},
            {"purchase_order_item_id": poi_map[p1["id"]], "quantity": 20},
        ],
    })
    assert gr_res.status_code == 201
    gr_id = gr_res.get_json()["data"]["id"]

    # Post Goods Receipt
    post_res = client.post(f"/api/v1/goods-receipts/{gr_id}/post")
    assert post_res.status_code == 200

    # Verify inventory balances were created atomically
    b1_res = client.get(f"/api/v1/inventory/balances?product_id={p1['id']}&warehouse_id={wh['id']}")
    assert b1_res.status_code == 200
    b1_data = b1_res.get_json()["data"]
    assert len(b1_data) == 1
    assert float(b1_data[0]["quantity_on_hand"]) == 20.0
    assert float(b1_data[0]["average_cost"]) == 15.0

    b2_res = client.get(f"/api/v1/inventory/balances?product_id={p2['id']}&warehouse_id={wh['id']}")
    assert b2_res.status_code == 200
    b2_data = b2_res.get_json()["data"]
    assert len(b2_data) == 1
    assert float(b2_data[0]["quantity_on_hand"]) == 30.0
    assert float(b2_data[0]["average_cost"]) == 25.0


def test_post_stock_transfer_with_uninitialized_destination_balance(client):
    """Posting stock transfer creates destination balances in sorted order without collision."""
    w_src = client.post("/api/v1/warehouses", json={
        "code": "WH-TR-SRC",
        "name": "TR Source Warehouse",
    }).get_json()["data"]

    w_dst = client.post("/api/v1/warehouses", json={
        "code": "WH-TR-DST",
        "name": "TR Dest Warehouse",
    }).get_json()["data"]

    p1 = client.post("/api/v1/products", json={
        "sku": "SKU-TR-ALPHA",
        "name": "TR Alpha Item",
        "min_stock": 0,
    }).get_json()["data"]

    p2 = client.post("/api/v1/products", json={
        "sku": "SKU-TR-BETA",
        "name": "TR Beta Item",
        "min_stock": 0,
    }).get_json()["data"]

    # Seed source balances only
    client.post("/api/v1/inventory/balances", json={
        "product_id": p1["id"],
        "warehouse_id": w_src["id"],
        "quantity_on_hand": 50,
        "average_cost": 10.0,
    })
    client.post("/api/v1/inventory/balances", json={
        "product_id": p2["id"],
        "warehouse_id": w_src["id"],
        "quantity_on_hand": 50,
        "average_cost": 20.0,
    })

    # Create transfer with inverted items [P2, P1]
    transfer_res = client.post("/api/v1/inventory/transfers", json={
        "source_warehouse_id": w_src["id"],
        "destination_warehouse_id": w_dst["id"],
        "reason": "Concurrency test transfer",
        "items": [
            {"product_id": p2["id"], "quantity": 15},
            {"product_id": p1["id"], "quantity": 10},
        ],
    })
    assert transfer_res.status_code == 201
    transfer_id = transfer_res.get_json()["data"]["id"]

    # Submit and approve
    assert client.post(f"/api/v1/inventory/transfers/{transfer_id}/submit").status_code == 200
    approver = create_approver_headers(client, username="transfer-approver")
    assert client.post(f"/api/v1/inventory/transfers/{transfer_id}/approve", headers=approver).status_code == 200

    # Post transfer (destination balances do not exist yet)
    post_res = client.post(f"/api/v1/inventory/transfers/{transfer_id}/post")
    assert post_res.status_code == 200
    assert post_res.get_json()["data"]["status"] == "POSTED"

    # Verify destination balances were created with correct values
    dst_b1 = client.get(f"/api/v1/inventory/balances?product_id={p1['id']}&warehouse_id={w_dst['id']}").get_json()["data"]
    assert len(dst_b1) == 1
    assert float(dst_b1[0]["quantity_on_hand"]) == 10.0
    assert float(dst_b1[0]["average_cost"]) == 10.0

    dst_b2 = client.get(f"/api/v1/inventory/balances?product_id={p2['id']}&warehouse_id={w_dst['id']}").get_json()["data"]
    assert len(dst_b2) == 1
    assert float(dst_b2[0]["quantity_on_hand"]) == 15.0
    assert float(dst_b2[0]["average_cost"]) == 20.0
