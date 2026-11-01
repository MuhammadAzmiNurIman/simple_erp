"""Authentication and role-based access tests."""

import pytest

from app import db
from app.models import Permission, Role, User, UserWarehouseAccess, Warehouse
from app.routes.identity.auth import generate_token
from app.authorization import (
    ROLE_DEFAULTS,
    required_permission,
    seed_authorization,
    sync_system_role_permissions,
)


def create_user(app, username, email, password, role='operator', all_warehouses=False):
    with app.app_context():
        user = User(
            username=username,
            email=email,
            role=role,
            all_warehouses=all_warehouses,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user.id


class TestAuth:
    def test_profile_can_be_updated_with_current_password(self, client):
        create_user(
            client.application,
            'profile-user',
            'profile-user@example.com',
            'current-password-123',
            role='operator'
        )
        login = client.post('/api/v1/auth/login', json={
            'username': 'profile-user',
            'password': 'current-password-123'
        }).get_json()['data']
        headers = {'Authorization': f"Bearer {login['token']}"}

        response = client.patch('/api/v1/auth/me', headers=headers, json={
            'username': 'updated-profile',
            'email': 'updated-profile@example.com',
            'current_password': 'current-password-123',
        })

        assert response.status_code == 200
        assert response.get_json()['data']['username'] == 'updated-profile'
        assert response.get_json()['data']['email'] == 'updated-profile@example.com'
        assert client.get('/api/v1/auth/me', headers=headers).get_json()['data']['username'] == 'updated-profile'

    def test_profile_update_rejects_wrong_password_and_duplicate_email(self, client):
        create_user(
            client.application,
            'profile-user',
            'profile-user@example.com',
            'current-password-123',
            role='operator'
        )
        create_user(
            client.application,
            'profile-other',
            'taken@example.com',
            'other-password-123',
            role='operator'
        )
        login = client.post('/api/v1/auth/login', json={
            'username': 'profile-user',
            'password': 'current-password-123'
        }).get_json()['data']
        headers = {'Authorization': f"Bearer {login['token']}"}

        wrong_password = client.patch('/api/v1/auth/me', headers=headers, json={
            'username': 'should-not-change',
            'current_password': 'wrong-password',
        })
        duplicate_email = client.patch('/api/v1/auth/me', headers=headers, json={
            'email': 'taken@example.com',
            'current_password': 'current-password-123',
        })

        assert wrong_password.status_code == 403
        assert duplicate_email.status_code == 409
        assert client.get('/api/v1/auth/me', headers=headers).get_json()['data']['username'] == 'profile-user'

    def test_password_change_rotates_and_revokes_current_session(self, client):
        create_user(
            client.application,
            'password-user',
            'password-user@example.com',
            'current-password-123',
            role='operator'
        )
        login = client.post('/api/v1/auth/login', json={
            'username': 'password-user',
            'password': 'current-password-123'
        }).get_json()['data']
        headers = {'Authorization': f"Bearer {login['token']}"}

        response = client.patch('/api/v1/auth/me', headers=headers, json={
            'current_password': 'current-password-123',
            'new_password': 'new-password-456',
            'refresh_token': login['refresh_token'],
        })

        assert response.status_code == 200
        updated = response.get_json()['data']
        assert updated['token'] != login['token']
        assert updated['refresh_token'] != login['refresh_token']
        assert client.get('/api/v1/auth/me', headers=headers).status_code == 401
        assert client.get(
            '/api/v1/auth/me',
            headers={'Authorization': f"Bearer {updated['token']}"}
        ).status_code == 200
        assert client.post('/api/v1/auth/refresh', json={
            'refresh_token': login['refresh_token']
        }).status_code == 401
        assert client.post('/api/v1/auth/login', json={
            'username': 'password-user',
            'password': 'new-password-456'
        }).status_code == 200

    def test_profile_permission_cannot_be_removed_from_roles(self, client):
        admin_id = create_user(
            client.application,
            'profile-role-admin',
            'profile-role-admin@example.com',
            'test-password',
            role='admin'
        )
        with client.application.app_context():
            token = generate_token(admin_id)
        response = client.put(
            '/api/v1/roles/operator/permissions',
            json={'permissions': ['inventory.read']},
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        assert 'profile.read' in response.get_json()['data']['permissions']

    def test_profile_update_validates_fields_and_password_changes(self, client):
        user_id = create_user(
            client.application,
            'profile-validation',
            'profile-validation@example.com',
            'current-password-123',
            role='operator'
        )
        with client.application.app_context():
            token = generate_token(user_id)
        headers = {'Authorization': f'Bearer {token}'}
        invalid_email = client.patch('/api/v1/auth/me', headers=headers, json={
            'email': 'not-an-email',
            'current_password': 'current-password-123',
        })
        unknown_field = client.patch('/api/v1/auth/me', headers=headers, json={
            'username': 'profile-validation',
            'current_password': 'current-password-123',
            'is_admin': True,
        })
        short_password = client.patch('/api/v1/auth/me', headers=headers, json={
            'new_password': 'short',
            'current_password': 'current-password-123',
            'refresh_token': 'unused',
        })
        same_password = client.patch('/api/v1/auth/me', headers=headers, json={
            'new_password': 'current-password-123',
            'current_password': 'current-password-123',
            'refresh_token': 'unused',
        })

        assert invalid_email.status_code == 400
        assert unknown_field.status_code == 400
        assert short_password.status_code == 400
        assert same_password.status_code == 400

    def test_profile_endpoint_requires_profile_permission(self, client):
        user_id = create_user(
            client.application,
            'profile-denied',
            'profile-denied@example.com',
            'current-password-123',
            role='operator'
        )
        with client.application.app_context():
            token = generate_token(user_id)
            role = db.session.get(Role, 'operator')
            role.permissions = [
                permission for permission in role.permissions
                if permission.code != 'profile.read'
            ]
            db.session.commit()

        response = client.get(
            '/api/v1/auth/me',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 403

    def test_public_registration_is_disabled(self, client):
        response = client.post('/api/v1/auth/register', json={
            'username': 'new-user',
            'email': 'new-user@example.com',
            'password': 'test-password',
            'role': 'admin'
        })

        assert response.status_code == 403
        with client.application.app_context():
            assert User.query.filter_by(username='new-user').first() is None

    def test_login_success(self, client):
        create_user(
            client.application,
            'logint',
            'login@example.com',
            'pass123',
            role='admin'
        )
        response = client.post('/api/v1/auth/login', json={
            'username': 'logint',
            'password': 'pass123'
        })
        assert response.status_code == 200
        data = response.get_json()['data']
        assert data['token']
        assert 'sales_orders.read' in data['permissions']
        assert 'roles.manage' in data['permissions']
        assert data['token_type'] == 'Bearer'
        assert data['expires_in'] == 3600
        assert data['refresh_token']
        assert data['refresh_expires_in'] == 7 * 24 * 3600

    def test_current_user_includes_effective_permissions(self, client):
        create_user(
            client.application,
            'permission-user',
            'permission@example.com',
            'pass123',
            role='admin'
        )
        login = client.post('/api/v1/auth/login', json={
            'username': 'permission-user',
            'password': 'pass123'
        }).get_json()['data']

        response = client.get(
            '/api/v1/auth/me',
            headers={'Authorization': f"Bearer {login['token']}"}
        )

        assert response.status_code == 200
        permissions = response.get_json()['data']['permissions']
        assert 'sales_orders.read' in permissions
        assert 'roles.manage' in permissions

    def test_refresh_rotates_tokens(self, client):
        create_user(
            client.application,
            'refresht',
            'refresh@example.com',
            'test-password',
            role='admin'
        )
        login = client.post('/api/v1/auth/login', json={
            'username': 'refresht',
            'password': 'test-password'
        }).get_json()['data']

        response = client.post('/api/v1/auth/refresh', json={
            'refresh_token': login['refresh_token']
        })
        assert response.status_code == 200
        refreshed = response.get_json()['data']
        assert refreshed['token'] != login['token']
        assert refreshed['refresh_token'] != login['refresh_token']
        assert refreshed['token_type'] == 'Bearer'
        assert refreshed['expires_in'] == 3600
        assert client.get(
            '/api/v1/auth/me',
            headers={'Authorization': f"Bearer {refreshed['token']}"}
        ).status_code == 200
        assert client.post('/api/v1/auth/refresh', json={
            'refresh_token': login['refresh_token']
        }).status_code == 401

    def test_refresh_rejects_access_token(self, client):
        create_user(
            client.application,
            'refresh-access',
            'refresh-access@example.com',
            'test-password',
            role='admin'
        )
        login = client.post('/api/v1/auth/login', json={
            'username': 'refresh-access',
            'password': 'test-password'
        }).get_json()['data']
        response = client.post('/api/v1/auth/refresh', json={
            'refresh_token': login['token']
        })
        assert response.status_code == 401

    def test_refresh_token_cannot_access_api(self, client):
        create_user(
            client.application,
            'refresh-api',
            'refresh-api@example.com',
            'test-password',
            role='admin'
        )
        login = client.post('/api/v1/auth/login', json={
            'username': 'refresh-api',
            'password': 'test-password'
        }).get_json()['data']
        response = client.get(
            '/api/v1/products',
            headers={'Authorization': f"Bearer {login['refresh_token']}"}
        )
        assert response.status_code == 401

    def test_refresh_requires_token(self, client):
        response = client.post(
            '/api/v1/auth/refresh',
            json={},
            headers={'Authorization': ''}
        )
        assert response.status_code == 400

    def test_logout_revokes_refresh_token(self, client):
        create_user(
            client.application,
            'logout-refresh',
            'logout-refresh@example.com',
            'test-password',
            role='admin'
        )
        login = client.post('/api/v1/auth/login', json={
            'username': 'logout-refresh',
            'password': 'test-password'
        }).get_json()['data']
        headers = {'Authorization': f"Bearer {login['token']}"}
        assert client.post(
            '/api/v1/auth/logout',
            json={'refresh_token': login['refresh_token']},
            headers=headers
        ).status_code == 200
        assert client.post('/api/v1/auth/refresh', json={
            'refresh_token': login['refresh_token']
        }).status_code == 401

    def test_login_failed(self, client):
        create_user(
            client.application,
            'failt',
            'fail@example.com',
            'password123',
            role='viewer'
        )
        response = client.post('/api/v1/auth/login', json={
            'username': 'failt',
            'password': 'wrongpassword'
        })
        assert response.status_code == 401

    def test_me_with_valid_token(self, client, valid_token_header):
        response = client.get('/api/v1/auth/me', headers=valid_token_header)
        assert response.status_code == 200

    def test_me_without_token(self, client):
        response = client.get(
            '/api/v1/auth/me',
            headers={'Authorization': ''}
        )
        assert response.status_code == 401

    def test_business_api_requires_authentication(self, client):
        response = client.get(
            '/api/v1/products',
            headers={'Authorization': ''}
        )
        assert response.status_code == 401

    def test_viewer_can_read_but_cannot_write(self, client):
        viewer_id = create_user(
            client.application,
            'test-viewer',
            'test-viewer@example.com',
            'test-viewer-password',
            role='viewer'
        )
        with client.application.app_context():
            viewer_token = generate_token(viewer_id)

        headers = {'Authorization': f'Bearer {viewer_token}'}
        assert client.get('/api/v1/categories', headers=headers).status_code == 200
        assert client.post(
            '/api/v1/categories',
            json={'name': 'Forbidden Category'},
            headers=headers
        ).status_code == 403

    def test_create_admin_cli(self, client):
        result = client.application.test_cli_runner().invoke(
            args=['create-admin'],
            input=(
                'cli-admin\n'
                'cli-admin@example.com\n'
                'Strong-test-password-123!\n'
                'Strong-test-password-123!\n'
            )
        )
        assert result.exit_code == 0
        with client.application.app_context():
            created = User.query.filter_by(username='cli-admin').first()
            assert created is not None
            assert created.role == 'admin'

    def test_create_operator_cli(self, client):
        with client.application.app_context():
            db.session.add(Warehouse(code='WH-CLI', name='CLI Test Warehouse'))
            db.session.commit()
        result = client.application.test_cli_runner().invoke(
            args=['create-user', '--role', 'operator'],
            input=(
                'cli-operator\n'
                'cli-operator@example.com\n'
                'Strong-test-password-123!\n'
                'Strong-test-password-123!\n'
            )
        )
        assert result.exit_code == 0
        with client.application.app_context():
            created = User.query.filter_by(username='cli-operator').first()
            assert created is not None
            assert created.role == 'operator'

    def test_admin_can_access_finance_posting_permission(self, client):
        supplier = client.post('/api/v1/suppliers', json={
            'name': 'Admin Finance Supplier',
        }).get_json()['data']
        user_id = create_user(
            client.application,
            'permission-admin',
            'permission-admin@example.com',
            'test-password',
            role='admin'
        )
        with client.application.app_context():
            token = generate_token(user_id)
        response = client.post(
            '/api/v1/supplier-payments',
            json={'supplier_id': supplier['id'], 'amount': 1},
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 201

    def test_warehouse_role_cannot_read_an_unassigned_warehouse(self, client):
        warehouses = []
        for suffix in ('A', 'B'):
            warehouse = client.post('/api/v1/warehouses', json={
                'code': f'WH-SCOPE-{suffix}',
                'name': f'Scope Warehouse {suffix}'
            }).get_json()['data']
            warehouses.append(warehouse)
        product = client.post('/api/v1/products', json={
            'sku': 'SKU-SCOPE',
            'name': 'Scoped Product',
            'min_stock': 0
        }).get_json()['data']
        balances = [
            client.post('/api/v1/inventory/balances', json={
                'product_id': product['id'],
                'warehouse_id': warehouse['id'],
                'quantity_on_hand': 5
            }).get_json()['data']
            for warehouse in warehouses
        ]
        with client.application.app_context():
            user = User(
                username='scoped-warehouse',
                email='scoped-warehouse@example.com',
                role='warehouse'
            )
            user.set_password('test-password')
            user.warehouse_access.append(
                UserWarehouseAccess(warehouse_id=warehouses[0]['id'])
            )
            db.session.add(user)
            db.session.commit()
            token = generate_token(user.id)
        headers = {'Authorization': f'Bearer {token}'}

        assert client.get(
            f"/api/v1/inventory/balances?warehouse_id={warehouses[0]['id']}",
            headers=headers
        ).status_code == 200
        assert client.get(
            f"/api/v1/inventory/balances?warehouse_id={warehouses[1]['id']}",
            headers=headers
        ).status_code == 403
        assert client.get('/api/v1/inventory/balances', headers=headers).status_code == 403
        assert client.get(
            f"/api/v1/inventory/balances/{balances[1]['id']}",
            headers=headers
        ).status_code == 403
        assert client.get(
            f"/api/v1/inventory/balances/{balances[1]['id']}?warehouse_id={warehouses[0]['id']}",
            headers=headers
        ).status_code == 403

    def test_registered_api_routes_have_permission_definitions(self, client):
        public_endpoints = {
            'auth.login', 'auth.register', 'auth.refresh', 'api_info.health_check',
            'openapi.openapi_spec',
        }
        with client.application.app_context():
            for rule in client.application.url_map.iter_rules():
                if not rule.rule.startswith('/api/v1/'):
                    continue
                for method in rule.methods - {'OPTIONS'}:
                    permission_code = required_permission(rule.endpoint, method)
                    assert rule.endpoint in public_endpoints or permission_code, (
                        rule.endpoint, method
                    )
                    if permission_code:
                        assert db.session.get(Permission, permission_code), (
                            rule.endpoint, method, permission_code
                        )

    def test_prd_canonical_api_routes_are_registered(self, client):
        required_routes = {
            ('/api/v1/products', 'GET'),
            ('/api/v1/products', 'POST'),
            ('/api/v1/products/<int:product_id>', 'GET'),
            ('/api/v1/products/<int:product_id>', 'PATCH'),
            ('/api/v1/categories', 'GET'),
            ('/api/v1/categories', 'POST'),
            ('/api/v1/units', 'GET'),
            ('/api/v1/units', 'POST'),
            ('/api/v1/suppliers', 'GET'),
            ('/api/v1/suppliers', 'POST'),
            ('/api/v1/suppliers/<int:supplier_id>', 'GET'),
            ('/api/v1/suppliers/<int:supplier_id>', 'PATCH'),
            ('/api/v1/customers', 'GET'),
            ('/api/v1/customers', 'POST'),
            ('/api/v1/customers/<int:customer_id>', 'GET'),
            ('/api/v1/customers/<int:customer_id>', 'PATCH'),
            ('/api/v1/warehouses', 'GET'),
            ('/api/v1/warehouses', 'POST'),
            ('/api/v1/warehouses/<int:warehouse_id>', 'GET'),
            ('/api/v1/warehouses/<int:warehouse_id>', 'PATCH'),
            ('/api/v1/inventory/balances', 'GET'),
            ('/api/v1/inventory/movements', 'GET'),
            ('/api/v1/inventory/low-stock', 'GET'),
            ('/api/v1/inventory/adjustments', 'GET'),
            ('/api/v1/inventory/adjustments', 'POST'),
            ('/api/v1/inventory/adjustments/<int:adjuster_id>/approve', 'POST'),
            ('/api/v1/inventory/adjustments/<int:adjuster_id>/post', 'POST'),
            ('/api/v1/inventory/transfers', 'GET'),
            ('/api/v1/inventory/transfers', 'POST'),
            ('/api/v1/inventory/transfers/<int:transfer_id>', 'GET'),
            ('/api/v1/inventory/transfers/<int:transfer_id>/submit', 'POST'),
            ('/api/v1/inventory/transfers/<int:transfer_id>/approve', 'POST'),
            ('/api/v1/inventory/transfers/<int:transfer_id>/post', 'POST'),
            ('/api/v1/purchase-orders', 'GET'),
            ('/api/v1/purchase-orders', 'POST'),
            ('/api/v1/purchase-orders/<int:po_id>', 'GET'),
            ('/api/v1/purchase-orders/<int:po_id>/submit', 'POST'),
            ('/api/v1/purchase-orders/<int:po_id>/approve', 'POST'),
            ('/api/v1/purchase-orders/<int:po_id>/cancel', 'POST'),
            ('/api/v1/goods-receipts', 'GET'),
            ('/api/v1/goods-receipts', 'POST'),
            ('/api/v1/goods-receipts/<int:receipt_id>', 'GET'),
            ('/api/v1/goods-receipts/<int:receipt_id>/post', 'POST'),
            ('/api/v1/vendor-bills', 'GET'),
            ('/api/v1/vendor-bills', 'POST'),
            ('/api/v1/sales-orders', 'GET'),
            ('/api/v1/sales-orders', 'POST'),
            ('/api/v1/sales-orders/<int:so_id>', 'GET'),
            ('/api/v1/sales-orders/<int:so_id>/submit', 'POST'),
            ('/api/v1/sales-orders/<int:so_id>/approve', 'POST'),
            ('/api/v1/sales-orders/<int:so_id>/reserve', 'POST'),
            ('/api/v1/sales-orders/<int:so_id>/cancel', 'POST'),
            ('/api/v1/shipments', 'GET'),
            ('/api/v1/shipments', 'POST'),
            ('/api/v1/shipments/<int:shipment_id>', 'GET'),
            ('/api/v1/shipments/<int:shipment_id>/post', 'POST'),
            ('/api/v1/sales-invoices', 'GET'),
            ('/api/v1/sales-invoices', 'POST'),
            ('/api/v1/sales-returns', 'GET'),
            ('/api/v1/sales-returns', 'POST'),
            ('/api/v1/sales-returns/<int:return_id>', 'GET'),
            ('/api/v1/sales-returns/<int:return_id>/post', 'POST'),
            ('/api/v1/customer-payments', 'GET'),
            ('/api/v1/customer-payments', 'POST'),
            ('/api/v1/customer-payments/<int:payment_id>/post', 'POST'),
            ('/api/v1/vendor-bills', 'GET'),
            ('/api/v1/vendor-bills', 'POST'),
            ('/api/v1/customer-payments/<int:payment_id>/allocations', 'POST'),
            ('/api/v1/supplier-payments', 'GET'),
            ('/api/v1/supplier-payments', 'POST'),
            ('/api/v1/supplier-payments/<int:payment_id>/post', 'POST'),
            ('/api/v1/supplier-payments/<int:payment_id>/allocations', 'POST'),
            ('/api/v1/finance/receivables', 'GET'),
            ('/api/v1/finance/payables', 'GET'),
            ('/api/v1/finance/cash-summary', 'GET'),
            ('/api/v1/dashboard/summary', 'GET'),
            ('/api/v1/reports/sales', 'GET'),
            ('/api/v1/reports/purchases', 'GET'),
            ('/api/v1/reports/inventory', 'GET'),
            ('/api/v1/reports/stock-movements', 'GET'),
            ('/api/v1/reports/receivables', 'GET'),
            ('/api/v1/reports/payables', 'GET'),
            ('/api/v1/audit-logs', 'GET'),
        }
        registered = {
            (rule.rule, method)
            for rule in client.application.url_map.iter_rules()
            for method in rule.methods - {'OPTIONS', 'HEAD'}
        }
        assert required_routes <= registered

    def test_openapi_spec_documents_every_registered_api_operation(self, client):
        import re

        response = client.get('/api/v1/openapi.json')
        assert response.status_code == 200
        spec = response.get_json()
        assert spec['openapi'] == '3.1.0'
        assert 'BearerAuth' in spec['components']['securitySchemes']

        documented = {
            (f"/api/v1{path}", method.upper())
            for path, operations in spec['paths'].items()
            for method in operations
        }
        registered = {
            (
                re.sub(
                    r'<(?:(?:[^:<>]+):)?([^<>]+)>',
                    r'{\1}',
                    rule.rule
                ),
                method
            )
            for rule in client.application.url_map.iter_rules()
            if rule.rule.startswith('/api/v1/')
            and rule.endpoint != 'auth.register'
            for method in rule.methods - {'OPTIONS', 'HEAD'}
        }
        assert documented == registered
        operation_ids = [
            operation['operationId']
            for operations in spec['paths'].values()
            for operation in operations.values()
        ]
        assert len(operation_ids) == len(set(operation_ids))

        def find_refs(value):
            if isinstance(value, dict):
                for key, nested in value.items():
                    if key == '$ref':
                        yield nested
                    else:
                        yield from find_refs(nested)
            elif isinstance(value, list):
                for nested in value:
                    yield from find_refs(nested)

        for reference in find_refs(spec):
            parts = reference.split('/')
            assert parts[:2] == ['#', 'components']
            assert len(parts) == 4
            _, _, component_type, component_name = parts
            assert component_name in spec['components'][component_type]

        create_order = spec['paths']['/sales-orders']['post']
        assert create_order['requestBody']['content']['application/json']['schema'] == {
            '$ref': '#/components/schemas/SalesOrderCreate'
        }
        assert create_order['security'] == [{'BearerAuth': []}]
        create_return = spec['paths']['/sales-returns']['post']
        assert create_return['requestBody']['content']['application/json']['schema'] == {
            '$ref': '#/components/schemas/SalesReturnCreate'
        }
        vendor_bill = spec['paths']['/vendor-bills']['post']
        assert vendor_bill['requestBody']['content']['application/json']['schema'] == {
            '$ref': '#/components/schemas/VendorBillCreate'
        }
        assert 'SalesReturnCreate' in spec['components']['schemas']
        assert 'ManagedUserCreate' in spec['components']['schemas']
        assert '/openapi.json' in spec['paths']
        assert spec['paths']['/openapi.json']['get']['responses']['200'][
            'content'
        ]['application/json']['schema'] == {
            '$ref': '#/components/schemas/OpenAPIDocument'
        }
        assert '/auth/register' not in spec['paths']
        permissions_spec = spec['paths']['/permissions']['get']
        assert permissions_spec['security'] == [{'BearerAuth': []}]
        assert {
            parameter['name'] for parameter in permissions_spec['parameters']
        } == {'module'}
        assert spec['paths']['/inventory/adjusters']['get']['deprecated'] is True
        assert spec['paths']['/inventory/adjusters']['get']['x-canonical-path'] == (
            '/inventory/adjustments'
        )
        assert spec['paths']['/movements']['get']['deprecated'] is True
        assert spec['paths']['/reports/low-stock']['get']['x-canonical-path'] == (
            '/inventory/low-stock'
        )
        assert spec['paths']['/invoices']['get']['x-canonical-path'] == (
            '/sales-invoices'
        )
        assert spec['paths']['/payments']['get']['x-canonical-path'] == (
            '/customer-payments'
        )
        assert 'deprecated' not in spec['paths']['/inventory/movements']['get']
        assert '/inventory/movements/{movement_id}' in spec['paths']
        sales_report_parameters = {
            parameter['name']: parameter
            for parameter in spec['paths']['/reports/sales']['get']['parameters']
        }
        assert {'from_date', 'to_date', 'warehouse_id'} <= set(
            sales_report_parameters
        )
        assert {'page', 'per_page'} <= set(sales_report_parameters)
        assert sales_report_parameters['from_date']['schema']['format'] == 'date'
        sales_order_parameters = {
            parameter['name']
            for parameter in spec['paths']['/sales-orders']['get']['parameters']
        }
        assert {'page', 'per_page', 'status', 'warehouse_id'} <= sales_order_parameters

    def test_authorization_seed_adds_new_default_permission_to_existing_role(self, client):
        with client.application.app_context():
            warehouse_role = db.session.get(Role, 'warehouse')
            permission = db.session.get(Permission, 'sales_returns.post')
            warehouse_role.permissions.remove(permission)
            db.session.delete(permission)
            db.session.commit()

            seed_authorization()

            warehouse_role = db.session.get(Role, 'warehouse')
            assert 'sales_returns.post' in {
                permission.code for permission in warehouse_role.permissions
            }

    def test_sync_system_role_permissions_applies_current_defaults(self, client):
        with client.application.app_context():
            admin_role = db.session.get(Role, 'admin')
            admin_role.permissions = [
                db.session.get(Permission, 'profile.read')
            ]
            db.session.commit()

            sync_system_role_permissions()

            admin_role = db.session.get(Role, 'admin')
            assert {
                permission.code for permission in admin_role.permissions
            } == ROLE_DEFAULTS['admin']

    def test_shipment_post_and_invoice_routes_require_finance_or_warehouse_permission(self, client):
        sales_id = create_user(
            client.application,
            'sales-permission-user',
            'sales-permission@example.com',
            'test-password',
            role='sales'
        )
        finance_id = create_user(
            client.application,
            'finance-permission-user',
            'finance-permission@example.com',
            'test-password',
            role='finance',
            all_warehouses=True,
        )
        with client.application.app_context():
            sales_token = generate_token(sales_id)
            finance_token = generate_token(finance_id)

        sales_headers = {'Authorization': f'Bearer {sales_token}'}
        finance_headers = {'Authorization': f'Bearer {finance_token}'}

        assert client.post(
            '/api/v1/shipments/999/invoice',
            headers=sales_headers
        ).status_code == 403
        assert client.post(
            '/api/v1/sales-orders/999/invoice',
            headers=sales_headers
        ).status_code == 403
        assert client.post(
            '/api/v1/shipments/999/invoice',
            headers=finance_headers
        ).status_code == 404
        assert client.post(
            '/api/v1/sales-orders/999/invoice',
            headers=finance_headers
        ).status_code == 404

    def test_legacy_shipment_route_requires_shipment_post_permission(self, client):
        sales_id = create_user(
            client.application,
            'sales-shipment-user',
            'sales-shipment@example.com',
            'test-password',
            role='sales'
        )
        with client.application.app_context():
            sales_token = generate_token(sales_id)

        response = client.post(
            '/api/v1/sales-orders/999/shipment',
            headers={'Authorization': f'Bearer {sales_token}'}
        )
        assert response.status_code == 403

    def test_logout_revokes_bearer_token(self, client):
        user_id = create_user(
            client.application,
            'logout-user',
            'logout-user@example.com',
            'test-password',
            role='admin'
        )
        with client.application.app_context():
            token = generate_token(user_id)
        headers = {'Authorization': f'Bearer {token}'}
        assert client.post('/api/v1/auth/logout', headers=headers).status_code == 200
        assert client.get('/api/v1/auth/me', headers=headers).status_code == 401

    def test_admin_can_list_permission_catalog(self, client):
        admin_id = create_user(
            client.application,
            'catalog-admin',
            'catalog-admin@example.com',
            'test-password',
            role='admin'
        )
        with client.application.app_context():
            token = generate_token(admin_id)
        headers = {'Authorization': f'Bearer {token}'}

        response = client.get('/api/v1/permissions', headers=headers)
        assert response.status_code == 200
        permissions = response.get_json()['data']
        assert permissions
        codes = {permission['code'] for permission in permissions}
        assert {'users.manage', 'reports.read', 'sales_orders.create'} <= codes
        inventory_read = next(
            permission for permission in permissions
            if permission['code'] == 'inventory.read'
        )
        assert inventory_read['module'] == 'inventory'
        assert inventory_read['action'] == 'read'
        assert inventory_read['warehouse_scoped'] is True

        filtered = client.get(
            '/api/v1/permissions?module=sales',
            headers=headers
        ).get_json()['data']
        assert filtered
        assert {permission['module'] for permission in filtered} == {'sales'}

    def test_admin_manages_roles_permissions_and_scoped_users(self, client):
        admin_id = create_user(
            client.application,
            'rbac-admin',
            'rbac-admin@example.com',
            'test-password',
            role='admin'
        )
        warehouse = client.post('/api/v1/warehouses', json={
            'code': 'WH-RBAC',
            'name': 'RBAC Warehouse'
        }).get_json()['data']
        with client.application.app_context():
            token = generate_token(admin_id)
        headers = {'Authorization': f'Bearer {token}'}

        role_response = client.post('/api/v1/roles', json={
            'code': 'reporter',
            'name': 'Report Reader',
            'description': 'Read-only reporting role'
        }, headers=headers)
        assert role_response.status_code == 201
        permission_response = client.put(
            '/api/v1/roles/reporter/permissions',
            json={'permissions': ['reports.read']},
            headers=headers
        )
        assert permission_response.status_code == 200
        assert permission_response.get_json()['data']['permissions'] == [
            'profile.read', 'reports.read'
        ]

        user_response = client.post('/api/v1/users', json={
            'username': 'scoped-reporter',
            'email': 'scoped-reporter@example.com',
            'password': 'a-secure-test-password',
            'role': 'reporter',
            'warehouse_ids': [warehouse['id']]
        }, headers=headers)
        assert user_response.status_code == 201
        user = user_response.get_json()['data']
        assert user['warehouse_ids'] == [warehouse['id']]
        assert user['all_warehouses'] is False
        update = client.patch(
            f"/api/v1/users/{user['id']}",
            json={'is_active': False},
            headers=headers
        )
        assert update.status_code == 200
        assert update.get_json()['data']['is_active'] is False


@pytest.fixture
def valid_token_header(client):
    user_id = create_user(
        client.application,
        'validuser',
        'valid@example.com',
        'validpass123',
        role='admin'
    )
    with client.application.app_context():
        token = generate_token(user_id)
    return {'Authorization': f'Bearer {token}'}
