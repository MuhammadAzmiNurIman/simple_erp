"""Units tests."""
class TestUnits:
    def test_get_units(self, client):
        resp = client.get('/api/v1/units')
        assert resp.status_code == 200

    def test_create_unit(self, client):
        resp = client.post('/api/v1/units', json={
            'name': 'Boxes',
            'description': 'Carton boxes'
        })
        assert resp.status_code == 201
        unit = resp.get_json()['data']
        assert unit['created_at']
        assert unit['updated_at']

    def test_create_duplicate_unit(self, client):
        """Test create fails with duplicate name."""
        client.post('/api/v1/units', json={
            'name': 'Duplicate Unit',
            'description': 'First'
        })
        resp = client.post('/api/v1/units', json={
            'name': 'Duplicate Unit',
            'description': 'Second'
        })
        assert resp.status_code == 409