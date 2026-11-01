# app/routes/warehouse.py
# CRUD Gudang - Master Data Warehouse
from flask import Blueprint, current_app, request, jsonify
from app import db, ma
from app.models import Warehouse
from app.schemas import warehouse_schema, warehouses_schema

bp = Blueprint('warehouse', __name__)


@bp.route('/warehouses', methods=['GET'])
def get_warehouses():
    """Get all warehouses with pagination and filter active"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    active_only = request.args.get('active', 'true', type=str).lower() == 'true'

    query = Warehouse.query

    current_user = getattr(request, 'current_user', None)
    if current_user and not current_user.all_warehouses and current_user.role != 'admin':
        query = query.filter(Warehouse.id.in_(request.allowed_warehouse_ids))

    if active_only:
        query = query.filter_by(is_active=True)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    warehouses = pagination.items

    return jsonify({
        'data': warehouses_schema.dump(warehouses),
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
    })


@bp.route('/warehouses', methods=['POST'])
def create_warehouse():
    """Create new warehouse"""
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({'error': 'A JSON object is required'}), 400
    code = data.get('code')
    name = data.get('name')
    address = data.get('address', '')

    if not code:
        return jsonify({'error': 'Code is required'}), 400
    if not name:
        return jsonify({'error': 'Name is required'}), 400

    # Check if warehouse code already exists
    existing = Warehouse.query.filter_by(code=code).first()
    if existing:
        return jsonify({'error': 'Warehouse code already exists'}), 409

    warehouse = Warehouse(code=code, name=name, address=address)
    try:
        db.session.add(warehouse)
        db.session.commit()

        return jsonify({
            'message': 'Warehouse created successfully',
            'data': warehouse_schema.dump(warehouse)
        }), 201
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Warehouse creation failed')
        return jsonify({'error': 'Unable to create warehouse'}), 500


@bp.route('/warehouses/<int:warehouse_id>', methods=['GET'])
def get_warehouse(warehouse_id):
    """Get single warehouse"""
    warehouse = db.get_or_404(Warehouse, warehouse_id)
    return jsonify({
        'data': warehouse_schema.dump(warehouse)
    })


@bp.route('/warehouses/<int:warehouse_id>', methods=['PATCH'])
def update_warehouse(warehouse_id):
    """Update warehouse"""
    warehouse = db.get_or_404(Warehouse, warehouse_id)
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({'error': 'A JSON object is required'}), 400
    if 'name' in data:
        warehouse.name = data['name']
    if 'address' in data:
        warehouse.address = data['address']
    try:
        db.session.commit()
        return jsonify({
            'message': 'Warehouse updated successfully',
            'data': warehouse_schema.dump(warehouse)
        })
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Warehouse update failed')
        return jsonify({'error': 'Unable to update warehouse'}), 500


@bp.route('/warehouses/<int:warehouse_id>', methods=['DELETE'])
def delete_warehouse(warehouse_id):
    """Soft delete warehouse (set inactive)"""
    warehouse = db.get_or_404(Warehouse, warehouse_id)
    try:
        warehouse.is_active = False
        db.session.commit()
        return jsonify({'message': 'Warehouse deactivated successfully'})
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Warehouse deactivation failed')
        return jsonify({'error': 'Unable to deactivate warehouse'}), 500
