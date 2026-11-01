"""Categories tests."""
class TestCategories:
    def test_get_categories(self, client):
        resp = client.get('/api/v1/categories')
        assert resp.status_code == 200

    def test_create_category(self, client):
        resp = client.post('/api/v1/categories', json={
            'name': 'Test Category',
            'description': 'Test description'
        })
        assert resp.status_code == 201
        category = resp.get_json()['data']
        assert category['created_at']
        assert category['updated_at']

    def test_create_duplicate_category(self, client):
        """Test create fails with duplicate name."""
        client.post('/api/v1/categories', json={
            'name': 'Duplicate Category',
            'description': 'First'
        })
        resp = client.post('/api/v1/categories', json={
            'name': 'Duplicate Category',
            'description': 'Second'
        })
        assert resp.status_code == 409