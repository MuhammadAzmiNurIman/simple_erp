"""Tests for purchase order persistence and stock posting."""

from decimal import Decimal

from app import db
from app.models import PurchaseOrder, PurchaseOrderItem, User
from app.routes.identity.auth import generate_token


def create_purchase_data(client, stock=6):
    supplier = client.post('/api/v1/suppliers', json={
        'name': 'Test Supplier'
    }).get_json()['data']
    warehouse = client.post('/api/v1/warehouses', json={
        'code': 'WH-PURCHASE',
        'name': 'Purchase Warehouse'
    }).get_json()['data']
    product = client.post('/api/v1/products', json={
        'sku': 'SKU-PURCHASE',
        'name': 'Purchase Product',
        'min_stock': 0
    }).get_json()['data']
    balance = client.post('/api/v1/inventory/balances', json={
        'product_id': product['id'],
        'warehouse_id': warehouse['id'],
        'quantity_on_hand': stock,
        'average_cost': 5
    }).get_json()['data']
    return supplier, warehouse, product, balance


def create_second_operator_headers(client):
    with client.application.app_context():
        user = User(
            username='purchase-approver',
            email='purchase-approver@example.com',
            role='manager',
            all_warehouses=True
        )
        user.set_password('test-password')
        db.session.add(user)
        db.session.commit()
        token = generate_token(user.id)
    return {'Authorization': f'Bearer {token}'}


