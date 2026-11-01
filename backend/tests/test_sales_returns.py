"""Tests for the posted-shipment return workflow."""

from app import db
from app.models import User
from app.routes.identity.auth import generate_token


def sales_approver_headers(client):
    with client.application.app_context():
        user = User.query.filter_by(username='return-test-manager').first()
        if user is None:
            user = User(
                username='return-test-manager',
                email='return-test-manager@example.com',
                role='manager',
                all_warehouses=True,
            )
            user.set_password('test-password')
            db.session.add(user)
            db.session.commit()
        token = generate_token(user.id)
    return {'Authorization': f'Bearer {token}'}


def create_posted_shipment(client, quantity=2):
    customer = client.post('/api/v1/customers', json={
        'name': 'Return Customer'
    }).get_json()['data']
    warehouse = client.post('/api/v1/warehouses', json={
        'code': 'WH-RETURN',
        'name': 'Return Warehouse'
    }).get_json()['data']
    product = client.post('/api/v1/products', json={
        'sku': 'SKU-RETURN',
        'name': 'Return Product',
        'min_stock': 0
    }).get_json()['data']
    balance = client.post('/api/v1/inventory/balances', json={
        'product_id': product['id'],
        'warehouse_id': warehouse['id'],
        'quantity_on_hand': 10,
        'average_cost': 5
    }).get_json()['data']
    order = client.post('/api/v1/sales-orders', json={
        'customer_id': customer['id'],
        'warehouse_id': warehouse['id'],
        'due_date': '2026-12-25',
        'items': [{'product_id': product['id'], 'quantity': quantity}]
    }).get_json()['data']
    assert client.post(
        f"/api/v1/sales-orders/{order['id']}/submit"
    ).status_code == 200
    assert client.post(
        f"/api/v1/sales-orders/{order['id']}/approve",
        headers=sales_approver_headers(client),
    ).status_code == 200
    shipment_response = client.post(
        f"/api/v1/sales-orders/{order['id']}/shipments",
        json={'items': [{
            'sales_order_item_id': order['items'][0]['id'],
            'quantity': quantity
        }]}
    )
    assert shipment_response.status_code == 201
    shipment = shipment_response.get_json()['data']
    posted = client.post(f"/api/v1/shipments/{shipment['id']}/post")
    assert posted.status_code == 200
    return shipment, balance


class TestSalesReturns:
    def test_return_posts_restocked_quantity_once(self, client):
        shipment, balance = create_posted_shipment(client)
        shipment_item_id = shipment['items'][0]['id']
        response = client.post('/api/v1/sales-returns', json={
            'shipment_id': shipment['id'],
            'reason': 'Customer returned unopened items',
            'items': [{
                'shipment_item_id': shipment_item_id,
                'quantity': 1.5,
                'condition': 'RESTOCK'
            }]
        })
        assert response.status_code == 201
        sales_return = response.get_json()['data']
        assert sales_return['status'] == 'DRAFT'
        assert sales_return['warehouse_id'] == balance['warehouse_id']
        assert client.get(
            f"/api/v1/inventory/balances/{balance['id']}"
        ).get_json()['data']['quantity_on_hand'] == 8

        posted = client.post(
            f"/api/v1/sales-returns/{sales_return['id']}/post"
        )
        assert posted.status_code == 200
        posted_data = posted.get_json()['data']
        assert posted_data['status'] == 'POSTED'
        assert posted_data['posted_by'] is not None
        assert client.get(
            f"/api/v1/inventory/balances/{balance['id']}"
        ).get_json()['data']['quantity_on_hand'] == 9.5

        movements = client.get(
            f"/api/v1/movements?product_id={shipment['items'][0]['product_id']}"
        ).get_json()['data']
        return_movements = [
            movement for movement in movements
            if movement['reference_type'] == 'SALES_RETURN'
        ]
        assert len(return_movements) == 1
        assert return_movements[0]['movement_type'] == 'RETURN_IN'
        assert return_movements[0]['quantity_delta'] == 1.5

        assert client.get('/api/v1/sales-returns').get_json()['total'] == 1
        assert client.get(
            f"/api/v1/sales-returns/{sales_return['id']}"
        ).get_json()['data']['return_number'] == sales_return['return_number']
        assert client.post(
            f"/api/v1/sales-returns/{sales_return['id']}/post"
        ).status_code == 409

    def test_damaged_return_is_recorded_without_restocking(self, client):
        shipment, balance = create_posted_shipment(client)
        sales_return = client.post('/api/v1/sales-returns', json={
            'shipment_id': shipment['id'],
            'reason': 'Items arrived damaged',
            'items': [{
                'shipment_item_id': shipment['items'][0]['id'],
                'quantity': 1,
                'condition': 'DAMAGED'
            }]
        }).get_json()['data']

        response = client.post(
            f"/api/v1/sales-returns/{sales_return['id']}/post"
        )
        assert response.status_code == 200
        assert client.get(
            f"/api/v1/inventory/balances/{balance['id']}"
        ).get_json()['data']['quantity_on_hand'] == 8
        movements = client.get(
            f"/api/v1/movements?product_id={shipment['items'][0]['product_id']}"
        ).get_json()['data']
        assert not any(
            movement['reference_type'] == 'SALES_RETURN'
            for movement in movements
        )

    def test_returns_cannot_exceed_posted_shipment_quantity(self, client):
        shipment, _ = create_posted_shipment(client, quantity=1)
        first_return = client.post('/api/v1/sales-returns', json={
            'shipment_id': shipment['id'],
            'reason': 'Return one item',
            'items': [{
                'shipment_item_id': shipment['items'][0]['id'],
                'quantity': 1,
                'condition': 'RESTOCK'
            }]
        }).get_json()['data']
        assert client.post(
            f"/api/v1/sales-returns/{first_return['id']}/post"
        ).status_code == 200

        excessive = client.post('/api/v1/sales-returns', json={
            'shipment_id': shipment['id'],
            'reason': 'Attempt duplicate return',
            'items': [{
                'shipment_item_id': shipment['items'][0]['id'],
                'quantity': 0.1,
                'condition': 'RESTOCK'
            }]
        })
        assert excessive.status_code == 409

    def test_returns_require_a_posted_shipment_and_valid_condition(self, client):
        shipment, _ = create_posted_shipment(client)
        invalid = client.post('/api/v1/sales-returns', json={
            'shipment_id': shipment['id'],
            'reason': 'Invalid condition',
            'items': [{
                'shipment_item_id': shipment['items'][0]['id'],
                'quantity': 1,
                'condition': 'DISPOSED'
            }]
        })
        assert invalid.status_code == 400
