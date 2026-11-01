"""Comprehensive tests for Error Handling Standardization & Sanitization (P1.3).

Validates:
1. Standardized JSON error response format across all status codes (400, 401, 403, 404, 405, 409, 500).
2. Exception sanitization: no internal tracebacks, SQL strings, or system paths leaked to client.
3. Database rollback execution on 500 errors.
4. Malformed JSON handling: BadRequest returns 400 without masking as 500.
"""

import pytest
from app import db
from app.models import Product, User
from app.routes.identity.auth import generate_token


def test_404_not_found_standardized_format(client):
    """Test 404 response on non-existent endpoints outside and inside API prefix."""
    # 1. Non-existent route outside /api/v1/
    resp_outside = client.get("/non-existent-endpoint-page")
    assert resp_outside.status_code == 404
    assert resp_outside.content_type.startswith("application/json")
    data_outside = resp_outside.get_json()
    assert "error" in data_outside
    assert data_outside["code"] == 404
    assert data_outside["status"] == "Not Found"

    # 2. Non-existent route inside /api/v1/ with authenticated client
    resp_inside = client.get("/api/v1/non-existent-resource-endpoint")
    assert resp_inside.status_code == 404
    assert resp_inside.content_type.startswith("application/json")
    data_inside = resp_inside.get_json()
    assert "error" in data_inside
    assert data_inside["code"] == 404
    assert data_inside["status"] == "Not Found"

    # 3. get_or_404 on valid route with non-existent ID
    resp_product = client.get("/api/v1/products/999999")
    assert resp_product.status_code == 404
    assert resp_product.content_type.startswith("application/json")
    data_product = resp_product.get_json()
    assert "error" in data_product
    assert data_product["code"] == 404


def test_405_method_not_allowed_standardized_format(client):
    """Test 405 response on invalid HTTP methods for public and authenticated routes."""
    # 1. Public route with unallowed method (POST to GET-only /api/v1/health)
    resp_health = client.post("/api/v1/health")
    assert resp_health.status_code == 405
    assert resp_health.content_type.startswith("application/json")
    data_health = resp_health.get_json()
    assert "error" in data_health
    assert data_health["code"] == 405
    assert data_health["status"] == "Method Not Allowed"

    # 2. Authenticated route with unallowed method (POST to GET-only /api/v1/products/<id>)
    resp_prod = client.post("/api/v1/products/1")
    assert resp_prod.status_code == 405
    assert resp_prod.content_type.startswith("application/json")
    data_prod = resp_prod.get_json()
    assert "error" in data_prod
    assert data_prod["code"] == 405
    assert data_prod["status"] == "Method Not Allowed"


def test_400_malformed_json_handling(client):
    """Test malformed JSON syntax correctly returns 400 Bad Request instead of 500."""
    # 1. Malformed JSON string to POST /api/v1/products
    resp_malformed = client.post(
        "/api/v1/products",
        data="{invalid_json_content",
        content_type="application/json"
    )
    assert resp_malformed.status_code == 400
    assert resp_malformed.content_type.startswith("application/json")
    data_malformed = resp_malformed.get_json()
    assert "error" in data_malformed
    assert data_malformed["code"] == 400
    assert data_malformed["status"] == "Bad Request"

    # 2. Malformed JSON to /api/v1/auth/login
    resp_login = client.post(
        "/api/v1/auth/login",
        data="[bad: json}",
        content_type="application/json"
    )
    assert resp_login.status_code == 400
    data_login = resp_login.get_json()
    assert "error" in data_login
    assert data_login["code"] == 400

    # 3. Non-dict JSON payload (JSON array instead of JSON object)
    resp_array = client.post(
        "/api/v1/products",
        json=["item1", "item2"]
    )
    assert resp_array.status_code == 400
    data_array = resp_array.get_json()
    assert "error" in data_array
    assert "JSON object is required" in data_array["error"]


