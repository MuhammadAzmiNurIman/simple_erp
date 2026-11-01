"""Conftest for DistribuFlow ERP API tests."""
import pytest
from app import create_app, db
from app.authorization import seed_authorization
from app.models import User
from app.routes.identity.auth import generate_token
from config import Config


class TestConfig(Config):
    """Configuration backed by an isolated in-memory database."""

    TESTING = True
    SECRET_KEY = 'test-secret-key'
    JWT_SECRET_KEY = 'test-jwt-secret-key-for-automated-tests'
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    CORS_ORIGINS = ['*']
    RATELIMIT_ENABLED = False


@pytest.fixture(scope='module')
def app():
    """Create Flask app for testing."""
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
    yield app


@pytest.fixture
def reset_database(app):
    """Reset only the isolated test database and seed an authenticated admin."""
    with app.app_context():
        db.drop_all()
        db.create_all()
        seed_authorization()
        admin = User(
            username='test-admin',
            email='test-admin@example.com',
            role='admin',
            all_warehouses=True
        )
        admin.set_password('test-admin-password')
        db.session.add(admin)
        db.session.commit()
        return {'Authorization': f'Bearer {generate_token(admin.id)}'}


@pytest.fixture
def client(app, reset_database):
    """Create a client authenticated as an admin for protected API tests."""
    with app.test_client() as test_client:
        test_client.environ_base['HTTP_AUTHORIZATION'] = reset_database['Authorization']
        yield test_client
