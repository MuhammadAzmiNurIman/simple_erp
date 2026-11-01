"""Products tests."""
class TestProducts:
    def test_get_products(self, client):
        resp = client.get('/api/v1/products')
        assert resp.status_code == 200

    def test_create_product(self, client):
        # First create dependencies
        client.post('/api/v1/categories', json={'name': 'Test Category', 'description': 'Test'})
        client.post('/api/v1/units', json={'name': 'pcs', 'description': 'Pieces'})
        client.post('/api/v1/warehouses', json={'name': 'Test Warehouse', 'location': 'Jakarta'})
        
        resp = client.post('/api/v1/products', json={
            'sku': 'SKU-001',
            'name': 'Test Product',
            'price': 99.99,
            'category_id': 1,
            'unit_id': 1,
            'warehouse_id': 1,
            'stock': 10,
            'min_stock': 2
        })
        assert resp.status_code == 201
        product = resp.get_json()['data']
        assert product['created_at']
        assert product['updated_at']

    def test_create_product_rejects_negative_minimum_stock(self, client):
        resp = client.post('/api/v1/products', json={
            'sku': 'SKU-002',
            'name': 'Another Product',
            'min_stock': -5
        })
        assert resp.status_code == 400