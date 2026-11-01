"""Statistics & Dashboard tests."""
class TestStatistics:
    def test_get_statistics(self, client):
        resp = client.get('/api/v1/statistics')
        assert resp.status_code == 200

    def test_statistics_has_valid_json(self, client):
        """Test statistics response is valid JSON."""
        resp = client.get('/api/v1/statistics')
        data = resp.get_json()
        assert data is not None

class TestDashboard:
    def test_get_dashboard(self, client):
        resp = client.get('/api/v1/dashboard')
        assert resp.status_code == 200

    def test_dashboard_has_valid_json(self, client):
        """Test dashboard response is valid JSON."""
        resp = client.get('/api/v1/dashboard')
        data = resp.get_json()
        assert data is not None