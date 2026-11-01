# app/routes/units.py
# CRUD Satuan - Master Data Satuan
from flask import Blueprint, current_app, request, jsonify
from app import db, ma
from app.models import Unit
from app.schemas import unit_schema, units_schema

bp = Blueprint('units', __name__)


@bp.route('/units', methods=['GET'])
def get_units():
    """Get all units with pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    active_only = request.args.get('active', 'true', type=str).lower() == 'true'

    query = Unit.query

    if active_only:
        query = query.filter_by(is_active=True)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    units = pagination.items

    return jsonify({
        'data': units_schema.dump(units),
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
    })


@bp.route('/units', methods=['POST'])
def create_unit():
    """Create new unit"""
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({'error': 'A JSON object is required'}), 400
    name = data.get('name')
    symbol = data.get('symbol', '')

    if not name:
        return jsonify({'error': 'Name is required'}), 400

    # Check if unit already exists
    existing = Unit.query.filter_by(name=name).first()
    if existing:
        return jsonify({'error': 'Unit name already exists'}), 409

    unit = Unit(name=name, symbol=symbol)
    try:
        db.session.add(unit)
        db.session.commit()

        return jsonify({
            'message': 'Unit created successfully',
            'data': unit_schema.dump(unit)
        }), 201
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Unit creation failed')
        return jsonify({'error': 'Unable to create unit'}), 500


@bp.route('/units/<int:unit_id>', methods=['GET'])
def get_unit(unit_id):
    """Get single unit"""
    unit = db.get_or_404(Unit, unit_id)
    return jsonify({
        'data': unit_schema.dump(unit)
    })


@bp.route('/units/<int:unit_id>', methods=['PATCH'])
def update_unit(unit_id):
    """Update unit"""
    unit = db.get_or_404(Unit, unit_id)
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({'error': 'A JSON object is required'}), 400
    if 'name' in data:
        # Check if new name conflicts
        existing = Unit.query.filter(
            Unit.name == data['name'], 
            Unit.id != unit_id
        ).first()
        if existing:
            return jsonify({'error': 'Unit name already exists'}), 409
        unit.name = data['name']
    if 'symbol' in data:
        unit.symbol = data['symbol']
    try:
        db.session.commit()
        return jsonify({
            'message': 'Unit updated successfully',
            'data': unit_schema.dump(unit)
        })
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Unit update failed')
        return jsonify({'error': 'Unable to update unit'}), 500


@bp.route('/units/<int:unit_id>', methods=['DELETE'])
def delete_unit(unit_id):
    """Soft delete unit (set inactive)"""
    unit = db.get_or_404(Unit, unit_id)
    try:
        unit.is_active = False
        db.session.commit()
        return jsonify({'message': 'Unit deactivated successfully'})
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Unit deactivation failed')
        return jsonify({'error': 'Unable to deactivate unit'}), 500