class TestPurchasing:
    def test_purchase_money_uses_decimal_and_half_up_rounding(self, client, app):
        supplier, warehouse, product, _ = create_purchase_data(client)
        response = client.post('/api/v1/purchase-orders', json={
            'supplier_id': supplier['id'],
            'warehouse_id': warehouse['id'],
            'items': [{
                'product_id': product['id'],
                'quantity': 1,
                'unit_cost': 2.675,
            }]
        })

        assert response.status_code == 201
        assert response.get_json()['data']['total_amount'] == 2.68
        with app.app_context():
            order = db.session.get(PurchaseOrder, response.get_json()['data']['id'])
            assert isinstance(order.total_amount, Decimal)
            assert isinstance(order.items[0].total_cost, Decimal)

    def test_purchase_order_submit_approval_and_cancel_routes(self, client):
        supplier, warehouse, product, _ = create_purchase_data(client)
        response = client.post('/api/v1/purchase-orders', json={
            'supplier_id': supplier['id'],
            'warehouse_id': warehouse['id'],
            'items': [{
                'product_id': product['id'],
                'quantity': 2,
                'unit_cost': 10
            }]
        })
        assert response.status_code == 201
        order = response.get_json()['data']
        submitted = client.post(
            f"/api/v1/purchase-orders/{order['id']}/submit"
        )
        assert submitted.status_code == 200
        assert submitted.get_json()['data']['status'] == 'SUBMITTED'
        approver_headers = create_second_operator_headers(client)
        assert client.post(
            f"/api/v1/purchase-orders/{order['id']}/approve",
            headers=approver_headers
        ).status_code == 200
        assert client.post(
            f"/api/v1/purchase-orders/{order['id']}/cancel"
        ).status_code == 200
        assert client.get(
            f"/api/v1/purchase-orders/{order['id']}"
        ).get_json()['data']['status'] == 'CANCELLED'

    def test_vendor_bill_post_method_contract_rejects_invalid_receipt(self, client):
        response = client.post('/api/v1/vendor-bills', json={
            'goods_receipt_id': 999
        })
        assert response.status_code == 404

    def test_purchase_order_is_persisted_and_posted_once(self, client):
        supplier, warehouse, product, balance = create_purchase_data(client)
        response = client.post('/api/v1/purchase-orders', json={
            'supplier_id': supplier['id'],
            'warehouse_id': warehouse['id'],
            'order_date': '2026-10-25',
            'items': [{
                'product_id': product['id'],
                'quantity': 4,
                'unit_cost': 10
            }]
        })
        assert response.status_code == 201
        order = response.get_json()['data']
        assert order['status'] == 'DRAFT'
        assert len(order['items']) == 1
        assert order['supplier_name'] == supplier['name']
        assert order['warehouse_name'] == warehouse['name']
        assert order['items'][0]['product_name'] == product['name']

        assert client.get(
            f"/api/v1/purchase-orders/{order['id']}"
        ).get_json()['data']['code'] == order['code']
        assert client.get('/api/v1/purchase-orders').get_json()['total'] == 1

        assert client.post(
            f"/api/v1/purchase-orders/{order['id']}/submit"
        ).status_code == 200
        approver_headers = create_second_operator_headers(client)
        assert client.post(
            f"/api/v1/purchase-orders/{order['id']}/approve",
            headers=approver_headers
        ).status_code == 200
        posted = client.post(
            f"/api/v1/purchase-orders/{order['id']}/post"
        )
        assert posted.status_code == 200
        assert posted.get_json()['data']['status'] == 'POSTED'
        assert client.get(
            f"/api/v1/purchase-orders/{order['id']}"
        ).get_json()['data']['status'] == 'RECEIVED'

        current = client.get(
            f"/api/v1/inventory/balances/{balance['id']}"
        ).get_json()['data']
        assert current['quantity_on_hand'] == 10
        assert current['average_cost'] == 7

        movements = client.get('/api/v1/movements').get_json()['data']
        assert len(movements) == 2  # opening balance plus posted goods receipt
        receipt_movements = [
            movement for movement in movements
            if movement['reference_type'] == 'GOODS_RECEIPT'
        ]
        assert len(receipt_movements) == 1
        assert receipt_movements[0]['movement_type'] == 'IN'
        assert receipt_movements[0]['quantity_delta'] == 4

        duplicate_post = client.post(
            f"/api/v1/purchase-orders/{order['id']}/post"
        )
        assert duplicate_post.status_code == 409

    def test_purchase_order_requires_approval_by_another_user(self, client):
        supplier, warehouse, product, _ = create_purchase_data(client)
        response = client.post('/api/v1/purchase-orders', json={
            'supplier_id': supplier['id'],
            'warehouse_id': warehouse['id'],
            'items': [{'product_id': product['id'], 'quantity': 4, 'unit_cost': 10}]
        })
        order = response.get_json()['data']
        assert client.post(
            f"/api/v1/purchase-orders/{order['id']}/submit"
        ).status_code == 200
        self_approval = client.post(
            f"/api/v1/purchase-orders/{order['id']}/approve"
        )
        assert self_approval.status_code == 403
        assert client.post(f"/api/v1/purchase-orders/{order['id']}/post").status_code == 409

    def test_partial_receipts_update_stock_and_create_one_bill_each(self, client):
        supplier, warehouse, product, balance = create_purchase_data(client)
        order_response = client.post('/api/v1/purchase-orders', json={
            'supplier_id': supplier['id'],
            'warehouse_id': warehouse['id'],
            'items': [{'product_id': product['id'], 'quantity': 4, 'unit_cost': 10}]
        })
        order = order_response.get_json()['data']
        assert client.post(
            f"/api/v1/purchase-orders/{order['id']}/submit"
        ).status_code == 200
        approver_headers = create_second_operator_headers(client)
        assert client.post(
            f"/api/v1/purchase-orders/{order['id']}/approve",
            headers=approver_headers
        ).status_code == 200
        item_id = order['items'][0]['id']

        for quantity in (1.5, 2.5):
            receipt_response = client.post('/api/v1/goods-receipts', json={
                'purchase_order_id': order['id'],
                'items': [{
                    'purchase_order_item_id': item_id,
                    'quantity': quantity
                }]
            })
            assert receipt_response.status_code == 201
            receipt = receipt_response.get_json()['data']
            assert receipt['supplier_name'] == supplier['name']
            assert receipt['items'][0]['product_name'] == product['name']
            receipt_id = receipt['id']
            posted = client.post(f'/api/v1/goods-receipts/{receipt_id}/post')
            assert posted.status_code == 200
            bill_id = posted.get_json()['vendor_bill']['id']
            assert client.post(f'/api/v1/goods-receipts/{receipt_id}/post').status_code == 409
            assert client.get(
                f'/api/v1/vendor-bills/{bill_id}'
            ).get_json()['data']['balance_due'] == round(quantity * 10, 2)

        current = client.get(
            f"/api/v1/inventory/balances/{balance['id']}"
        ).get_json()['data']
        assert current['quantity_on_hand'] == 10
        assert current['average_cost'] == 7
        assert client.get(
            f"/api/v1/purchase-orders/{order['id']}"
        ).get_json()['data']['status'] == 'RECEIVED'

    def test_supplier_payment_draft_and_allocation_posting(self, client):
        supplier, warehouse, product, _ = create_purchase_data(client)
        order_response = client.post('/api/v1/purchase-orders', json={
            'supplier_id': supplier['id'],
            'warehouse_id': warehouse['id'],
            'items': [{'product_id': product['id'], 'quantity': 4, 'unit_cost': 10}]
        })
        order = order_response.get_json()['data']
        assert client.post(
            f"/api/v1/purchase-orders/{order['id']}/submit"
        ).status_code == 200
        approver_headers = create_second_operator_headers(client)
        assert client.post(
            f"/api/v1/purchase-orders/{order['id']}/approve",
            headers=approver_headers
        ).status_code == 200
        posted_receipt = client.post(f"/api/v1/purchase-orders/{order['id']}/post")
        assert posted_receipt.status_code == 200
        bill = posted_receipt.get_json()['vendor_bill']

        draft_response = client.post('/api/v1/supplier-payments', json={
            'supplier_id': supplier['id'],
            'amount': 20,
            'payment_method': 'BANK_TRANSFER'
        })
        assert draft_response.status_code == 201
        payment = draft_response.get_json()['data']
        assert payment['status'] == 'DRAFT'
        assert payment['supplier_name'] == supplier['name']
        assert client.get(
            f"/api/v1/vendor-bills/{bill['id']}"
        ).get_json()['data']['balance_due'] == 40

        posted_payment = client.post(
            f"/api/v1/supplier-payments/{payment['id']}/post",
            json={'allocations': [{'vendor_bill_id': bill['id'], 'amount': 15}]}
        )
        assert posted_payment.status_code == 200
        assert posted_payment.get_json()['data']['status'] == 'POSTED'
        assert posted_payment.get_json()['data']['unallocated_amount'] == 5
        bill_after = client.get(
            f"/api/v1/vendor-bills/{bill['id']}"
        ).get_json()['data']
        assert bill_after['status'] == 'PARTIALLY_PAID'
        assert bill_after['balance_due'] == 25
        payables = client.get(
            '/api/v1/finance/payables'
        ).get_json()
        assert payables['total'] == 1
        assert payables['summary']['outstanding_amount'] == 25
        assert client.get(
            '/api/v1/finance/cash-summary'
        ).get_json()['data']['outgoing_amount'] == 20

        second_draft = client.post('/api/v1/supplier-payments', json={
            'supplier_id': supplier['id'],
            'amount': 20,
            'payment_method': 'CASH'
        }).get_json()['data']
        allocated = client.post(
            f"/api/v1/supplier-payments/{second_draft['id']}/allocations",
            json={'allocations': [
                {'vendor_bill_id': bill['id'], 'amount': 15}
            ]}
        )
        assert allocated.status_code == 200
        assert allocated.get_json()['data']['allocated_amount'] == 15
        assert client.get(
            f"/api/v1/vendor-bills/{bill['id']}"
        ).get_json()['data']['balance_due'] == 25
        assert client.post(
            f"/api/v1/supplier-payments/{second_draft['id']}/post"
        ).status_code == 200
        assert client.get(
            f"/api/v1/vendor-bills/{bill['id']}"
        ).get_json()['data']['balance_due'] == 10
        assert client.get(
            '/api/v1/finance/cash-summary'
        ).get_json()['data']['outgoing_amount'] == 40
        dashboard = client.get(
            '/api/v1/dashboard/summary?from_date=2026-01-01&to_date=2026-12-31'
        ).get_json()['data']
        assert dashboard['total_purchase_amount'] == 40
        assert dashboard['payables_outstanding'] == 10
        assert dashboard['cash_outgoing'] == 40
        purchases_report = client.get(
            '/api/v1/reports/purchases?from_date=2026-01-01&to_date=2026-12-31'
        ).get_json()
        assert purchases_report['total_purchase_amount'] == 40
        assert client.post(
            f"/api/v1/supplier-payments/{payment['id']}/post",
            json={'allocations': []}
        ).status_code == 409

    def test_supplier_payment_rejects_non_string_payment_method(self, client):
        supplier, _, _, _ = create_purchase_data(client)
        response = client.post('/api/v1/supplier-payments', json={
            'supplier_id': supplier['id'],
            'amount': 10,
            'payment_method': []
        })
        assert response.status_code == 400

    def test_purchase_order_validates_items(self, client):
        supplier, warehouse, product, _ = create_purchase_data(client)
        response = client.post('/api/v1/purchase-orders', json={
            'supplier_id': supplier['id'],
            'warehouse_id': warehouse['id'],
            'items': [{
                'product_id': product['id'],
                'quantity': -1,
                'unit_cost': 10
            }]
        })
        assert response.status_code == 400

    def test_post_unknown_purchase_order_returns_not_found(self, client):
        assert client.post('/api/v1/purchase-orders/999/post').status_code == 404
