from uuid import uuid4

from flask import Blueprint, current_app, jsonify, request

from app import db
from app.models import Customer, Supplier


customers_bp = Blueprint('customers', __name__)
suppliers_bp = Blueprint('suppliers', __name__)


def _create_partner(model, prefix):
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({'error': 'A JSON object is required'}), 400

    name = data.get('name')
    if not isinstance(name, str) or not name.strip() or len(name) > 100:
        return jsonify({'error': 'A valid name is required'}), 400

    code = data.get('code') or f'{prefix}-{uuid4().hex[:8].upper()}'
    if not isinstance(code, str) or not code.strip() or len(code) > 20:
        return jsonify({'error': 'A valid code is required'}), 400

    email = data.get('email')
    if email is not None and (not isinstance(email, str) or len(email) > 120):
        return jsonify({'error': 'Invalid email'}), 400
    if model.query.filter_by(code=code).first():
        return jsonify({'error': 'Code already exists'}), 409
    if email and model.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists'}), 409

    partner = model(
        code=code,
        name=name.strip(),
        email=email,
        phone=data.get('phone'),
        address=data.get('address')
    )
    try:
        db.session.add(partner)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Business partner creation failed')
        return jsonify({'error': 'Unable to create business partner'}), 500

    return jsonify({'data': partner.to_dict()}), 201


def _get_partner(model, partner_id, label):
    partner = db.session.get(model, partner_id)
    if not partner:
        return jsonify({'error': f'{label} not found'}), 404
    return jsonify({'data': partner.to_dict()})


def _patch_partner(model, partner_id, label):
    partner = db.session.get(model, partner_id)
    if not partner:
        return jsonify({'error': f'{label} not found'}), 404
    data = request.get_json()
    if not isinstance(data, dict) or not data:
        return jsonify({'error': 'A non-empty JSON object is required'}), 400
    allowed_fields = {'name', 'email', 'phone', 'address', 'is_active'}
    unknown_fields = set(data) - allowed_fields
    if unknown_fields:
        return jsonify({
            'error': 'Unsupported fields',
            'fields': sorted(unknown_fields)
        }), 400

    if 'name' in data and (
        not isinstance(data['name'], str)
        or not data['name'].strip()
        or len(data['name']) > 100
    ):
        return jsonify({'error': 'A valid name is required'}), 400
    if 'email' in data and data['email'] is not None:
        if not isinstance(data['email'], str) or len(data['email']) > 120:
            return jsonify({'error': 'Invalid email'}), 400
        duplicate = model.query.filter(
            model.email == data['email'],
            model.id != partner_id
        ).first()
        if duplicate:
            return jsonify({'error': 'Email already exists'}), 409
    for field in ('phone', 'address'):
        if field in data and data[field] is not None and not isinstance(data[field], str):
            return jsonify({'error': f'{field} must be a string or null'}), 400
    if 'is_active' in data and not isinstance(data['is_active'], bool):
        return jsonify({'error': 'is_active must be a boolean'}), 400

    for field, value in data.items():
        setattr(partner, field, value.strip() if field == 'name' else value)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Business partner update failed')
        return jsonify({'error': f'Unable to update {label.lower()}'}), 500
    return jsonify({'data': partner.to_dict()})


@customers_bp.route('/customers', methods=['GET'])
def get_customers():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    pagination = Customer.query.order_by(Customer.id).paginate(
        page=page,
        per_page=min(max(per_page, 1), 100),
        error_out=False
    )
    return jsonify({
        'data': [customer.to_dict() for customer in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
    })


@customers_bp.route('/customers', methods=['POST'])
def create_customer():
    return _create_partner(Customer, 'CUST')


@customers_bp.route('/customers/<int:customer_id>', methods=['GET'])
def get_customer(customer_id):
    return _get_partner(Customer, customer_id, 'Customer')


@customers_bp.route('/customers/<int:customer_id>', methods=['PATCH'])
def patch_customer(customer_id):
    return _patch_partner(Customer, customer_id, 'Customer')


@suppliers_bp.route('/suppliers', methods=['GET'])
def get_suppliers():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    pagination = Supplier.query.order_by(Supplier.id).paginate(
        page=page,
        per_page=min(max(per_page, 1), 100),
        error_out=False
    )
    return jsonify({
        'data': [supplier.to_dict() for supplier in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
    })


@suppliers_bp.route('/suppliers', methods=['POST'])
def create_supplier():
    return _create_partner(Supplier, 'SUP')


@suppliers_bp.route('/suppliers/<int:supplier_id>', methods=['GET'])
def get_supplier(supplier_id):
    return _get_partner(Supplier, supplier_id, 'Supplier')


@suppliers_bp.route('/suppliers/<int:supplier_id>', methods=['PATCH'])
def patch_supplier(supplier_id):
    return _patch_partner(Supplier, supplier_id, 'Supplier')
