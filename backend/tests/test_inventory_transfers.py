from app import db
from app.models import User
from app.routes.identity.auth import generate_token


def create_transfer_data(client):
    source = client.post('/api/v1/warehouses', json={
        'code': 'WH-TRANSFER-SRC',
        'name': 'Transfer Source'
    }).get_json()['data']
    destination = client.post('/api/v1/warehouses', json={
        'code': 'WH-TRANSFER-DST',
        'name': 'Transfer Destination'
    }).get_json()['data']
    product = client.post('/api/v1/products', json={
        'sku': 'SKU-TRANSFER',
        'name': 'Transfer Product',
        'min_stock': 0
    }).get_json()['data']
    balance = client.post('/api/v1/inventory/balances', json={
        'product_id': product['id'],
        'warehouse_id': source['id'],
        'quantity_on_hand': 20,
        'average_cost': 7
    }).get_json()['data']
    return source, destination, product, balance


def create_approver_headers(client):
    with client.application.app_context():
        user = User(
            username='transfer-approver',
            email='transfer-approver@example.com',
            role='manager',
            all_warehouses=True
        )
        user.set_password('test-password')
        db.session.add(user)
        db.session.commit()
        token = generate_token(user.id)
    return {'Authorization': f'Bearer {token}'}


class TestInventoryTransfers:
    def test_transfer_approval_posts_both_ledgers_atomically(self, client):
        source, destination, product, source_balance = create_transfer_data(client)
        transfer_response = client.post('/api/v1/inventory/transfers', json={
            'source_warehouse_id': source['id'],
            'destination_warehouse_id': destination['id'],
            'reason': 'Rebalance stock',
            'items': [{'product_id': product['id'], 'quantity': 5}]
        })
        assert transfer_response.status_code == 201
        transfer = transfer_response.get_json()['data']
        assert transfer['status'] == 'DRAFT'

        assert client.post(
            f"/api/v1/inventory/transfers/{transfer['id']}/submit"
        ).status_code == 200
        assert client.post(
            f"/api/v1/inventory/transfers/{transfer['id']}/approve"
        ).status_code == 403
        approver_headers = create_approver_headers(client)
        assert client.post(
            f"/api/v1/inventory/transfers/{transfer['id']}/approve",
            headers=approver_headers
        ).status_code == 200
        posted = client.post(f"/api/v1/inventory/transfers/{transfer['id']}/post")
        assert posted.status_code == 200
        assert posted.get_json()['data']['status'] == 'POSTED'
        assert client.post(f"/api/v1/inventory/transfers/{transfer['id']}/post").status_code == 409

        source_after = client.get(
            f"/api/v1/inventory/balances/{source_balance['id']}"
        ).get_json()['data']
        destination_after = client.get(
            f"/api/v1/inventory/balances?warehouse_id={destination['id']}"
        ).get_json()['data'][0]
        assert source_after['quantity_on_hand'] == 15
        assert source_after['quantity_reserved'] == 0
        assert destination_after['quantity_on_hand'] == 5
        assert destination_after['average_cost'] == 7

        movements = client.get(
            f"/api/v1/movements?product_id={product['id']}"
        ).get_json()['data']
        transfer_movements = [
            movement for movement in movements
            if movement['reference_type'] == 'STOCK_TRANSFER'
        ]
        assert len(transfer_movements) == 2
        assert {movement['movement_type'] for movement in transfer_movements} == {
            'TRANSFER_OUT', 'TRANSFER_IN'
        }
        assert sum(movement['quantity_delta'] for movement in transfer_movements) == 0

    def test_transfer_checks_stock_and_distinct_warehouses(self, client):
        source, destination, product, _ = create_transfer_data(client)
        same_warehouse = client.post('/api/v1/inventory/transfers', json={
            'source_warehouse_id': source['id'],
            'destination_warehouse_id': source['id'],
            'reason': 'Invalid move',
            'items': [{'product_id': product['id'], 'quantity': 1}]
        })
        assert same_warehouse.status_code == 400

        draft = client.post('/api/v1/inventory/transfers', json={
            'source_warehouse_id': source['id'],
            'destination_warehouse_id': destination['id'],
            'reason': 'Too much stock',
            'items': [{'product_id': product['id'], 'quantity': 21}]
        })
        transfer_id = draft.get_json()['data']['id']
        failed = client.post(f'/api/v1/inventory/transfers/{transfer_id}/submit')
        assert failed.status_code == 409
        assert client.get(
            f'/api/v1/inventory/transfers/{transfer_id}'
        ).get_json()['data']['status'] == 'DRAFT'

    def test_scoped_user_cannot_transfer_into_unassigned_warehouse(self, client):
        source, destination, product, _ = create_transfer_data(client)
        transfer_response = client.post('/api/v1/inventory/transfers', json={
            'source_warehouse_id': source['id'],
            'destination_warehouse_id': destination['id'],
            'reason': 'Restricted transfer',
            'items': [{'product_id': product['id'], 'quantity': 1}]
        })
        assert transfer_response.status_code == 201
        transfer_id = transfer_response.get_json()['data']['id']
        with client.application.app_context():
            user = User(
                username='single-warehouse',
                email='single-warehouse@example.com',
                role='warehouse'
            )
            user.set_password('test-password')
            from app.models import UserWarehouseAccess
            user.warehouse_access.append(
                UserWarehouseAccess(warehouse_id=source['id'])
            )
            db.session.add(user)
            db.session.commit()
            token = generate_token(user.id)
        response = client.post('/api/v1/inventory/transfers', json={
            'source_warehouse_id': source['id'],
            'destination_warehouse_id': destination['id'],
            'reason': 'Unauthorized destination',
            'items': [{'product_id': product['id'], 'quantity': 1}]
        }, headers={'Authorization': f'Bearer {token}'})
        assert response.status_code == 403
        headers = {'Authorization': f'Bearer {token}'}
        assert client.get(
            f'/api/v1/inventory/transfers/{transfer_id}',
            headers=headers
        ).status_code == 403
        assert client.get(
            '/api/v1/inventory/transfers'
            f'?source_warehouse_id={source["id"]}'
            f'&destination_warehouse_id={destination["id"]}',
            headers=headers
        ).status_code == 403
