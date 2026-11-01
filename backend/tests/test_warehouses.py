"""Warehouses tests."""
class TestWarehouses:
    def test_get_warehouses(self, client):
        resp = client.get('/api/v1/warehouses')
        assert resp.status_code == 200

    def test_create_warehouse(self, client):
        resp = client.post('/api/v1/warehouses', json={
            'code': 'WH-001',
            'name': 'Main Warehouse',
            'location': 'Jakarta'
        })
        assert resp.status_code == 201

    def test_create_warehouse_duplicate_code(self, client):
        """Test create with duplicate code."""
        # First create a warehouse
        client.post('/api/v1/warehouses', json={
            'code': 'WH-DUP1',
            'name': 'Duplicate Warehouse',
            'location': 'First'
        })
        # Duplicate warehouse codes are rejected.
        resp = client.post('/api/v1/warehouses', json={
            'code': 'WH-DUP1',
            'name': 'Duplicate Warehouse 2',
            'location': 'Second'
        })
        assert resp.status_code == 409

    def test_create_warehouse_different(self, client):
        """Test create warehouse with different data."""
        resp = client.post('/api/v1/warehouses', json={
            'code': 'WH-002',
            'name': 'Second Warehouse',
            'location': 'Surabaya'
        })
        assert resp.status_code == 201