"""Reports tests."""
class TestReports:
    def test_get_low_stock_report(self, client):
        resp = client.get('/api/v1/reports/low-stock')
        assert resp.status_code == 200

    def test_get_turnover_report(self, client):
        resp = client.get('/api/v1/reports/turnover')
        assert resp.status_code == 200

    def test_get_replenishment_report(self, client):
        resp = client.get('/api/v1/reports/replenishment')
        assert resp.status_code == 200

    def test_prd_report_and_dashboard_routes_are_available(self, client):
        for path in (
            '/api/v1/reports/sales',
            '/api/v1/reports/purchases',
            '/api/v1/reports/inventory',
            '/api/v1/reports/stock-movements',
            '/api/v1/reports/receivables',
            '/api/v1/reports/payables',
            '/api/v1/dashboard/summary',
        ):
            response = client.get(path)
            assert response.status_code == 200, (path, response.get_json())
            assert isinstance(response.get_json()['data'], (dict, list))

    def test_report_date_filters_reject_invalid_ranges(self, client):
        invalid_date = client.get('/api/v1/reports/sales?from_date=not-a-date')
        assert invalid_date.status_code == 400
        reversed_period = client.get(
            '/api/v1/dashboard/summary?from_date=2026-12-31&to_date=2026-01-01'
        )
        assert reversed_period.status_code == 400

    def test_turnover_separates_movement_types(self, client):
        from app import db
        from app.models import StockMovement

        product = client.post('/api/v1/products', json={
            'sku': 'SKU-TURNOVER',
            'name': 'Turnover Product'
        }).get_json()['data']
        warehouse = client.post('/api/v1/warehouses', json={
            'code': 'WH-TURNOVER',
            'name': 'Turnover Warehouse'
        }).get_json()['data']

        with client.application.app_context():
            db.session.add_all([
                StockMovement(
                    product_id=product['id'],
                    warehouse_id=warehouse['id'],
                    movement_type='IN',
                    quantity_delta=5,
                    unit_cost=2
                ),
                StockMovement(
                    product_id=product['id'],
                    warehouse_id=warehouse['id'],
                    movement_type='OUT',
                    quantity_delta=-2,
                    unit_cost=2
                )
            ])
            db.session.commit()

        response = client.get('/api/v1/reports/turnover')
        data = response.get_json()['data']
        assert response.status_code == 200
        assert {(row['movement_type'], row['total_quantity']) for row in data} == {
            ('IN', 5.0),
            ('OUT', 2.0)
        }