def test_401_and_403_standardized_format(app, client):
    """Test 401 Unauthorized and 403 Forbidden return standardized error JSON."""
    with app.app_context():
        # Unauthenticated request to protected endpoint
        unauth_client = app.test_client()
        resp_unauth = unauth_client.get("/api/v1/products")
        assert resp_unauth.status_code == 401
        data_unauth = resp_unauth.get_json()
        assert "error" in data_unauth
        assert data_unauth["error"] == "Authentication required"

        # Invalid token request
        resp_bad_token = unauth_client.get(
            "/api/v1/products",
            headers={"Authorization": "Bearer invalid.token.payload"}
        )
        assert resp_bad_token.status_code == 401
        data_bad_token = resp_bad_token.get_json()
        assert "error" in data_bad_token
        assert "Invalid or expired token" in data_bad_token["error"]

        # 403 Forbidden: create user with role 'viewer' (no products.create permission)
        viewer = User(
            username="viewer_err_test",
            email="viewer_err@example.com",
            role="viewer",
            all_warehouses=True
        )
        viewer.set_password("viewerpass12345")
        db.session.add(viewer)
        db.session.commit()
        viewer_token = generate_token(viewer.id)

        resp_forbidden = client.post(
            "/api/v1/products",
            headers={"Authorization": f"Bearer {viewer_token}"},
            json={"sku": "ERR-P1", "name": "Error Test Product"}
        )
        assert resp_forbidden.status_code == 403
        data_forbidden = resp_forbidden.get_json()
        assert "error" in data_forbidden
        assert "Insufficient permissions" in data_forbidden["error"]


def test_409_conflict_standardized_format(client):
    """Test 409 Conflict return standardized error JSON."""
    # Create product
    res1 = client.post(
        "/api/v1/products",
        json={"sku": "SKU-DUP-1", "name": "Original Product"}
    )
    assert res1.status_code == 201

    # Attempt to create product with duplicate SKU
    res2 = client.post(
        "/api/v1/products",
        json={"sku": "SKU-DUP-1", "name": "Duplicate Product"}
    )
    assert res2.status_code == 409
    data_dup = res2.get_json()
    assert "error" in data_dup
    assert "SKU already exists" in data_dup["error"]


def test_route_level_error_responses_include_code_and_status(client):
    """Route-level {'error': ...} payloads are normalized to the global envelope."""
    client.post(
        '/api/v1/products',
        json={'sku': 'ERR-NORMALIZED', 'name': 'Normalized Product'}
    )
    response = client.post(
        '/api/v1/products',
        json={'sku': 'ERR-NORMALIZED', 'name': 'Duplicate Product'}
    )
    assert response.status_code == 409
    data = response.get_json()
    assert data['error'] == 'SKU already exists'
    assert data['code'] == 409
    assert data['status'] == 'Conflict'


def test_500_sanitization_and_session_rollback():
    """Test that unhandled exceptions are completely sanitized and roll back db session."""
    from app import create_app
    from config import Config

    class ErrorTestConfig(Config):
        TESTING = True
        SECRET_KEY = "test-secret-key"
        JWT_SECRET_KEY = "test-jwt-secret"
        SQLALCHEMY_DATABASE_URI = "sqlite://"
        RATELIMIT_ENABLED = False

    test_app = create_app(ErrorTestConfig)

    @test_app.route("/test-simulated-crash", methods=["POST"])
    def simulated_crash():
        # Dirty the session before crash
        dirty_product = Product(sku="DIRTY-ROLLBACK-SKU", name="Dirty", is_active=True)
        db.session.add(dirty_product)
        # Simulate unexpected crash with sensitive internal details
        raise RuntimeError(
            "CRITICAL_DATABASE_FAILURE: password='super_secret_db_pass' at /internal/core/engine.py:42"
        )

    with test_app.app_context():
        db.create_all()

    test_client = test_app.test_client()
    resp = test_client.post("/test-simulated-crash")
    assert resp.status_code == 500
    assert resp.content_type.startswith("application/json")
    data = resp.get_json()

    # 1. Standardized JSON structure
    assert data["code"] == 500
    assert data["error"] == "Internal server error"
    assert data["status"] == "Internal Server Error"

    # 2. Sanitization: ensure no leaked credentials, file paths, or exception details
    raw_response_text = resp.get_data(as_text=True)
    assert "super_secret_db_pass" not in raw_response_text
    assert "CRITICAL_DATABASE_FAILURE" not in raw_response_text
    assert "engine.py" not in raw_response_text
    assert "Traceback" not in raw_response_text

    # 3. Session rollback verification: dirty_product must NOT be committed to the database
    with test_app.app_context():
        persisted = Product.query.filter_by(sku="DIRTY-ROLLBACK-SKU").first()
        assert persisted is None
