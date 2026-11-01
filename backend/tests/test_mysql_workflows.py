"""Opt-in end-to-end workflows against a disposable migrated MySQL database."""
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text

from app import create_app, db
from app.authorization import seed_authorization
from app.models import User
from app.routes.identity.auth import generate_token
from config import Config


@pytest.fixture(scope='module')
def mysql_api():
    database_url = os.getenv('ERP_MYSQL_TEST_URL')
    if not database_url:
        pytest.skip('Set ERP_MYSQL_TEST_URL to run MySQL workflow integration tests.')

    engine = create_engine(database_url)
    if not engine.url.drivername.startswith('mysql'):
        pytest.fail('ERP_MYSQL_TEST_URL must use a MySQL driver.')
    if not engine.url.database or not engine.url.database.endswith('_test'):
        pytest.fail('MySQL workflow tests require a database name ending in _test.')

    with engine.connect() as connection:
        revision = connection.execute(
            text('SELECT version_num FROM alembic_version')
        ).scalar_one_or_none()
        if revision != 'd4e5f6a7b8c9':
            pytest.fail(
                'Run `flask db upgrade` on the disposable MySQL test database first.'
            )
        tables = connection.execute(text("""
            SELECT TABLE_NAME
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_TYPE = 'BASE TABLE'
        """)).scalars().all()
        nonempty = []
        for table in tables:
            if table in {'alembic_version', 'roles', 'permissions', 'role_permissions'}:
                continue
            count = connection.execute(
                text(f'SELECT COUNT(*) FROM `{table}`')
            ).scalar_one()
            if count:
                nonempty.append(f'{table}={count}')
        if nonempty:
            pytest.fail(
                'The disposable MySQL test database must not contain business '
                f'data before the test: {", ".join(nonempty)}.'
            )

    test_config = type('MySQLWorkflowTestConfig', (Config,), {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': database_url,
        'SECRET_KEY': 'mysql-integration-test-secret',
        'JWT_SECRET_KEY': 'mysql-integration-test-jwt-secret',
        'RATELIMIT_ENABLED': False,
    })
    app = create_app(test_config)
    run_id = uuid4().hex[:10]
    with app.app_context():
        seed_authorization()
        users = []
        for suffix in ('maker', 'approver'):
            user = User(
                username=f'mysql-{run_id}-{suffix}',
                email=f'mysql-{run_id}-{suffix}@example.test',
                role='operator',
                all_warehouses=True
            )
            user.set_password('integration-test-only')
            db.session.add(user)
            users.append(user)
        db.session.commit()
        headers = [
            {'Authorization': f'Bearer {generate_token(user.id)}'}
            for user in users
        ]

    try:
        with app.test_client() as client:
            yield client, headers, run_id
    finally:
        with app.app_context():
            db.session.remove()
            with db.engine.begin() as connection:
                connection.exec_driver_sql('SET FOREIGN_KEY_CHECKS=0')
                for table in tables:
                    if table in {'alembic_version', 'roles', 'permissions', 'role_permissions'}:
                        continue
                    connection.exec_driver_sql(f'DELETE FROM `{table}`')
                connection.exec_driver_sql('SET FOREIGN_KEY_CHECKS=1')
            db.session.remove()
        engine.dispose()


def _post(client, path, headers, payload=None):
    response = client.post(path, headers=headers, json=payload)
    assert response.status_code in {200, 201}, (
        path, response.status_code, response.get_json()
    )
    return response.get_json()


