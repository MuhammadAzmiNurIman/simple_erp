class TestPartnerRoutes:
    def test_customer_and_supplier_detail_patch_contracts(self, client):
        customer_response = client.post('/api/v1/customers', json={
            'name': 'Route Contract Customer',
            'email': 'customer-route@example.com'
        })
        supplier_response = client.post('/api/v1/suppliers', json={
            'name': 'Route Contract Supplier',
            'email': 'supplier-route@example.com'
        })
        assert customer_response.status_code == 201
        assert supplier_response.status_code == 201
        customer_id = customer_response.get_json()['data']['id']
        supplier_id = supplier_response.get_json()['data']['id']

        customer = client.get(
            f'/api/v1/customers/{customer_id}'
        )
        supplier = client.get(
            f'/api/v1/suppliers/{supplier_id}'
        )
        assert customer.status_code == 200
        assert supplier.status_code == 200

        patched_customer = client.patch(
            f'/api/v1/customers/{customer_id}',
            json={'name': 'Updated Customer', 'is_active': False}
        )
        patched_supplier = client.patch(
            f'/api/v1/suppliers/{supplier_id}',
            json={'phone': '123456'}
        )
        assert patched_customer.status_code == 200
        assert patched_customer.get_json()['data']['name'] == 'Updated Customer'
        assert patched_customer.get_json()['data']['is_active'] is False
        assert patched_supplier.status_code == 200
        assert patched_supplier.get_json()['data']['phone'] == '123456'

    def test_partner_patch_rejects_unknown_fields_and_duplicate_email(self, client):
        first = client.post('/api/v1/customers', json={
            'name': 'First Customer',
            'email': 'first@example.com'
        }).get_json()['data']
        second = client.post('/api/v1/customers', json={
            'name': 'Second Customer',
            'email': 'second@example.com'
        }).get_json()['data']

        unknown_field = client.patch(
            f"/api/v1/customers/{first['id']}",
            json={'code': 'CUST-CHANGED'}
        )
        duplicate_email = client.patch(
            f"/api/v1/customers/{second['id']}",
            json={'email': 'first@example.com'}
        )
        assert unknown_field.status_code == 400
        assert duplicate_email.status_code == 409
