"""Stock movement API tests."""


def test_stock_movement_can_be_retrieved(client):
    from app import db
    from app.models import StockMovement

    product = client.post('/api/v1/products', json={
        'sku': 'SKU-MOVEMENT',
        'name': 'Movement Product'
    }).get_json()['data']
    warehouse = client.post('/api/v1/warehouses', json={
        'code': 'WH-MOVEMENT',
        'name': 'Movement Warehouse'
    }).get_json()['data']

    with client.application.app_context():
        movement = StockMovement(
            product_id=product['id'],
            warehouse_id=warehouse['id'],
            movement_type='IN',
            quantity_delta=5,
            unit_cost=3
        )
        db.session.add(movement)
        db.session.commit()
        movement_id = movement.id

    response = client.get(f'/api/v1/movements/{movement_id}')
    assert response.status_code == 200
    assert response.get_json()['data']['quantity_delta'] == 5
    assert response.get_json()['data']['is_inbound'] is True
    assert response.get_json()['data']['is_outbound'] is False
    assert client.get('/api/v1/movements').get_json()['total'] == 1
