"""Tests for sales orders, reservations, invoices, and payments."""

from decimal import Decimal

from app import db
from app.models import InventoryBalance, SalesOrder, User
from app.routes.identity.auth import generate_token


def sales_approver_headers(client):
    with client.application.app_context():
        user = User.query.filter_by(username='sales-test-manager').first()
        if user is None:
            user = User(
                username='sales-test-manager',
                email='sales-test-manager@example.com',
                role='manager',
                all_warehouses=True,
            )
            user.set_password('test-password')
            db.session.add(user)
            db.session.commit()
        token = generate_token(user.id)
    return {'Authorization': f'Bearer {token}'}


def submit_and_approve_sales_order(client, order_id, submit=True):
    if submit:
        submitted = client.post(f'/api/v1/sales-orders/{order_id}/submit')
        assert submitted.status_code == 200
    approved = client.post(
        f'/api/v1/sales-orders/{order_id}/approve',
        headers=sales_approver_headers(client),
    )
    assert approved.status_code == 200
    return approved


def create_sales_data(client):
    customer = client.post('/api/v1/customers', json={
        'name': 'Test Customer'
    }).get_json()['data']
    warehouse = client.post('/api/v1/warehouses', json={
        'code': 'WH-SALES',
        'name': 'Sales Warehouse'
    }).get_json()['data']
    products = []
    for sku in ('SKU-SALES-1', 'SKU-SALES-2'):
        product = client.post('/api/v1/products', json={
            'sku': sku,
            'name': sku,
            'min_stock': 0
        }).get_json()['data']
        balance = client.post('/api/v1/inventory/balances', json={
            'product_id': product['id'],
            'warehouse_id': warehouse['id'],
            'quantity_on_hand': 10,
            'average_cost': 5
        }).get_json()['data']
        products.append((product, balance))
    return customer, warehouse, products


def create_invoice(client, customer, warehouse, product):
    order_response = client.post('/api/v1/sales-orders', json={
        'customer_id': customer['id'],
        'warehouse_id': warehouse['id'],
        'due_date': '2026-12-25',
        'items': [{'product_id': product['id'], 'quantity': 1}]
    })
    assert order_response.status_code == 201
    order_id = order_response.get_json()['data']['id']
    submit_and_approve_sales_order(client, order_id)
    shipment_response = client.post(
        f'/api/v1/sales-orders/{order_id}/shipment'
    )
    assert shipment_response.status_code == 200
    invoice_response = client.post(
        f'/api/v1/sales-orders/{order_id}/invoice'
    )
    assert invoice_response.status_code == 201
    return invoice_response.get_json()['data']