def test_purchase_sales_and_payment_workflows_on_mysql(mysql_api):
    client, (maker_headers, approver_headers), run_id = mysql_api
    supplier = _post(client, '/api/v1/suppliers', maker_headers, {
        'name': f'MySQL Supplier {run_id}'
    })['data']
    customer = _post(client, '/api/v1/customers', maker_headers, {
        'name': f'MySQL Customer {run_id}'
    })['data']
    warehouse = _post(client, '/api/v1/warehouses', maker_headers, {
        'code': f'MY{run_id[:6]}',
        'name': f'MySQL Warehouse {run_id}'
    })['data']
    product = _post(client, '/api/v1/products', maker_headers, {
        'sku': f'MYSQL-{run_id}',
        'name': f'MySQL Product {run_id}',
        'min_stock': 0
    })['data']
    balance = _post(client, '/api/v1/inventory/balances', maker_headers, {
        'product_id': product['id'],
        'warehouse_id': warehouse['id'],
        'quantity_on_hand': 10,
        'average_cost': 5
    })['data']

    purchase_order = _post(client, '/api/v1/purchase-orders', maker_headers, {
        'supplier_id': supplier['id'],
        'warehouse_id': warehouse['id'],
        'items': [{
            'product_id': product['id'],
            'quantity': 2,
            'unit_cost': 10
        }]
    })['data']
    _post(
        client,
        f"/api/v1/purchase-orders/{purchase_order['id']}/approve",
        approver_headers
    )
    receipt = _post(client, '/api/v1/goods-receipts', maker_headers, {
        'purchase_order_id': purchase_order['id'],
        'items': [{
            'purchase_order_item_id': purchase_order['items'][0]['id'],
            'quantity': 2
        }]
    })['data']
    posted_receipt = _post(
        client,
        f"/api/v1/goods-receipts/{receipt['id']}/post",
        maker_headers
    )
    vendor_bill = posted_receipt['vendor_bill']
    assert vendor_bill['total_amount'] == 20

    sales_order = _post(client, '/api/v1/sales-orders', maker_headers, {
        'customer_id': customer['id'],
        'warehouse_id': warehouse['id'],
        'due_date': '2026-12-31',
        'items': [{'product_id': product['id'], 'quantity': 3}]
    })['data']
    _post(
        client,
        f"/api/v1/sales-orders/{sales_order['id']}/submit",
        maker_headers
    )
    _post(
        client,
        f"/api/v1/sales-orders/{sales_order['id']}/approve",
        approver_headers
    )
    shipment = _post(client, '/api/v1/shipments', maker_headers, {
        'sales_order_id': sales_order['id'],
        'items': [{
            'sales_order_item_id': sales_order['items'][0]['id'],
            'quantity': 3
        }]
    })['data']
    posted_shipment = _post(
        client,
        f"/api/v1/shipments/{shipment['id']}/post",
        maker_headers
    )['data']
    assert posted_shipment['status'] == 'POSTED'

    invoice = _post(client, '/api/v1/sales-invoices', maker_headers, {
        'shipment_id': shipment['id']
    })['data']
    customer_payment = _post(client, '/api/v1/customer-payments', maker_headers, {
        'customer_id': customer['id'],
        'amount': invoice['total_amount'],
        'payment_method': 'BANK_TRANSFER'
    })['data']
    _post(
        client,
        f"/api/v1/customer-payments/{customer_payment['id']}/allocations",
        maker_headers,
        {'allocations': [{
            'invoice_id': invoice['id'],
            'amount': invoice['total_amount']
        }]}
    )
    posted_customer_payment = _post(
        client,
        f"/api/v1/customer-payments/{customer_payment['id']}/post",
        maker_headers
    )['data']
    assert posted_customer_payment['status'] == 'POSTED'

    supplier_payment = _post(client, '/api/v1/supplier-payments', maker_headers, {
        'supplier_id': supplier['id'],
        'amount': vendor_bill['total_amount'],
        'payment_method': 'BANK_TRANSFER'
    })['data']
    _post(
        client,
        f"/api/v1/supplier-payments/{supplier_payment['id']}/allocations",
        maker_headers,
        {'allocations': [{
            'vendor_bill_id': vendor_bill['id'],
            'amount': vendor_bill['total_amount']
        }]}
    )
    posted_supplier_payment = _post(
        client,
        f"/api/v1/supplier-payments/{supplier_payment['id']}/post",
        maker_headers
    )['data']
    assert posted_supplier_payment['status'] == 'POSTED'

    current_balance = client.get(
        f"/api/v1/inventory/balances/{balance['id']}",
        headers=maker_headers
    ).get_json()['data']
    assert current_balance['quantity_on_hand'] == 9
    assert current_balance['quantity_reserved'] == 0
    assert client.get(
        f"/api/v1/finance/receivables",
        headers=maker_headers
    ).status_code == 200
    assert client.get(
        f"/api/v1/finance/payables",
        headers=maker_headers
    ).status_code == 200
    assert client.get(
        f"/api/v1/finance/cash-summary",
        headers=maker_headers
    ).status_code == 200
