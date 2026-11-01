from app import db
from app.models import AuditLog


def test_api_info_returns_endpoint_metadata(client):
    response = client.get('/api/v1/api-info')
    data = response.get_json()

    assert response.status_code == 200
    assert data['name'] == 'DistribuFlow ERP API'
    assert data['total_endpoints'] > 0


def test_health_check_reports_database_availability(client):
    response = client.get('/api/v1/health')
    assert response.status_code == 200
    assert response.get_json() == {
        'status': 'healthy',
        'database': 'available'
    }


def test_rate_limit_defaults_allow_dashboard_polling(client):
    limits = client.application.config['RATELIMIT_DEFAULT_LIMITS']
    assert '2000 per hour' in limits
    assert '20000 per day' in limits


def test_cors_origins_are_configurable(client):
    assert client.application.config['CORS_ORIGINS'] == ['*']
    response = client.get(
        '/api/v1/health',
        headers={'Origin': 'http://localhost:5173'}
    )
    assert response.headers['Access-Control-Allow-Origin'] in {
        '*', 'http://localhost:5173'
    }


def test_successful_mutations_are_written_to_audit_log(client):
    response = client.post('/api/v1/categories', json={'name': 'Audited Category'})
    assert response.status_code == 201
    with client.application.app_context():
        event = AuditLog.query.order_by(AuditLog.id.desc()).first()
        assert event is not None
        assert event.endpoint == 'categories.create_category'
        assert event.action == 'POST'
        assert event.status_code == 201