class TestSales:
    def test_sales_order_money_uses_decimal_rounding(self, client, app):
        customer, warehouse, products = create_sales_data(client)
        with app.app_context():
            balance = db.session.get(InventoryBalance, products[0][1]['id'])
            balance.average_cost = Decimal('2.675')
            db.session.commit()
        response = client.post('/api/v1/sales-orders', json={
            'customer_id': customer['id'],
            'warehouse_id': warehouse['id'],
            'due_date': '2026-12-25',
            'items': [{'product_id': products[0][0]['id'], 'quantity': 2}],
        })

        assert response.status_code == 201
        order_data = response.get_json()['data']
        assert order_data['total_amount'] == 5.36
        assert order_data['items'][0]['unit_price'] == 2.68
        assert order_data['items'][0]['total_price'] == 5.36
        with app.app_context():
            order = db.session.get(SalesOrder, order_data['id'])
            assert isinstance(order.total_amount, Decimal)
            assert isinstance(order.items[0].unit_price, Decimal)
            assert isinstance(order.items[0].total_price, Decimal)

    def test_get_sales_orders(self, client):
        response = client.get('/api/v1/sales-orders')
        assert response.status_code == 200

    def test_due_date_is_required(self, client):
        customer, warehouse, products = create_sales_data(client)
        response = client.post('/api/v1/sales-orders', json={
            'customer_id': customer['id'],
            'warehouse_id': warehouse['id'],
            'items': [{'product_id': products[0][0]['id'], 'quantity': 1}]
        })
        assert response.status_code == 400

    def test_multiple_products_reserve_and_ship_correct_balances(self, client):
        customer, warehouse, products = create_sales_data(client)
        response = client.post('/api/v1/sales-orders', json={
            'customer_id': customer['id'],
            'warehouse_id': warehouse['id'],
            'due_date': '2026-12-25',
            'items': [
                {'product_id': products[0][0]['id'], 'quantity': 2},
                {'product_id': products[1][0]['id'], 'quantity': 3}
            ]
        })
        assert response.status_code == 201
        order = response.get_json()['data']
        assert order['status'] == 'RESERVED'

        submit_and_approve_sales_order(client, order['id'])

        for product, balance in products:
            current = client.get(
                f"/api/v1/inventory/balances/{balance['id']}"
            ).get_json()['data']
            assert current['quantity_on_hand'] == 10
            expected_reserved = 2 if product['id'] == products[0][0]['id'] else 3
            assert current['quantity_reserved'] == expected_reserved

        shipment = client.post(
            f"/api/v1/sales-orders/{order['id']}/shipment"
        )
        assert shipment.status_code == 200
        assert shipment.get_json()['data']['status'] == 'SHIPPED'

        expected_quantities = {products[0][0]['id']: 8, products[1][0]['id']: 7}
        for product, balance in products:
            current = client.get(
                f"/api/v1/inventory/balances/{balance['id']}"
            ).get_json()['data']
            assert current['quantity_on_hand'] == expected_quantities[product['id']]
            assert current['quantity_reserved'] == 0

        movements = client.get('/api/v1/movements').get_json()['data']
        shipment_movements = [
            movement for movement in movements
            if movement['reference_type'] == 'SHIPMENT'
        ]
        assert len(shipment_movements) == 2
        assert len(movements) == 4  # two opening balances plus two shipment lines
        assert client.get('/api/v1/inventory/movements').get_json()['total'] == 4
        assert client.get(
            f"/api/v1/inventory/low-stock?warehouse_id={warehouse['id']}"
        ).status_code == 200

    def test_canonical_sales_order_shipment_and_invoice_routes(self, client):
        customer, warehouse, products = create_sales_data(client)
        order = client.post('/api/v1/sales-orders', json={
            'customer_id': customer['id'],
            'warehouse_id': warehouse['id'],
            'due_date': '2026-12-25',
            'items': [{'product_id': products[0][0]['id'], 'quantity': 2}]
        }).get_json()['data']

        submitted = client.post(
            f"/api/v1/sales-orders/{order['id']}/submit"
        )
        assert submitted.status_code == 200
        assert submitted.get_json()['data']['status'] == 'SUBMITTED'
        assert client.post(
            f"/api/v1/sales-orders/{order['id']}/shipments",
            json={'items': [{
                'sales_order_item_id': order['items'][0]['id'],
                'quantity': 1
            }]}
        ).status_code == 409
        approved = submit_and_approve_sales_order(
            client, order['id'], submit=False
        )
        assert approved.status_code == 200
        assert approved.get_json()['data']['status'] == 'RESERVED'

        created_shipment = client.post('/api/v1/shipments', json={
            'sales_order_id': order['id'],
            'items': [{
                'sales_order_item_id': order['items'][0]['id'],
                'quantity': 2
            }]
        })
        assert created_shipment.status_code == 201
        shipment = created_shipment.get_json()['data']
        assert shipment['customer_name']
        assert shipment['warehouse_name']
        assert shipment['items'][0]['product_name']
        assert client.get('/api/v1/shipments').get_json()['total'] == 1
        assert client.post(
            f"/api/v1/shipments/{shipment['id']}/post"
        ).status_code == 200

        invoice_response = client.post('/api/v1/sales-invoices', json={
            'shipment_id': shipment['id']
        })
        assert invoice_response.status_code == 201
        invoice = invoice_response.get_json()['data']
        assert invoice['customer_name']
        assert invoice['sales_order_code']
        assert invoice['items'][0]['product_name']
        assert invoice['items'][0]['total_price'] == invoice['total_amount']
        assert client.get('/api/v1/sales-invoices').get_json()['total'] == 1
        assert client.get(
            f"/api/v1/sales-invoices/{invoice['id']}"
        ).get_json()['data']['id'] == invoice['id']

    def test_full_invoice_and_payment_lifecycle(self, client):
        customer, warehouse, products = create_sales_data(client)
        response = client.post('/api/v1/sales-orders', json={
            'customer_id': customer['id'],
            'warehouse_id': warehouse['id'],
            'due_date': '2026-12-25',
            'items': [{'product_id': products[0][0]['id'], 'quantity': 2}]
        })
        order_id = response.get_json()['data']['id']
        assert response.status_code == 201
        submit_and_approve_sales_order(client, order_id)
        assert client.post(
            f'/api/v1/sales-orders/{order_id}/shipment'
        ).status_code == 200

        invoice_response = client.post(
            f'/api/v1/sales-orders/{order_id}/invoice'
        )
        assert invoice_response.status_code == 201
        invoice = invoice_response.get_json()['data']
        assert invoice['total_amount'] == 10
        assert client.get(
            f"/api/v1/invoices/{invoice['id']}"
        ).get_json()['data']['balance_due'] == 10

        partial = client.post('/api/v1/payments', json={
            'invoice_id': invoice['id'],
            'amount': 4,
            'payment_method': 'CASH'
        })
        assert partial.status_code == 201
        partial_payment = partial.get_json()['data']
        assert partial_payment['status'] == 'DRAFT'
        assert partial_payment['customer_name']
        assert partial_payment['invoice_code'] == invoice['code']
        assert client.get(
            f"/api/v1/invoices/{invoice['id']}"
        ).get_json()['data']['balance_due'] == 10
        posted_partial = client.post(
            f"/api/v1/payments/{partial_payment['id']}/post"
        )
        assert posted_partial.status_code == 200
        assert posted_partial.get_json()['data']['invoice']['status'] == 'PARTIALLY_PAID'
        assert posted_partial.get_json()['data']['invoice']['balance_due'] == 6
        receivables = client.get(
            '/api/v1/finance/receivables?as_of=2026-12-25'
        ).get_json()
        assert receivables['total'] == 1
        assert receivables['summary']['outstanding_amount'] == 6
        assert receivables['summary']['overdue_amount'] == 0
        cash_summary = client.get(
            '/api/v1/finance/cash-summary'
        ).get_json()['data']
        assert cash_summary['incoming_amount'] == 4
        assert cash_summary['outgoing_amount'] == 0

        final = client.post('/api/v1/payments', json={
            'invoice_id': invoice['id'],
            'amount': 6,
            'payment_method': 'BANK_TRANSFER'
        })
        assert final.status_code == 201
        final_payment = final.get_json()['data']
        assert final_payment['status'] == 'DRAFT'
        posted_final = client.post(
            f"/api/v1/payments/{final_payment['id']}/post"
        )
        assert posted_final.status_code == 200
        assert posted_final.get_json()['data']['invoice']['status'] == 'PAID'
        assert client.get('/api/v1/payments').get_json()['total'] == 2
        assert client.get('/api/v1/invoices?status=PAID').get_json()['total'] == 1
        assert client.get('/api/v1/finance/receivables').get_json()['total'] == 0
        assert client.get('/api/v1/finance/cash-summary').get_json()[
            'data'
        ]['incoming_amount'] == 10
        dashboard = client.get(
            '/api/v1/dashboard/summary?from_date=2026-01-01&to_date=2026-12-31'
        ).get_json()['data']
        assert dashboard['total_sales_amount'] == 10
        assert dashboard['receivables_outstanding'] == 0
        assert dashboard['cash_incoming'] == 10
        sales_report = client.get(
            '/api/v1/reports/sales?from_date=2026-01-01&to_date=2026-12-31'
        ).get_json()
        assert sales_report['total_sales_amount'] == 10
        inventory_report = client.get('/api/v1/reports/inventory').get_json()
        assert inventory_report['total_inventory_value'] == 90
        movement_report = client.get('/api/v1/reports/stock-movements').get_json()
        assert movement_report['total'] == 3  # two opening balances plus one shipment

    def test_customer_payment_can_be_allocated_to_multiple_invoices(self, client):
        customer, warehouse, products = create_sales_data(client)
        first_invoice = create_invoice(
            client, customer, warehouse, products[0][0]
        )
        second_invoice = create_invoice(
            client, customer, warehouse, products[1][0]
        )

        payment_response = client.post('/api/v1/customer-payments', json={
            'customer_id': customer['id'],
            'amount': 8,
            'payment_method': 'BANK_TRANSFER'
        })
        assert payment_response.status_code == 201
        payment = payment_response.get_json()['data']
        assert payment['customer_id'] == customer['id']
        assert payment['invoice_id'] is None

        allocation_response = client.post(
            f"/api/v1/customer-payments/{payment['id']}/allocations",
            json={'allocations': [
                {'invoice_id': first_invoice['id'], 'amount': 5},
                {'invoice_id': second_invoice['id'], 'amount': 3}
            ]}
        )
        assert allocation_response.status_code == 200
        assert len(allocation_response.get_json()['data']['allocations']) == 2

        for invoice in (first_invoice, second_invoice):
            current = client.get(
                f"/api/v1/invoices/{invoice['id']}"
            ).get_json()['data']
            assert current['amount_paid'] == 0
            assert current['balance_due'] == 5

        posted = client.post(
            f"/api/v1/customer-payments/{payment['id']}/post"
        )
        assert posted.status_code == 200
        result = posted.get_json()['data']
        assert result['status'] == 'POSTED'
        assert len(result['invoices']) == 2
        assert result['invoice'] is None

        first_after = client.get(
            f"/api/v1/invoices/{first_invoice['id']}"
        ).get_json()['data']
        second_after = client.get(
            f"/api/v1/invoices/{second_invoice['id']}"
        ).get_json()['data']
        assert first_after['amount_paid'] == 5
        assert first_after['balance_due'] == 0
        assert first_after['status'] == 'PAID'
        assert second_after['amount_paid'] == 3
        assert second_after['balance_due'] == 2
        assert second_after['status'] == 'PARTIALLY_PAID'
        assert client.get('/api/v1/customer-payments').get_json()['total'] == 1

    def test_customer_payment_allocations_validate_customer_and_amount(self, client):
        customer, warehouse, products = create_sales_data(client)
        invoice = create_invoice(client, customer, warehouse, products[0][0])
        payment = client.post('/api/v1/customer-payments', json={
            'customer_id': customer['id'],
            'amount': 4
        }).get_json()['data']

        over_payment = client.post(
            f"/api/v1/customer-payments/{payment['id']}/allocations",
            json={'allocations': [
                {'invoice_id': invoice['id'], 'amount': 5}
            ]}
        )
        assert over_payment.status_code == 400
        assert 'payment amount' in over_payment.get_json()['error']

        other_customer = client.post('/api/v1/customers', json={
            'name': 'Different Customer'
        }).get_json()['data']
        other_invoice = create_invoice(
            client, other_customer, warehouse, products[1][0]
        )
        wrong_customer = client.post(
            f"/api/v1/customer-payments/{payment['id']}/allocations",
            json={'allocations': [
                {'invoice_id': other_invoice['id'], 'amount': 1}
            ]}
        )
        assert wrong_customer.status_code == 400
        assert 'belong to the payment customer' in wrong_customer.get_json()['error']

        no_allocations = client.post(
            f"/api/v1/customer-payments/{payment['id']}/post"
        )
        assert no_allocations.status_code == 409
        assert client.get(
            f"/api/v1/invoices/{invoice['id']}"
        ).get_json()['data']['balance_due'] == 5

    def test_partial_shipments_have_individual_invoices(self, client):
        customer, warehouse, products = create_sales_data(client)
        order_response = client.post('/api/v1/sales-orders', json={
            'customer_id': customer['id'],
            'warehouse_id': warehouse['id'],
            'due_date': '2026-12-25',
            'items': [{'product_id': products[0][0]['id'], 'quantity': 4}]
        })
        order = order_response.get_json()['data']
        item_id = order['items'][0]['id']
        submit_and_approve_sales_order(client, order['id'])

        first_draft = client.post(
            f"/api/v1/sales-orders/{order['id']}/shipments",
            json={'items': [{'sales_order_item_id': item_id, 'quantity': 1.5}]}
        )
        assert first_draft.status_code == 201
        shipment = first_draft.get_json()['data']
        assert shipment['status'] == 'DRAFT'
        assert client.post(
            f"/api/v1/shipments/{shipment['id']}/post"
        ).status_code == 200

        first_invoice = client.post(
            f"/api/v1/shipments/{shipment['id']}/invoice"
        )
        assert first_invoice.status_code == 201
        assert first_invoice.get_json()['data']['total_amount'] == 7.5
        assert client.post(
            f"/api/v1/shipments/{shipment['id']}/invoice"
        ).status_code == 409

        second = client.post(
            f"/api/v1/sales-orders/{order['id']}/shipments",
            json={'items': [{'sales_order_item_id': item_id, 'quantity': 2.5}]}
        )
        assert second.status_code == 201
        second_id = second.get_json()['data']['id']
        assert client.post(f'/api/v1/shipments/{second_id}/post').status_code == 200
        assert client.post(f'/api/v1/shipments/{second_id}/invoice').status_code == 201
        assert client.get(
            f"/api/v1/sales-orders/{order['id']}"
        ).get_json()['data']['status'] == 'INVOICED'

    def test_cancelling_partially_shipped_order_releases_only_remaining_reservation(self, client):
        customer, warehouse, products = create_sales_data(client)
        order = client.post('/api/v1/sales-orders', json={
            'customer_id': customer['id'],
            'warehouse_id': warehouse['id'],
            'due_date': '2026-12-25',
            'items': [{'product_id': products[0][0]['id'], 'quantity': 4}]
        }).get_json()['data']
        item_id = order['items'][0]['id']
        submit_and_approve_sales_order(client, order['id'])
        draft = client.post(
            f"/api/v1/sales-orders/{order['id']}/shipments",
            json={'items': [{'sales_order_item_id': item_id, 'quantity': 1}]}
        )
        shipment_id = draft.get_json()['data']['id']
        assert client.post(f'/api/v1/shipments/{shipment_id}/post').status_code == 200

        cancelled = client.post(f"/api/v1/sales-orders/{order['id']}/cancel")
        assert cancelled.status_code == 200
        assert cancelled.get_json()['data']['status'] == 'CANCELLED'
        current = client.get(
            f"/api/v1/inventory/balances/{products[0][1]['id']}"
        ).get_json()['data']
        assert current['quantity_on_hand'] == 9
        assert current['quantity_reserved'] == 0

    def test_sales_order_rejects_aggregate_quantity_over_available_stock(self, client):
        customer, warehouse, products = create_sales_data(client)
        response = client.post('/api/v1/sales-orders', json={
            'customer_id': customer['id'],
            'warehouse_id': warehouse['id'],
            'due_date': '2026-12-25',
            'items': [
                {'product_id': products[0][0]['id'], 'quantity': 6},
                {'product_id': products[0][0]['id'], 'quantity': 5}
            ]
        })
        assert response.status_code == 400

    def test_cancelling_reserved_order_releases_stock(self, client):
        customer, warehouse, products = create_sales_data(client)
        response = client.post('/api/v1/sales-orders', json={
            'customer_id': customer['id'],
            'warehouse_id': warehouse['id'],
            'due_date': '2026-12-25',
            'items': [{'product_id': products[0][0]['id'], 'quantity': 2}]
        })
        order = response.get_json()['data']

        cancelled = client.post(
            f"/api/v1/sales-orders/{order['id']}/cancel"
        )
        assert cancelled.status_code == 200
        assert cancelled.get_json()['data']['status'] == 'CANCELLED'

        balance = client.get(
            f"/api/v1/inventory/balances/{products[0][1]['id']}"
        ).get_json()['data']
        assert balance['quantity_on_hand'] == 10
        assert balance['quantity_reserved'] == 0
