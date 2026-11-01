"""Tests for the inventory adjustment approval workflow."""

from app import db
from app.models import User
from app.routes.identity.auth import generate_token


def create_balance(client, sku='SKU-ADJ', quantity=10):
    warehouse = client.post('/api/v1/warehouses', json={
        'code': f'WH-{sku}',
        'name': 'Test Warehouse'
    }).get_json()['data']
    product = client.post('/api/v1/products', json={
        'sku': sku,
        'name': 'Test Product',
        'min_stock': 0
    }).get_json()['data']
    balance = client.post('/api/v1/inventory/balances', json={
        'product_id': product['id'],
        'warehouse_id': warehouse['id'],
        'quantity_on_hand': quantity,
        'average_cost': 25
    }).get_json()['data']
    return balance


def reviewer_headers(client):
    with client.application.app_context():
        user = User.query.filter_by(username='adjustment-reviewer').first()
        if user is None:
            user = User(
                username='adjustment-reviewer',
                email='adjustment-reviewer@example.com',
                role='manager',
                all_warehouses=True
            )
            user.set_password('test-password')
            db.session.add(user)
            db.session.commit()
        token = generate_token(user.id)
    return {'Authorization': f'Bearer {token}'}


class TestInventoryAdjuster:
    def test_adjustment_changes_stock_only_when_posted(self, client):
        balance = create_balance(client)
        response = client.post('/api/v1/inventory/adjusters', json={
            'inventory_balance_id': balance['id'],
            'adjustment_type': 'ADD',
            'quantity': 20,
            'description': 'Stock count adjustment'
        })

        assert response.status_code == 201
        adjustment = response.get_json()['data']
        assert adjustment['status'] == 'PENDING'

        current_balance = client.get(
            f"/api/v1/inventory/balances/{balance['id']}"
        ).get_json()['data']
        assert current_balance['quantity_on_hand'] == 10

        approval = client.post(
            f"/api/v1/inventory/adjusters/{adjustment['id']}/approve",
            headers=reviewer_headers(client)
        )
        assert approval.status_code == 200
        assert approval.get_json()['data']['status'] == 'APPROVED'
        assert approval.get_json()['data']['created_by'] != approval.get_json()['data']['reviewed_by']

        current_balance = client.get(
            f"/api/v1/inventory/balances/{balance['id']}"
        ).get_json()['data']
        assert current_balance['quantity_on_hand'] == 10
        movements_before_post = client.get('/api/v1/movements').get_json()['data']
        assert len(movements_before_post) == 1
        assert movements_before_post[0]['reference_type'] == 'OPENING_BALANCE'

        posting = client.post(
            f"/api/v1/inventory/adjusters/{adjustment['id']}/post"
        )
        assert posting.status_code == 200
        assert posting.get_json()['data']['status'] == 'POSTED'
        assert posting.get_json()['data']['posted_by'] is not None

        current_balance = client.get(
            f"/api/v1/inventory/balances/{balance['id']}"
        ).get_json()['data']
        assert current_balance['quantity_on_hand'] == 30

        movements = client.get('/api/v1/movements').get_json()['data']
        adjustment_movements = [
            movement for movement in movements
            if movement['reference_type'] == 'INVENTORY_ADJUSTMENT'
        ]
        assert len(adjustment_movements) == 1
        assert adjustment_movements[0]['quantity_delta'] == 20
        repeated_post = client.post(
            f"/api/v1/inventory/adjusters/{adjustment['id']}/post"
        )
        assert repeated_post.status_code == 409

    def test_adjustments_canonical_route_aliases(self, client):
        balance = create_balance(client, sku='SKU-ADJ-ALIAS')
        response = client.post('/api/v1/inventory/adjustments', json={
            'inventory_balance_id': balance['id'],
            'adjustment_type': 'ADD',
            'quantity': 2
        })

        assert response.status_code == 201
        assert response.get_json()['data']['status'] == 'PENDING'
        assert client.get('/api/v1/inventory/adjustments').status_code == 200

    def test_rejected_adjustment_does_not_change_stock(self, client):
        balance = create_balance(client, sku='SKU-REJECT')
        response = client.post('/api/v1/inventory/adjusters', json={
            'inventory_balance_id': balance['id'],
            'adjustment_type': 'REDUCE',
            'quantity': 5
        })
        adjustment_id = response.get_json()['data']['id']

        rejection = client.post(
            f'/api/v1/inventory/adjusters/{adjustment_id}/reject',
            headers=reviewer_headers(client)
        )
        assert rejection.status_code == 200
        assert rejection.get_json()['data']['status'] == 'REJECTED'
        assert client.post(
            f'/api/v1/inventory/adjusters/{adjustment_id}/post'
        ).status_code == 409

        current_balance = client.get(
            f"/api/v1/inventory/balances/{balance['id']}"
        ).get_json()['data']
        assert current_balance['quantity_on_hand'] == 10
        movements = client.get('/api/v1/movements').get_json()['data']
        assert len(movements) == 1
        assert movements[0]['reference_type'] == 'OPENING_BALANCE'

    def test_adjustment_creator_cannot_approve_own_request(self, client):
        balance = create_balance(client, sku='SKU-SELF-APPROVAL')
        response = client.post('/api/v1/inventory/adjusters', json={
            'inventory_balance_id': balance['id'],
            'adjustment_type': 'ADD',
            'quantity': 1
        })
        adjustment_id = response.get_json()['data']['id']
        rejected = client.post(
            f'/api/v1/inventory/adjusters/{adjustment_id}/approve'
        )
        assert rejected.status_code == 403

    def test_pending_reduction_respects_reserved_stock(self, client):
        balance = create_balance(client, sku='SKU-RESERVED')
        from app import db
        from app.models import InventoryBalance

        with client.application.app_context():
            record = db.session.get(InventoryBalance, balance['id'])
            record.quantity_reserved = 8
            db.session.commit()

        response = client.post('/api/v1/inventory/adjusters', json={
            'inventory_balance_id': balance['id'],
            'adjustment_type': 'REDUCE',
            'quantity': 3
        })
        assert response.status_code == 400
