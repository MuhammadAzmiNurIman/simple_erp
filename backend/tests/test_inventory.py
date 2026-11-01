"""Inventory Balance tests."""
from app import db
from app.models import InventoryBalance


class TestInventoryBalances:
    def test_get_inventory_balances(self, client):
        resp = client.get('/api/v1/inventory/balances')
        assert resp.status_code == 200

    def test_get_inventory_summary(self, client):
        resp = client.get('/api/v1/inventory/summary')
        assert resp.status_code == 200

    def test_inventory_balance_exposes_computed_fields(self, client):
        product = client.post('/api/v1/products', json={
            'sku': 'SKU-BALANCE',
            'name': 'Balance Product'
        }).get_json()['data']
        warehouse = client.post('/api/v1/warehouses', json={
            'code': 'WH-BALANCE',
            'name': 'Balance Warehouse'
        }).get_json()['data']
        created = client.post('/api/v1/inventory/balances', json={
            'product_id': product['id'],
            'warehouse_id': warehouse['id'],
            'quantity_on_hand': 10,
            'average_cost': 4.5
        })
        assert created.status_code == 201
        balance = created.get_json()['data']
        assert balance['quantity_available'] == 10
        assert balance['total_value'] == 45
        assert 'is_active' not in balance
        assert 'created_at' not in balance

        with client.application.app_context():
            row = db.session.get(InventoryBalance, balance['id'])
            row.quantity_reserved = 3
            db.session.commit()

        refreshed = client.get(
            f"/api/v1/inventory/balances/{balance['id']}"
        ).get_json()['data']
        assert refreshed['quantity_available'] == 7
        assert refreshed['total_value'] == 45